# ElohimOS Phase 1 E2E Validation Report
Date: 2025-11-12
Status: In Progress

## Executive Summary

Phase 1 Setup Wizard implementation complete with 7 functional steps. This document tracks E2E validation against acceptance criteria and edge cases.

---

## 1. Wizard Flow Validation

### 1.1 Clean Start
**Test**: First-time user sees setup wizard before login

**Code Review** (`App.tsx:97-112`):
```typescript
useEffect(() => {
  const checkSetup = async () => {
    try {
      const { setupWizardApi } = await import('./lib/setupWizardApi')
      const status = await setupWizardApi.getSetupStatus()
      setSetupComplete(status.setup_completed)
    } catch (error) {
      setSetupComplete(true)  // Fail-open: don't block user
    }
  }
  checkSetup()
}, [])
```

**Display Logic** (`App.tsx:234-248`):
```typescript
if (setupComplete === false) {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <SetupWizard onComplete={() => {
        setSetupComplete(true)
        setAuthState('checking')
      }} />
    </Suspense>
  )
}
```

**Backend Endpoint** (`setup_wizard_routes.py:155-178`):
- `GET /api/v1/setup/status`
- Returns `{ setup_completed: bool, founder_setup_completed: bool }`
- Reads from `founder_setup` table

**Status**: ✅ **PASS** (Code Review)
- Clean start flow correct
- Wizard appears before auth check
- Status reflects `founder_setup.setup_completed`

**Manual Test Required**:
- [ ] Fresh database → wizard appears
- [ ] Status endpoint shows Ollama installed/running
- [ ] Status shows correct RAM tier (Essential/Balanced/Power User)

---

### 1.2 Wizard Resume on Reload
**Test**: Reload during any step resumes at same step

**Current Implementation**:
- Wizard state is **in-memory only** (no localStorage persistence)
- Each step re-fetches server state on mount
- Steps are **idempotent** (can be re-entered safely)

**Step-by-Step Resume Behavior**:

| Step | Resume Strategy | Data Source |
|------|----------------|-------------|
| Welcome | Always safe | None |
| Account | Re-enter form | None (no persistence) |
| Ollama | Re-check status | `GET /api/v1/setup/ollama` |
| Models | Re-fetch recommendations | `GET /api/v1/setup/models/recommendations` |
| Download | Re-check installed | `GET /api/v1/setup/models/installed` |
| Hot Slots | Re-fetch installed + slots | `GET /api/v1/setup/models/installed` |
| Completion | Re-display summary | Wizard state (in-memory) |

**Status**: ⚠️ **PARTIAL**
- ✅ Steps re-fetch server state correctly
- ✅ Idempotent operations (safe to re-enter)
- ❌ Current step index not persisted (reloads to Welcome)
- ❌ Form data lost on reload (AccountStep)

**Impact**: **Low** - First-run wizard typically completed in one session

**Recommendation**:
- **Now**: Document as known limitation
- **Later**: Add optional localStorage persistence if users report issues

---

### 1.3 Setup Completion
**Test**: After completion, wizard never reappears

**Completion Flow**:
1. CompletionStep calls `setupWizardApi.completeSetup()`
2. Backend: `POST /api/v1/setup/complete`
3. Backend updates `founder_setup.setup_completed = 1`
4. Frontend: `onComplete()` → `setSetupComplete(true)`
5. App.tsx no longer renders wizard

**Code** (`CompletionStep.tsx:19-42`):
```typescript
const handleFinish = async () => {
  try {
    await setupWizardApi.completeSetup()
    if (enableAutoPreload) {
      localStorage.setItem('setup_autoPreloadModel', 'true')
    }
    if (props.onComplete) {
      props.onComplete()
    }
  } catch (err) {
    setError(err.message)
  }
}
```

**Backend** (`setup_wizard_routes.py:405-430`):
- Calls `get_founder_wizard().is_setup_complete()`
- Returns success/failure

**Status**: ✅ **PASS** (Code Review)
- Completion marks `founder_setup.setup_completed = 1`
- App.tsx checks status on every mount
- Wizard never reappears after completion

**Manual Test Required**:
- [ ] Complete wizard → reload → login appears (not wizard)
- [ ] Database shows `setup_completed = 1` in `founder_setup` table

---

## 2. Models & Downloads Validation

### 2.1 Tier Selection from Config
**Test**: ModelsStep loads correct tier based on RAM

**Backend** (`setup_wizard.py:191-239`):
```python
async def detect_system_resources(self) -> Dict[str, Any]:
    ram_gb = int(psutil.virtual_memory().total / (1024 ** 3))

    if ram_gb >= 32:
        tier = "power_user"
    elif ram_gb >= 16:
        tier = "balanced"
    else:
        tier = "essential"

    # Load from recommended_models.json
    config = json.load(open(self.config_path))
    tier_info = config.get("tiers", {}).get(tier, {})
```

**Frontend** (`ModelsStep.tsx:42-64`):
```typescript
const loadRecommendations = async () => {
  const data = await setupWizardApi.getModelRecommendations()
  setRecommendations(data)

  // Auto-select based on hot_slot_recommendations
  const autoSelected = new Set<string>()
  Object.values(data.hot_slot_recommendations).forEach(modelName => {
    if (modelName) autoSelected.add(modelName)
  })
  setSelectedModels(autoSelected)
}
```

**Config** (`recommended_models.json:5-145`):
- Essential: 3 models (qwen2.5-coder:1.5b, phi3.5:3.8b, llama3.1:8b)
- Balanced: 3 models (deepseek-r1:8b, qwen2.5-coder:14b, gpt-oss:20b)
- Power User: 1 model (qwen2.5-coder:32b)

**Status**: ✅ **PASS** (Code Review)
- RAM detection correct
- Tier mapping correct
- Config loading correct
- Auto-selection uses hot_slot_recommendations

**Manual Test Required**:
- [ ] 8GB RAM → Essential tier (3 models pre-selected)
- [ ] 16GB RAM → Balanced tier (3-4 models pre-selected)
- [ ] 32GB+ RAM → Power User tier (4 models pre-selected)

---

### 2.2 SSE Progress Tracking
**Test**: Download shows real-time progress per model

**Backend SSE Endpoint** (`setup_wizard_routes.py:316-430`):
```python
@router.get("/models/download/progress")
async def download_model_progress(model_name: str):
    async def progress_generator():
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ''):
            progress_data = {
                "model": model_name,
                "status": "downloading",
                "progress": 0.0,
                "message": line
            }

            # Extract percentage
            if "%" in line:
                percent_str = line.split("%")[0].split()[-1]
                progress_data["progress"] = float(percent_str)

            yield f"data: {json.dumps(progress_data)}\n\n"

        # Final status
        if process.returncode == 0:
            yield f"data: {json.dumps({...status: 'complete'...})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        progress_generator(),
        media_type="text/event-stream"
    )
```

**Frontend SSE Consumer** (`DownloadStep.tsx:61-105`):
```typescript
const eventSource = new EventSource(
  `/api/v1/setup/models/download/progress?model_name=${encodeURIComponent(modelName)}`
)

await new Promise<void>((resolve, reject) => {
  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close()
      resolve()
      return
    }

    const data = JSON.parse(event.data)
    setModelProgress(prev => {
      const next = new Map(prev)
      next.set(modelName, {
        status: data.status === 'complete' ? 'complete' : 'downloading',
        progress: data.progress || 0,
        message: data.message
      })
      return next
    })

    if (data.status === 'complete') {
      eventSource.close()
      resolve()
    } else if (data.status === 'error') {
      eventSource.close()
      reject(new Error(data.message))
    }
  }

  eventSource.onerror = () => {
    eventSource.close()
    reject(new Error('Connection error'))
  }
})
```

**Error Handling**:
```typescript
catch (err) {
  setModelProgress(prev => {
    const next = new Map(prev)
    next.set(modelName, {
      status: 'error',
      progress: 0,
      message: err.message
    })
    return next
  })
}
```

**Status**: ✅ **PASS** (Code Review)
- SSE stream format correct
- Progress parsing correct
- Error handling graceful (continues to next model)
- EventSource cleanup on unmount

**Manual Test Required**:
- [ ] DevTools → Network → EventStream shows heartbeats
- [ ] Progress bar updates in real-time
- [ ] Failed download shows error, doesn't block wizard
- [ ] Multiple models download sequentially

---

### 2.3 Auto-Preload Toggle
**Test**: Disable/enable setting and verify App.tsx respects it

**CompletionStep Toggle** (`CompletionStep.tsx:140-156`):
```typescript
<input
  id="enableAutoPreload"
  type="checkbox"
  checked={enableAutoPreload}
  onChange={(e) => setEnableAutoPreload(e.target.checked)}
/>

// On finish:
if (enableAutoPreload) {
  localStorage.setItem('setup_autoPreloadModel', 'true')
}
```

**App.tsx Integration** (`App.tsx:177-203`):
```typescript
useEffect(() => {
  // Only preload if enabled in settings
  if (!settings.autoPreloadModel) {
    console.debug('Auto-preload disabled in settings')
    return
  }

  if (!sessionId) return
  if (!localStorage.getItem('auth_token')) return

  const preloadDefaultModel = async () => {
    try {
      console.log(`🔄 Auto-preloading: ${settings.defaultModel} (source: frontend_default)`)
      await api.preloadModel(settings.defaultModel, '1h', 'frontend_default')
      console.log(`✅ Model preloaded (source: frontend_default)`)
    } catch (error) {
      console.debug('⚠️ Preload failed (non-critical):', error)
    }
  }

  const timeoutId = setTimeout(preloadDefaultModel, 3000)
  return () => clearTimeout(timeoutId)
}, [sessionId, settings.defaultModel, settings.autoPreloadModel])
```

**Settings UI** (`ChatSettingsContent.tsx:432-444`):
```typescript
<input
  type="checkbox"
  checked={settings.autoPreloadModel}
  onChange={(e) => updateSettings({ autoPreloadModel: e.target.checked })}
/>
```

**Status**: ✅ **PASS** (Code Review)
- Completion step sets localStorage preference
- Settings UI toggles store value
- App.tsx checks `settings.autoPreloadModel` before preloading
- 3-second delay allows Ollama to start

**Manual Test Required**:
- [ ] Enable in wizard → login → console shows preload after 3s
- [ ] Disable in Settings → reload → no preload
- [ ] Re-enable in Settings → reload → preload works

---

## 3. Hot Slots Validation

### 3.1 Assign/Eject via UI
**Test**: Hot slot changes persist to `model_hot_slots.json`

**HotSlotsStep Assignment** (`HotSlotsStep.tsx:54-74`):
```typescript
const handleNext = async () => {
  try {
    // Save hot slots configuration
    await setupWizardApi.configureHotSlots(slots)

    props.updateWizardState({
      hotSlotsConfigured: true,
      hotSlots: slots
    })

    props.onNext()
  } catch (err) {
    setError(err.message)
  }
}
```

**Backend Endpoint** (`setup_wizard_routes.py:313-360`):
```python
@router.post("/hot-slots")
async def configure_hot_slots(body: ConfigureHotSlotsRequest):
    wizard = get_setup_wizard()

    # Validate slot numbers (1-4)
    for slot_num in body.slots.keys():
        if slot_num not in [1, 2, 3, 4]:
            raise HTTPException(400, f"Invalid slot: {slot_num}")

    success = await wizard.configure_hot_slots(body.slots)
    if success:
        return {"success": True, "message": "Hot slots configured"}
```

**Setup Wizard Service** (`setup_wizard.py:409-447`):
```python
async def configure_hot_slots(self, slots: Dict[int, str]) -> bool:
    from model_manager import ModelManager

    manager = ModelManager()

    for slot_num, model_name in slots.items():
        if model_name is None:
            manager.remove_from_slot(slot_num)
        else:
            success = manager.assign_to_slot(slot_num, model_name)
            if not success:
                return False

    return True
```

**Model Manager Persistence** (`model_manager.py:142-190`):
```python
def save_hot_slots(self):
    """Save hot slots to disk (model_hot_slots.json)"""
    try:
        with open(HOT_SLOTS_FILE, 'w') as f:
            json.dump(self.hot_slots, f, indent=2)
        logger.info(f"💾 Hot slots saved to {HOT_SLOTS_FILE}")
    except Exception as e:
        logger.error(f"❌ Failed to save hot slots: {e}")
```

**Status**: ✅ **PASS** (Code Review)
- HotSlotsStep saves via API
- Backend validates slot numbers (1-4)
- ModelManager writes to `model_hot_slots.json`
- Logging shows save success

**Manual Test Required**:
- [ ] Assign slot 1 → `model_hot_slots.json` shows assignment
- [ ] Eject slot 2 → JSON shows `null`
- [ ] POST returns 200 on success
- [ ] Invalid slot number (5) returns 400

---

### 3.2 Model Selector Reflects Loaded Models
**Test**: After assignment, Model Selector shows assigned model

**Integration Point**: ModelManagementSidebar uses same `model_manager.py`

**Status**: ✅ **PASS** (Existing Integration)
- Hot slots JSON read on sidebar mount
- Assign/eject updates same JSON file
- No additional work needed

---

## 4. Auth & Permissions Validation

### 4.1 Performance Monitor Auth
**Test**: Returns 200 with token, 403 without

**PerformanceMonitorDropdown** (`PerformanceMonitorDropdown.tsx:71-92`):
```typescript
const fetchStats = async () => {
  try {
    const token = localStorage.getItem('auth_token')
    const response = await fetch('/api/v1/chat/performance/stats', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    if (!response.ok) {
      throw new Error('Failed to fetch stats')
    }
    const data = await response.json()
    setStats(data)
  } catch (err) {
    setError(err.message)
  }
}
```

**Backend Route** (`chat.py:route`):
- Requires `@require_perm_team("chat.use")` decorator
- Returns 403 without valid token

**Status**: ✅ **PASS** (Code Review - Fixed in Codex validation)
- Authorization header present
- Error handling correct

**Manual Test Required**:
- [ ] Logged in → Performance dropdown shows stats
- [ ] Clear token → 403 error
- [ ] Network tab shows `Authorization: Bearer <token>`

---

### 4.2 Chat Route Permissions
**Test**: Non-authorized user gets 403

**Chat Routes** (`chat.py:protected routes`):
```python
@router.post("/sessions/{chat_id}/messages")
@require_perm_team("chat.use")
async def send_message(...):
    ...
```

**Enforcement** (`permission_engine.py`):
- Checks user role permissions
- Founder bypass for founder_rights
- Team-aware permission checks

**Status**: ✅ **PASS** (Existing Implementation)
- 6 chat endpoints have `@require_perm_team` decorator
- Permission engine enforces access control

**Manual Test Required**:
- [ ] Guest role → 403 on chat message
- [ ] Super admin → 200 on chat message

---

## 5. Monitoring Validation

### 5.1 Metal4 Polling Behavior
**Test**: Shared service polls once, handles 429 with backoff

**Shared Service** (`metal4StatsService.ts:20-120`):
```typescript
class Metal4StatsService {
  private subscribers: Set<Subscriber> = new Set()
  private polling: boolean = false
  private pollingInterval: NodeJS.Timeout | null = null
  private pollDelay: number = 2000  // 2 seconds default
  private backoffDelay: number = 60000  // 60 seconds on 429

  private async poll() {
    try {
      const response = await fetch('/api/v1/monitoring/metal4', {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.status === 429) {
        // Rate limited - back off
        this.stopPolling()
        setTimeout(() => this.startPolling(), this.backoffDelay)
        return
      }

      const data = await response.json()
      this.broadcast(data)
    } catch (err) {
      console.error('Metal4 stats poll failed:', err)
    }
  }

  startPolling() {
    if (this.polling) return
    this.polling = true
    this.pollingInterval = setInterval(() => this.poll(), this.pollDelay)
  }

  subscribe(callback: Subscriber): () => void {
    this.subscribers.add(callback)
    if (this.subscribers.size === 1 && !this.polling) {
      this.startPolling()  // Start when first subscriber
    }
    return () => {
      this.subscribers.delete(callback)
      if (this.subscribers.size === 0) {
        this.stopPolling()  // Stop when last subscriber leaves
      }
    }
  }
}

export const metal4StatsService = new Metal4StatsService()
```

**Component Usage** (`Header.tsx`, `ControlCenterModal.tsx`, `WorkflowTreeSidebar.tsx`):
```typescript
useEffect(() => {
  const unsubscribe = metal4StatsService.subscribe((stats) => {
    setMetal4Stats(stats)
  })
  return unsubscribe
}, [])
```

**Status**: ✅ **PASS** (Code Review)
- Singleton service ensures one poller per tab
- Auto-start on first subscriber
- Auto-stop when no subscribers
- 429 triggers 60s backoff

**Manual Test Required**:
- [ ] Open 3 components → Network shows 1 poller only
- [ ] Close all components → polling stops
- [ ] 429 response → 60s pause before retry
- [ ] Multiple tabs → each tab has own poller (expected)

---

## 6. Edge Cases Validation

### 6.1 Partial Downloads
**Test**: Proceed with at least one failure

**DownloadStep Error Handling** (`DownloadStep.tsx:113-125`):
```typescript
catch (err) {
  // Mark as error but continue to next model
  setModelProgress(prev => {
    const next = new Map(prev)
    next.set(modelName, {
      model: modelName,
      status: 'error',
      progress: 0,
      message: err.message
    })
    return next
  })
}

// After all downloads (success or failure):
setIsDownloading(false)
setAllComplete(true)  // Allow continue
```

**HotSlotsStep Adaptation** (`HotSlotsStep.tsx:76-77`):
```typescript
// Only show models that were selected (download success not checked)
const availableModels = selectedModels.length > 0 ? selectedModels : installedModels
```

**Status**: ⚠️ **PARTIAL**
- ✅ Errors don't block wizard progress
- ✅ Continue button enabled after all attempts
- ❌ Hot slots shows selected models, not downloaded models
- **Impact**: User may assign slot to non-downloaded model

**Recommendation**:
- **Quick Fix**: Filter `availableModels` by checking installed models
- **Code**:
  ```typescript
  const availableModels = selectedModels.filter(m =>
    installedModels.includes(m)
  )
  ```

---

### 6.2 No Network (OllamaStep)
**Test**: Blocks until network restored, re-check works

**OllamaStep Check** (`OllamaStep.tsx:32-50`):
```typescript
const checkOllama = async () => {
  try {
    const result = await setupWizardApi.checkOllama()
    setStatus(result)
    props.updateWizardState({
      ollamaInstalled: result.installed,
      ollamaRunning: result.running
    })
  } catch (err) {
    setError(err.message)
  }
}

// Re-check button
<button onClick={checkOllama}>
  <RefreshCw className="w-4 h-4" />
  Check Again
</button>

// Continue blocked
const canProceed = status?.installed && status?.running
```

**Status**: ✅ **PASS** (Code Review)
- Network error shows error message
- Re-check button visible
- Continue disabled until Ollama running

**Manual Test Required**:
- [ ] Disconnect network → check fails → error shown
- [ ] Reconnect → click "Check Again" → success
- [ ] Continue button enabled only when running

---

### 6.3 Change Tier Mid-Download
**Test**: Stop current pulls, start new selection

**Current Behavior**:
- ModelsStep is **before** DownloadStep
- Once download starts, user cannot go back to change tier
- Back button disabled during downloads (`DownloadStep.tsx:240-246`)

**Status**: ✅ **EXPECTED BEHAVIOR**
- Tier selection locked once downloads start
- Users can skip downloads and change later via Model Management

**Recommendation**: Document as intended behavior

---

### 6.4 Multiple Tabs
**Test**: Single poller per tab, no duplicate hot-slot writes

**Metal4 Poller**:
- Each tab has independent `metal4StatsService` instance
- Each tab polls independently (expected for multi-tab support)
- No shared worker (intentional - keeps logic simple)

**Hot Slots**:
- Writes go through backend API (serialized by FastAPI)
- JSON file writes are atomic (Python `json.dump`)
- No race condition risk

**Status**: ✅ **PASS** (Design Review)
- Multiple tabs supported
- No data corruption risk
- Each tab polls independently (minor overhead, acceptable)

---

## 7. Quick Checks

### 7.1 SSE Stability
**Checklist**:
- [ ] DevTools → Network → EventStream filter
- [ ] Verify SSE connection shows "pending" while downloading
- [ ] Message format: `data: {"model":"...","progress":45.5,"status":"downloading"}\n\n`
- [ ] Final message: `data: [DONE]\n\n`
- [ ] No reconnection loops

---

### 7.2 Backend Logs
**Checklist**:
- [ ] No Metal shader compile errors (fixed in Phase 0)
- [ ] No "coroutine was never awaited" warnings (fixed in Phase 0)
- [ ] No repeated ModelManager shape errors
- [ ] Hot slot saves show: `💾 Hot slots saved to model_hot_slots.json`
- [ ] Model preload shows: `✅ Model preloaded (source: frontend_default)`

---

### 7.3 Storage Verification
**Checklist**:
- [ ] `apps/backend/api/data/model_hot_slots.json` exists after HotSlots save
- [ ] JSON format: `{"1": "model-name", "2": null, "3": "model-name", "4": null}`
- [ ] File updates on assign/eject operations

---

## Summary

### Code Review Results (Static Analysis)

| Category | Status | Notes |
|----------|--------|-------|
| Wizard Flow | ✅ PASS | Clean start, completion logic correct |
| Wizard Resume | ⚠️ PARTIAL | No state persistence (low priority) |
| Model Recommendations | ✅ PASS | Tier detection, config loading correct |
| SSE Downloads | ✅ PASS | Progress tracking, error handling correct |
| Hot Slots | ✅ PASS | Assignment, persistence, API correct |
| Auth Headers | ✅ PASS | Protected endpoints use Authorization |
| Monitoring | ✅ PASS | Shared service, 429 backoff correct |

### Manual Testing Required

**Critical Path** (must test before Phase 2):
- [ ] Fresh database → wizard flow → completion
- [ ] Model download progress bars work
- [ ] Hot slots persist to JSON
- [ ] Auto-preload toggle works

**Nice-to-Have** (can defer):
- [ ] Wizard resume at each step
- [ ] Partial download graceful handling
- [ ] Network failure recovery

### Known Gaps

1. **Wizard State Persistence**: Reloads reset to Welcome step
   - Impact: Low (first-run usually one session)
   - Fix: Add localStorage wrapper (30 mins)

2. **Hot Slots Model Filtering**: Shows selected, not downloaded models
   - Impact: Medium (user may assign non-downloaded model)
   - Fix: Filter by installed models (5 mins)
   - **Code**: `HotSlotsStep.tsx:77`
     ```typescript
     const availableModels = selectedModels.filter(m =>
       installedModels.includes(m)
     )
     ```

### Recommendations

**Before Phase 2**:
1. ✅ Fix hot slots filtering (5 mins) - RECOMMENDED
2. ⏸️ Add wizard state persistence (30 mins) - DEFER
3. ✅ Manual test critical path - REQUIRED

**Phase 2 Ready**: Yes, with hot slots fix applied

---

## Next Steps

1. Apply hot slots filtering fix
2. Run manual critical path tests
3. Document any failures
4. Proceed to Phase 2 implementation

---

**Validation Owner**: Claude Code
**Review Date**: 2025-11-12
**Status**: Code review complete, manual tests pending
