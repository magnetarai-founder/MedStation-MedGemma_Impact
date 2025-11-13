# ElohimOS Phase 2: Local-Only Core Polish

**Date**: 2025-11-12
**Status**: Ready to Start
**Prerequisites**: Phase 0 ✅ | Phase 1 ✅ | E2E Validation ✅

---

## Overview

Phase 2 focuses on polishing the local-only experience with enhanced UX, performance guardrails, and basic RBAC visibility. All work targets single-user, offline-first usage before introducing team features in Phase 3.

**Key Themes**:
- Local vs Team context clarity
- Performance and resource management
- Enhanced chat features
- Security visibility

---

## 1. Local-Only Core Polish

### 1.1 Docs/Vault/Workflows Local Mode
**Goal**: Ensure all queries enforce `team_id IS NULL` for local resources

**Tasks**:
- [ ] Audit all SQL queries in `docs_service.py`
- [ ] Add `WHERE team_id IS NULL` to local document queries
- [ ] Create database indexes for performance:
  ```sql
  CREATE INDEX idx_documents_local ON documents(user_id) WHERE team_id IS NULL;
  CREATE INDEX idx_workflows_local ON workflows(user_id) WHERE team_id IS NULL;
  CREATE INDEX idx_vault_local ON vault_items(user_id) WHERE team_id IS NULL;
  ```
- [ ] Test query performance with EXPLAIN ANALYZE

**Acceptance**:
- ✅ Local resources never leak into team context
- ✅ Query plans use indexes efficiently
- ✅ No N+1 queries on document lists

---

### 1.2 Local vs Team Visual Badges
**Goal**: Clear UI indicators for context switching

**Design**:
```
┌─────────────────────────────────────┐
│ [📍 Local]  Documents  Chat  Code  │  ← Header badge
└─────────────────────────────────────┘

Document List:
  ┌─────────────────────────┐
  │ 📄 README.md  [Local]   │
  │ 📄 API Spec   [Local]   │
  │ 📄 Team Plan  [Team: Engineering] │  ← Future
  └─────────────────────────┘
```

**Tasks**:
- [ ] Create `<ContextBadge>` component
  - Props: `context: 'local' | 'team'`, `teamName?: string`
  - Variants: inline (small) and header (prominent)
- [ ] Add badge to Header (persistent)
- [ ] Add inline badges to:
  - Document list items
  - Workflow cards
  - Chat session list
  - Vault items
- [ ] Style: Local = green, Team = blue

**Files**:
- `apps/frontend/src/components/ContextBadge.tsx` (NEW)
- `apps/frontend/src/components/Header.tsx`
- `apps/frontend/src/components/DocumentList.tsx`
- `apps/frontend/src/components/WorkflowTreeSidebar.tsx`

**Acceptance**:
- ✅ Header shows "Local" badge always (Phase 2)
- ✅ All resource lists show context inline
- ✅ Badge colors are distinct and accessible

---

## 2. Chat Enhancements

### 2.1 Token Usage Meter
**Goal**: Per-session token count display with visual meter

**Backend**:
- ✅ Endpoint exists: `GET /api/v1/chat/sessions/{id}/token-count`
- ✅ Returns: `{ prompt_tokens, completion_tokens, total_tokens }`

**Frontend Design**:
```
┌──────────────────────────────────────┐
│  Chat Session: Project Discussion    │
│  ╔══════════════════════════╗ 75%    │
│  ║████████████████████░░░░░░║        │
│  ╚══════════════════════════╝        │
│  6,144 / 8,192 tokens                │
└──────────────────────────────────────┘
```

**Tasks**:
- [ ] Create `<TokenMeter>` component
  - Props: `sessionId`, `contextWindow`
  - Auto-refresh on new messages
  - Color: green (0-60%), yellow (60-85%), red (85-100%)
- [ ] Add to ChatWindow header/footer
- [ ] Display format: `{used:,} / {limit:,} tokens ({percent}%)`
- [ ] Warn user at 90% threshold

**Files**:
- `apps/frontend/src/components/TokenMeter.tsx` (NEW)
- `apps/frontend/src/components/ChatWindow.tsx`
- `apps/frontend/src/lib/api.ts` (add `getSessionTokenCount` method)

**Acceptance**:
- ✅ Meter updates after each message
- ✅ Warning shown at 90% capacity
- ✅ User can see token breakdown (prompt vs completion)

---

### 2.2 Per-Session Model Selector
**Goal**: Change model mid-session without creating new chat

**Current**: Global model selector (applies to all new sessions)
**New**: Per-session model selector (overrides global default)

**Tasks**:
- [ ] Add model selector dropdown to ChatWindow toolbar
- [ ] Store selected model in session metadata
  - Backend: Add `active_model` column to `chat_sessions` table
  - Migration: `ALTER TABLE chat_sessions ADD COLUMN active_model TEXT`
- [ ] Update message endpoint to use session model if set
- [ ] Show model name in chat header
- [ ] Add "Reset to Default" button

**Files**:
- `apps/backend/api/alembic/versions/XXX_add_session_model.py` (NEW - migration)
- `apps/backend/api/routes/chat.py` (update message endpoint)
- `apps/frontend/src/components/ChatWindow.tsx`
- `apps/frontend/src/stores/chatStore.ts` (add `activeModel` to session)

**Acceptance**:
- ✅ User can switch model mid-conversation
- ✅ New messages use session model if set, else default
- ✅ Model name visible in chat UI

---

### 2.3 Memory Fit Warnings
**Goal**: Warn before loading model that exceeds available RAM

**Detection Logic**:
```python
def check_model_fit(model_name: str) -> Dict[str, Any]:
    # Get model size from Ollama
    model_info = ollama_client.show(model_name)
    model_size_gb = model_info['size'] / (1024 ** 3)

    # Get available RAM
    available_gb = psutil.virtual_memory().available / (1024 ** 3)

    # Rule: Model should fit in 50% of available RAM
    fits = model_size_gb <= (available_gb * 0.5)

    return {
        "fits": fits,
        "model_size_gb": model_size_gb,
        "available_gb": available_gb,
        "recommendation": "OK" if fits else "May cause system slowdown"
    }
```

**Tasks**:
- [ ] Add `POST /api/v1/chat/models/check-fit` endpoint
- [ ] Frontend: Call before model selection
- [ ] Show warning modal if doesn't fit:
  ```
  ⚠️ Model Size Warning
  This model (12GB) may exceed available RAM (8GB).
  Loading may cause system slowdown.

  [ Cancel ]  [ Load Anyway ]
  ```
- [ ] Add to:
  - ModelSelector dropdown (on change)
  - Hot slot assignment (on assign)
  - Setup wizard ModelsStep (on selection)

**Files**:
- `apps/backend/api/routes/chat.py` (add check-fit endpoint)
- `apps/frontend/src/components/ModelSelector.tsx`
- `apps/frontend/src/components/ModelManagementSidebar.tsx`

**Acceptance**:
- ✅ Warning shown when model > 50% available RAM
- ✅ User can proceed with override
- ✅ No warnings for appropriate-sized models

---

## 3. Performance Guardrails

### 3.1 Usable Memory Limit on Hot Slots
**Goal**: Prevent assigning models that collectively exceed RAM

**Logic**:
```python
def validate_hot_slot_assignment(slot_num: int, model_name: str):
    # Get sizes of currently assigned models
    current_total_gb = sum(
        get_model_size(model)
        for slot, model in hot_slots.items()
        if slot != slot_num and model is not None
    )

    # Add new model size
    new_model_size = get_model_size(model_name)
    proposed_total_gb = current_total_gb + new_model_size

    # Get system RAM
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    # Rule: Hot slots should not exceed 75% of total RAM
    max_allowed_gb = total_ram_gb * 0.75

    if proposed_total_gb > max_allowed_gb:
        raise HTTPException(
            status_code=400,
            detail=f"Hot slots would use {proposed_total_gb:.1f}GB / {total_ram_gb:.1f}GB RAM. Limit: {max_allowed_gb:.1f}GB"
        )
```

**Tasks**:
- [ ] Add validation to `POST /api/v1/chat/models/hot-slots/{slot_num}`
- [ ] Frontend: Show warning before assign if would exceed
- [ ] Display current hot slot RAM usage in ModelManagementSidebar
  ```
  Hot Slots RAM Usage: 18.5 GB / 24 GB (77%)
  ┌─────────────────────────┐
  │ Slot 1: gpt-oss:20b (12GB) │
  │ Slot 2: qwen:14b (6.5GB)    │
  │ Slot 3: Empty               │
  │ Slot 4: Empty               │
  └─────────────────────────┘
  ```

**Files**:
- `apps/backend/api/routes/chat.py` (add validation)
- `apps/backend/api/model_manager.py` (add size calculation)
- `apps/frontend/src/components/ModelManagementSidebar.tsx`

**Acceptance**:
- ✅ Assignment denied if would exceed 75% RAM
- ✅ User sees clear error message with usage stats
- ✅ RAM usage meter visible in sidebar

---

### 3.2 Background Cleanup for Stale Artifacts
**Goal**: Periodic cleanup of temp files, old sessions, orphaned data

**Tasks**:
- [ ] Create `cleanup_service.py`
  - Delete temp files older than 7 days (`/tmp/elohimos_*`)
  - Archive chat sessions older than 90 days (move to `archived_sessions` table)
  - Delete orphaned document embeddings (doc deleted but embedding remains)
  - Clean up stale model cache entries
- [ ] Add scheduled task (runs daily at 2 AM local time)
  - Use APScheduler or systemd timer
- [ ] Add manual trigger endpoint: `POST /api/v1/admin/cleanup`
- [ ] Log cleanup actions with stats

**Files**:
- `apps/backend/api/services/cleanup_service.py` (NEW)
- `apps/backend/api/main.py` (register scheduled task)

**Acceptance**:
- ✅ Temp files cleaned daily
- ✅ Old sessions archived
- ✅ Disk usage stays under control

---

## 4. Monitoring UX

### 4.1 Metal4 Activity Indicator
**Goal**: Header shows light indicator when Metal4 is active

**Design**:
```
Header:
  [📍 Local] ElohimOS [🟢 Metal4]  ← Green when idle
  [📍 Local] ElohimOS [🟡 Metal4]  ← Yellow when processing
  [📍 Local] ElohimOS [🔴 Metal4]  ← Red when error
```

**Tasks**:
- [ ] Extend Metal4 stats to include:
  ```json
  {
    "status": "idle" | "processing" | "error",
    "queue_depth": 0,
    "last_activity": "2025-11-12T10:30:00Z"
  }
  ```
- [ ] Add light indicator to Header
  - Tooltips show queue depth and last activity
  - Click opens PerformanceMonitorDropdown
- [ ] Update shared `metal4StatsService` to parse status

**Files**:
- `apps/backend/api/metal4_sql_engine.py` (add status field)
- `apps/frontend/src/components/Header.tsx`
- `apps/frontend/src/services/metal4StatsService.ts`

**Acceptance**:
- ✅ Light reflects current Metal4 status
- ✅ Tooltip shows queue depth
- ✅ Click opens performance details

---

### 4.2 Queue Backlog Exposure
**Goal**: Show pending Metal4 queries in performance monitor

**Tasks**:
- [ ] Add queue metrics to `/api/v1/monitoring/metal4`:
  ```json
  {
    "queue": {
      "pending": 3,
      "in_flight": 1,
      "avg_wait_ms": 120
    }
  }
  ```
- [ ] Display in PerformanceMonitorDropdown:
  ```
  Queue Status
  ┌─────────────────────────┐
  │ Pending: 3 queries      │
  │ In Flight: 1            │
  │ Avg Wait: 120ms         │
  └─────────────────────────┘
  ```

**Files**:
- `apps/backend/api/metal4_sql_engine.py` (add queue tracking)
- `apps/frontend/src/components/PerformanceMonitorDropdown.tsx`

**Acceptance**:
- ✅ Queue depth visible
- ✅ Wait time estimates shown

---

## 5. Security & RBAC

### 5.1 Minimal Admin/RBAC Screen
**Goal**: Visualize effective permissions for current user/team

**Design**:
```
Settings → Permissions

Current User: admin (super_admin role)

Effective Permissions:
  ┌──────────────────────────────────┐
  │ ✅ chat.use                      │
  │ ✅ chat.manage_sessions          │
  │ ✅ docs.read                     │
  │ ✅ docs.write                    │
  │ ✅ workflows.execute             │
  │ ✅ admin.manage_users            │
  │ ❌ founder.all (requires password)│
  └──────────────────────────────────┘

Role Baseline: super_admin
Team Context: Local (no team)
```

**Tasks**:
- [ ] Create `PermissionsTab` in Settings
- [ ] Add endpoint: `GET /api/v1/auth/permissions/effective`
  - Returns list of all permission keys
  - Marks each as granted/denied for current user
- [ ] Display in table format with filter/search
- [ ] Show role baseline and team context
- [ ] Link to permission model docs

**Files**:
- `apps/backend/api/routes/auth.py` (add endpoint)
- `apps/frontend/src/components/settings/PermissionsTab.tsx` (NEW)
- `apps/frontend/src/components/SettingsModal.tsx` (add tab)

**Acceptance**:
- ✅ User can see all effective permissions
- ✅ Clear indication of granted vs denied
- ✅ Founder rights shown as separate category

---

### 5.2 Audit Events
**Goal**: Log critical actions for security review

**Events to Log**:
- Setup wizard completion
- Hot slot assignment/eject
- Model downloads
- Permission changes
- Account creation
- Founder password verification

**Schema**:
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    action TEXT NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_user ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_event ON audit_log(event_type, timestamp DESC);
```

**Tasks**:
- [ ] Create `audit_service.py`
  - `log_event(user_id, event_type, action, details)`
  - Async logging (non-blocking)
- [ ] Add audit calls to:
  - Setup wizard completion
  - Hot slot changes (`model_manager.py`)
  - Model downloads (`setup_wizard.py`)
  - Permission grants (`permission_engine.py`)
- [ ] Create admin endpoint: `GET /api/v1/admin/audit-log`
  - Paginated, filterable
  - Requires `admin.view_audit` permission
- [ ] Basic UI in Settings (admin only)

**Files**:
- `apps/backend/api/services/audit_service.py` (NEW)
- `apps/backend/api/alembic/versions/XXX_create_audit_log.py` (NEW - migration)
- `apps/backend/api/routes/admin.py` (NEW - audit endpoint)
- `apps/frontend/src/components/settings/AuditLogTab.tsx` (NEW)

**Acceptance**:
- ✅ Critical events logged with context
- ✅ Logs queryable by admin
- ✅ No performance impact on user actions

---

## Implementation Order

### Sprint 1: Local Context & Chat
1. Local vs Team badges (1.2) - **2 hours**
2. Token usage meter (2.1) - **1 hour**
3. Per-session model selector (2.2) - **2 hours**
4. Memory fit warnings (2.3) - **1.5 hours**

**Total**: ~6.5 hours

---

### Sprint 2: Performance & Monitoring
1. Usable memory limit (3.1) - **2 hours**
2. Background cleanup (3.2) - **2 hours**
3. Metal4 activity indicator (4.1) - **1 hour**
4. Queue backlog (4.2) - **0.5 hours**

**Total**: ~5.5 hours

---

### Sprint 3: Security & RBAC
1. Permissions visualization (5.1) - **2 hours**
2. Audit logging (5.2) - **3 hours**
3. Local mode SQL queries (1.1) - **1 hour**

**Total**: ~6 hours

---

## Total Estimated Effort: 18 hours

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Local resource isolation | 100% (no team leaks) |
| Token usage visibility | Per-session meter < 1s load |
| Memory warnings | 0 OOM crashes from model loading |
| Cleanup efficiency | Disk growth < 1GB/week |
| Audit coverage | 100% of critical actions logged |
| RBAC clarity | Users understand their permissions |

---

## Dependencies

**External**:
- None (all work is local-only)

**Internal**:
- Phase 0 complete ✅
- Phase 1 complete ✅
- E2E validation ✅

---

## Rollout Plan

1. **Week 1**: Sprint 1 (Local context + Chat)
2. **Week 2**: Sprint 2 (Performance + Monitoring)
3. **Week 3**: Sprint 3 (Security + RBAC)
4. **Week 4**: Integration testing + polish

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| Memory checks may be inaccurate | Use conservative thresholds (50% for models, 75% for hot slots) |
| Audit log table growth | Implement rotation policy (archive after 1 year) |
| Cleanup service may delete active files | Add "last accessed" check before deletion |

---

## Next Phase Preview (Phase 3)

- Team context switching
- Multi-user collaboration
- Shared documents and workflows
- Team permission enforcement
- Invite/role management

---

**Phase 2 Owner**: Claude Code
**Start Date**: TBD (awaiting user approval)
**Estimated Completion**: 3 weeks
**Status**: Ready to Start
