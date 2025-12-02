# TASK 4: End-to-End Emergency Mode Testing Plan

**Status**: Ready for Manual Testing
**Prerequisites**: Xcode project build fix required (see below)

---

## ⚠️ PREREQUISITE: Fix Xcode Build Error

Before testing, add `APIConfiguration.swift` to the Xcode project:

1. Open `apps/native/MagnetarStudio.xcodeproj` in Xcode
2. Right-click on `Shared/Networking` folder
3. Select "Add Files to MagnetarStudio..."
4. Navigate to and select: `Shared/Networking/APIConfiguration.swift`
5. Ensure "Add to targets: MagnetarStudio" is checked
6. Click "Add"
7. Build the project (Cmd+B) - should now succeed

**Why this is needed**: APIConfiguration.swift was created in Phase 0 but wasn't added to the Xcode project file automatically.

---

## Test Environment Setup

### 1. Start Backend Server

```bash
cd /Users/indiedevhipps/Documents/MagnetarStudio/apps/backend

# Set environment variable to DISABLE actual wipe (Week 1 safety)
export ELOHIM_ALLOW_EMERGENCY_WIPE=false

# Start server
python3 -m uvicorn main:app --reload --port 8000
```

**Expected Output**:
```
⚠️  Emergency wipe DISABLED (ELOHIM_ALLOW_EMERGENCY_WIPE=false)
   This is a safety measure. Set ELOHIM_ALLOW_EMERGENCY_WIPE=true to enable.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. Launch MagnetarStudio App

In Xcode:
- Select scheme: "MagnetarStudio"
- Configuration: Debug
- Click Run (Cmd+R)

**Expected**: App launches, Console pane visible (View → Debug Area → Show Debug Area)

---

## 🧪 TEST 1: Triple-Click Panic Button

### Steps

1. In the running app, locate the panic button in the header
2. Click it once - nothing should happen
3. Click it twice quickly (< 1 second apart)
4. **Expected**: Standard panic mode modal appears (NOT emergency mode)
5. Close the modal
6. Click panic button **three times quickly** (< 1 second apart)

### Expected Result ✅

- Emergency Mode Confirmation Modal appears
- Title: "⚠️ EMERGENCY MODE ⚠️"
- Subtitle: "THIS IS IRREVERSIBLE"
- Text input field: "Type 'I UNDERSTAND' to proceed"
- Countdown timer: "Window closes in 10 seconds"
- Cancel button visible

### Console Output ✅

```
🚨 Emergency Mode triggered (triple-click)
⌨️ Key monitoring started: Cmd+Shift+Delete for 5 seconds triggers emergency mode
```

### Pass Criteria

- ✅ Modal appears after triple-click
- ✅ Modal does NOT appear after double-click
- ✅ Countdown timer is visible and counts down
- ✅ UI shows clear warnings (red borders, warning icons)

---

## 🧪 TEST 2: "I UNDERSTAND" Text Confirmation Path

### Steps

1. Triple-click panic button to open Emergency Modal
2. Type "I UNDERSTAND" (exact case) in the text field
3. **Expected**: Second confirmation screen appears automatically
4. Read the final warning
5. Click "Proceed with Emergency Mode"

### Expected Result ✅

#### Console Output - Phase 1 (Simulation Identification):

```
🧪 SIMULATION MODE: Emergency wipe started
   Reason: User-initiated

   📁 Would delete 3 vault files:
      - /Users/username/.magnetar/vault_sensitive.db
      - /Users/username/.magnetar/vault_unsensitive.db
      - /Users/username/.magnetar/app.db

   📁 Would delete 2 backup files:
      - /Users/username/.elohimos_backups/backup_2025_12_01.tar.gz.enc

   📁 Would delete 15 model files:
      - /Users/username/.magnetar/models/llama-3.2-3b.gguf
      - ...

   📁 Would delete 42 cache files:
      - /Users/username/Library/Caches/com.magnetarstudio.app/...

   📁 Would delete 5 audit log files:
      - /Users/username/.magnetar/audit.db

   📁 Would delete app bundle: /Applications/MagnetarStudio.app

   📁 Would delete 2 LaunchAgent files:
      - /Users/username/Library/LaunchAgents/com.magnetarstudio.helper.plist

   📁 Would delete 3 preference files:
      - /Users/username/Library/Preferences/com.magnetarstudio.app.plist

   📁 Would delete 1 Application Support directories:
      - /Users/username/Library/Application Support/MagnetarStudio/

   📁 Would delete 1 log directories:
      - /Users/username/Library/Logs/MagnetarStudio/

   📁 Would delete 8 temporary files:
      - /tmp/magnetar_...

✅ SIMULATION COMPLETE: 82 files identified
   Duration: 0.23s

   📊 Summary by category:
      Vaults: 3
      Backups: 2
      Models: 15
      Cache: 42
      Audit: 5
      LaunchAgents: 2
      Preferences: 3
      App Support: 1
      Logs: 1
      Temporary: 8
```

### Pass Criteria

- ✅ All 11 file categories identified
- ✅ Total file count > 0
- ✅ Console shows "SIMULATION COMPLETE"
- ✅ NO files actually deleted (verify by checking ~/.magnetar still exists)
- ✅ Duration < 1 second
- ✅ Modal closes after completion

---

## 🧪 TEST 3: Cmd+Shift+Delete 5-Second Hold Path

### Steps

1. Triple-click panic button to open Emergency Modal
2. **Do NOT type "I UNDERSTAND"**
3. Hold down: **Cmd + Shift + Delete** keys simultaneously
4. Keep holding for 5 seconds
5. Watch the progress bar fill up (red progress bar should appear)

### Expected Result ✅

#### Visual Feedback:
- Red progress bar appears below text field
- Progress bar fills from 0% to 100% over 5 seconds
- Text hint: "Or: Hold Cmd+Shift+Delete for 5 seconds"
- Progress percentage updates every 0.1 seconds

#### After 5 Seconds:
- Secondary confirmation screen appears automatically
- No need to type "I UNDERSTAND"
- Click "Proceed with Emergency Mode"

#### Console Output:
```
⏱️ Emergency key combo hold started...
   Progress: 0%
   Progress: 20%
   Progress: 40%
   Progress: 60%
   Progress: 80%
   Progress: 100%
✅ Emergency key combo held for 5 seconds - triggering emergency mode

🧪 SIMULATION MODE: Emergency wipe started
   ... (same as Test 2)
```

### Pass Criteria

- ✅ Progress bar appears when keys held
- ✅ Progress bar fills over exactly 5 seconds
- ✅ Emergency mode triggers after 5 seconds
- ✅ If keys released early (< 5s), progress bar resets
- ✅ Simulation completes successfully

---

## 🧪 TEST 4: Backend Integration (Simulation Call)

**Note**: Current implementation does NOT call backend in simulation mode. This test verifies the backend endpoint is ready for production integration.

### Steps

1. In Terminal, test backend endpoint directly:

```bash
# Get auth token (if needed)
TOKEN=$(cat ~/.magnetar/auth_token 2>/dev/null || echo "test-token")

# Call emergency endpoint (should be blocked by env var)
curl -X POST http://localhost:8000/api/v1/panic/emergency \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"confirmation": "CONFIRM", "reason": "E2E test"}'
```

### Expected Result ✅

```json
{
  "detail": "Emergency mode is disabled. Set ELOHIM_ALLOW_EMERGENCY_WIPE=true to enable."
}
```

**HTTP Status**: 403 Forbidden

### Pass Criteria

- ✅ Backend rejects request with 403
- ✅ Environment variable guard working correctly
- ✅ No files deleted on backend server

---

## 🧪 TEST 5: Error Handling - Network Failure

**Note**: Simulation mode doesn't call backend, so this test is for production readiness documentation.

### Steps (For Production Testing in Week 2)

1. Stop the backend server (Ctrl+C in terminal)
2. Trigger emergency mode via app
3. Observe error handling

### Expected Result (Week 2 Production) ✅

- Emergency mode continues despite backend failure
- Error logged: "Backend wipe failed: Connection refused"
- Local wipe proceeds (simulation in Week 1, real in production)
- User sees completion message with error note

---

## 🧪 TEST 6: Verify NO Actual Deletion (Safety Check)

### Steps

1. Before triggering emergency mode, note existing files:

```bash
ls -la ~/.magnetar/
ls -la /Applications/MagnetarStudio.app 2>/dev/null || echo "App not in /Applications"
```

2. Trigger emergency mode via any method (text or key combo)
3. Wait for "SIMULATION COMPLETE" message
4. Check files again:

```bash
ls -la ~/.magnetar/
ls -la /Applications/MagnetarStudio.app 2>/dev/null || echo "App not in /Applications"
```

### Expected Result ✅

- All files STILL EXIST
- No databases deleted
- App bundle still present
- Console shows "SIMULATION MODE" and "NO FILES DELETED"

### Pass Criteria

- ✅ Zero files deleted
- ✅ All directories intact
- ✅ App still runs after emergency mode trigger

---

## 🧪 TEST 7: Countdown Timer Behavior

### Steps

1. Triple-click panic button
2. **Do nothing** - don't type, don't press keys
3. Wait for countdown to reach 0

### Expected Result ✅

- Modal closes automatically after 10 seconds
- Console shows: "Emergency mode canceled (timeout)"
- No emergency wipe triggered

### Pass Criteria

- ✅ Modal auto-closes at 0 seconds
- ✅ No emergency action taken
- ✅ App remains functional

---

## 🧪 TEST 8: Cancel Button Behavior

### Steps

1. Triple-click panic button
2. Click "Cancel" button

### Expected Result ✅

- Modal closes immediately
- Console shows: "Emergency mode canceled by user"
- No emergency wipe triggered

### Pass Criteria

- ✅ Modal closes on cancel
- ✅ No emergency action taken
- ✅ Can trigger again if needed

---

## 📊 Test Summary Checklist

After completing all tests, verify:

| Test | Status | Notes |
|------|--------|-------|
| 1. Triple-click trigger | ⬜ | Modal appears on 3rd click |
| 2. "I UNDERSTAND" path | ⬜ | Text confirmation works |
| 3. Cmd+Shift+Delete hold | ⬜ | 5-second timer works |
| 4. Backend integration | ⬜ | Endpoint returns 403 (env var guard) |
| 5. Error handling | ⬜ | Graceful backend failure |
| 6. NO deletion safety | ⬜ | Files still exist after simulation |
| 7. Countdown timer | ⬜ | Auto-closes at 0 seconds |
| 8. Cancel button | ⬜ | Modal cancels gracefully |

**All tests must pass before proceeding to Week 2 VM testing.**

---

## 🔍 Expected File Identification by Category

Based on a typical MagnetarStudio installation:

| Category | Expected Count | Example Paths |
|----------|---------------|---------------|
| **Vault Databases** | 3-5 | `~/.magnetar/vault_*.db` |
| **Backups** | 0-10 | `~/.elohimos_backups/*.tar.gz.enc` |
| **Models** | 5-20 | `~/.magnetar/models/*.gguf` |
| **Cache** | 20-100 | `~/Library/Caches/com.magnetarstudio.app/*` |
| **Audit Logs** | 1-5 | `~/.magnetar/audit.db` |
| **App Bundle** | 1 | `/Applications/MagnetarStudio.app` |
| **LaunchAgents** | 0-3 | `~/Library/LaunchAgents/com.magnetarstudio.*.plist` |
| **Preferences** | 1-5 | `~/Library/Preferences/com.magnetarstudio.*.plist` |
| **App Support** | 1 | `~/Library/Application Support/MagnetarStudio/` |
| **Logs** | 1 | `~/Library/Logs/MagnetarStudio/` |
| **Temporary** | 5-20 | `/tmp/magnetar_*` |

**Total Expected**: 50-200 files (depends on usage)

---

## 🚨 Critical Safety Reminders

Before ANY testing:

1. ✅ Ensure `EMERGENCY_MODE_ENABLED = false` in EmergencyModeService.swift (Line 19)
2. ✅ Ensure `ELOHIM_ALLOW_EMERGENCY_WIPE=false` in backend environment
3. ✅ Verify `isSimulationMode = true` in EmergencyModeService.swift (Line 34)
4. ✅ Week 1 = Simulation ONLY, no actual deletion
5. ✅ Week 2 = VM testing with actual deletion (isolated VM only)

---

## 📝 Test Results Documentation

After completing tests, document results here:

### Test Execution Date: __________

### Test 1 Result:
- Triple-click worked: YES / NO
- Modal appeared: YES / NO
- Notes: _______________________________

### Test 2 Result:
- "I UNDERSTAND" path worked: YES / NO
- Files identified: _______ (expected: 50-200)
- Categories found: _______ (expected: 11)
- Notes: _______________________________

### Test 3 Result:
- Key combo hold worked: YES / NO
- 5-second timing accurate: YES / NO
- Progress bar visible: YES / NO
- Notes: _______________________________

### Test 6 Result (CRITICAL):
- Files deleted: YES / NO (MUST BE NO)
- All files intact: YES / NO (MUST BE YES)
- Notes: _______________________________

---

## ✅ Completion Criteria

Task 4 is complete when:

1. ✅ All 8 tests pass
2. ✅ Zero files deleted (simulation mode verified)
3. ✅ All 11 file categories identified
4. ✅ Both trigger methods work (text + key combo)
5. ✅ Console output matches expected format
6. ✅ Error handling graceful
7. ✅ Backend endpoint ready (blocked by env var)
8. ✅ Test results documented above

---

## 🚀 Next Steps After Task 4

Once all tests pass:

- **Week 2**: VM Phase 1 - Simulation testing with fake data in VM
- **Week 2**: VM Phase 2 - Actual deletion testing in isolated VM
- **Week 2**: Memory zeroing implementation
- **Week 2**: Keychain purge implementation
- **Week 2**: Self-uninstall implementation
- **Week 2**: Forensic analysis with recovery tools

---

**Status**: READY FOR MANUAL TESTING
**Safety**: All guards active, simulation mode verified
**Risk Level**: ZERO (Week 1 simulation only)

---

For His glory and the protection of His people. 🙏
