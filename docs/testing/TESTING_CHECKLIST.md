# Backend Integration Testing Checklist

## Test Environment Setup

### Prerequisites
- [ ] Backend server running: `cd apps/backend && ./venv/bin/python -m uvicorn api.main:app --reload`
- [ ] Ollama server running: `ollama serve`
- [ ] At least one Ollama model installed: `ollama pull qwen2.5-coder:7b`
- [ ] MagnetarStudio app built in DEBUG configuration

### Backend Health Check
```bash
# Verify backend is accessible
curl http://localhost:8000/health

# Verify Ollama is accessible
curl http://localhost:11434/api/version
```

---

## 1. Chat Messaging with Streaming SSE

### Test 1.1: Normal Streaming Flow
- [ ] Launch app, navigate to Chat workspace (Cmd+1)
- [ ] Create new chat session (Cmd+N or click "New Chat")
- [ ] Type a simple prompt: "Hello, how are you?"
- [ ] Press Enter or click Send
- [ ] **Expected:**
  - Loading indicator appears
  - Tokens stream in real-time to the assistant message
  - Message completes with "done" event
  - No placeholder "Backend integration coming soon!" message

### Test 1.2: Error Handling - Backend Down
- [ ] Stop backend server: `pkill -f uvicorn`
- [ ] Send another message
- [ ] **Expected:**
  - Error message appears (connection failed)
  - No crash
  - Previous messages remain visible

### Test 1.3: Error Handling - Invalid Model
- [ ] Restart backend
- [ ] Select a model that doesn't exist in dropdown
- [ ] Send message
- [ ] **Expected:**
  - Error from backend (model not found)
  - Error displayed to user
  - No crash

### Test 1.4: Multiple Sessions
- [ ] Create 3 different chat sessions
- [ ] Send messages in each
- [ ] Switch between sessions
- [ ] **Expected:**
  - Messages persist in correct sessions
  - No message cross-contamination

---

## 2. Setup Wizard Backend Integration

### Test 2.1: First-Time Setup (Backend Up)
- [ ] Delete app data: `rm -rf ~/Library/Application\ Support/com.magnetarstudio.app`
- [ ] Launch app
- [ ] Complete setup wizard:
  - Enter display name
  - Enter team name
  - Select preferences
  - Click "Complete Setup"
- [ ] **Expected:**
  - POST to `/api/v1/setup/complete` succeeds
  - Console shows: "Setup wizard complete: Success"
  - App transitions to main workspace

### Test 2.2: Setup with Backend Down
- [ ] Delete app data again
- [ ] Stop backend server
- [ ] Launch app and complete setup wizard
- [ ] **Expected:**
  - Console shows: "Setup wizard error: ..."
  - App still completes locally (graceful fallback)
  - No crash, transitions to main workspace

### Test 2.3: Setup Data Validation
- [ ] With backend running, complete setup
- [ ] Check backend logs for POST request
- [ ] **Expected:**
  - Request body contains displayName, teamName, preferences
  - Backend receives correct JSON format

---

## 3. Models Store Pull/Delete Operations

### Test 3.1: Model Pull Success
- [ ] Navigate to MagnetarHub (Cmd+5)
- [ ] Find a model not yet installed (e.g., "mistral")
- [ ] Click "Pull Model" or trigger pull action
- [ ] **Expected:**
  - Progress updates stream to console
  - Model appears in installed list after completion
  - Models list auto-refreshes

### Test 3.2: Model Pull - Ollama Down
- [ ] Stop Ollama: `pkill ollama`
- [ ] Try to pull a model
- [ ] **Expected:**
  - Error message about connection failure
  - No crash
  - Models list remains intact

### Test 3.3: Model Delete Success
- [ ] With Ollama running
- [ ] Select an installed model
- [ ] Click "Delete" action
- [ ] **Expected:**
  - Model removed from local array immediately (optimistic update)
  - DELETE request sent to Ollama
  - Model disappears from list

### Test 3.4: Model List Refresh
- [ ] Pull a model via CLI: `ollama pull llama3.1:8b`
- [ ] Refresh app or navigate away and back
- [ ] **Expected:**
  - New model appears in list

---

## 4. Menu Commands & Shortcuts

### Test 4.1: Workspace Navigation
- [ ] Press Cmd+1 → **Expected:** Navigate to Team workspace
- [ ] Press Cmd+2 → **Expected:** Navigate to Chat workspace
- [ ] Press Cmd+3 → **Expected:** Navigate to Database workspace
- [ ] Press Cmd+4 → **Expected:** Navigate to Kanban workspace
- [ ] Press Cmd+5 → **Expected:** Navigate to MagnetarHub workspace

### Test 4.2: New Chat Session
- [ ] In any workspace, press Cmd+N
- [ ] **Expected:**
  - Navigate to Chat workspace
  - Create new chat session
  - Focus on input field

### Test 4.3: New Database Tab
- [ ] Press Cmd+T
- [ ] **Expected:**
  - Navigate to Database workspace
  - Create new query tab
  - Ready for SQL input

### Test 4.4: File Upload
- [ ] Press Cmd+O
- [ ] **Expected:**
  - NSOpenPanel file picker appears
- [ ] Select a CSV/JSON file
- [ ] **Expected:**
  - Navigate to Database workspace
  - File uploaded and visible

### Test 4.5: Sidebar Toggle
- [ ] Press Cmd+Ctrl+S
- [ ] **Expected:** Sidebar collapses
- [ ] Press Cmd+Ctrl+S again
- [ ] **Expected:** Sidebar expands

### Test 4.6: Help Menu
- [ ] Click Help → Documentation
- [ ] **Expected:** Opens browser to docs URL
- [ ] Click Help → Report Issue
- [ ] **Expected:** Opens browser to GitHub issues
- [ ] Click Help → About MagnetarStudio
- [ ] **Expected:** Standard macOS About panel appears

### Test 4.7: Command Palette
- [ ] Trigger Command Palette (if keyboard shortcut exists)
- [ ] **Expected:** Alert/placeholder appears (future implementation)

---

## 5. Settings Actions

### Test 5.1: API Test Connection (Backend Up)
- [ ] Open Settings (Cmd+,)
- [ ] Navigate to API tab
- [ ] Ensure API Base URL is `http://localhost:8000`
- [ ] Click "Test Connection"
- [ ] **Expected:**
  - Button shows loading state
  - Success message appears (green)
  - Status text: "Connection successful"

### Test 5.2: API Test Connection (Backend Down)
- [ ] Stop backend server
- [ ] Click "Test Connection" again
- [ ] **Expected:**
  - Button shows loading state
  - Error message appears (red)
  - Status text shows connection error

### Test 5.3: Clear Cache
- [ ] Restart backend
- [ ] In Settings, navigate to appropriate section
- [ ] Click "Clear Cache"
- [ ] **Expected:**
  - Confirmation dialog or immediate action
  - Success message appears
  - App cache directory emptied
  - App continues to function

### Test 5.4: Reset Keychain
- [ ] Click "Reset Keychain"
- [ ] **Expected:**
  - Stored auth token deleted
  - Success message appears
  - No crash

### Test 5.5: MagnetarCloud Login
- [ ] Click "Login to MagnetarCloud"
- [ ] **Expected:**
  - Browser opens to auth URL
  - Or alert if URL not configured

### Test 5.6: Subscription Management
- [ ] Click "Manage Subscription"
- [ ] **Expected:**
  - Browser opens to billing URL
  - Or alert if URL not configured

---

## 6. Vault Status Check

### Test 6.1: Vault Access Allowed
- [ ] Ensure backend running with vault access enabled
- [ ] Navigate to Team workspace
- [ ] Click "Vault" tab
- [ ] **Expected:**
  - Status check runs (check console for request)
  - If 200 response: Navigate to Vault view
  - No errors, vault content loads

### Test 6.2: Vault Access Denied (403)
- [ ] Configure backend to return 403 for vault endpoint
  - Or ensure user has no vault permissions
- [ ] Click "Vault" tab again
- [ ] **Expected:**
  - Status check gets 403
  - VaultSetupModal appears
  - Error message: "Vault access denied. Setup may be required."

### Test 6.3: Vault Status - Backend Error
- [ ] Stop backend server
- [ ] Click "Vault" tab
- [ ] **Expected:**
  - Error caught gracefully
  - Console shows: "Vault status check error: ..."
  - No crash, no navigation

### Test 6.4: Vault Status - Network Timeout
- [ ] Start backend but make vault endpoint very slow (5+ seconds)
- [ ] Click "Vault" tab
- [ ] **Expected:**
  - Loading state visible
  - Eventually times out or succeeds
  - No UI freeze

---

## 7. MagnetarHub Cloud Models CRUD

### Test 7.1: Fetch Cloud Models (Endpoint Missing)
- [ ] Navigate to MagnetarHub workspace
- [ ] Select "Cloud Models" category
- [ ] **Expected:**
  - Console shows: "Failed to fetch cloud models (endpoint may not exist yet)"
  - Empty list displayed (no crash)
  - Message: "No cloud models available" or similar

### Test 7.2: Fetch Cloud Models (Endpoint Exists)
- [ ] If cloud endpoint implemented, verify it returns model list
- [ ] **Expected:**
  - Models populate in list
  - Loading state shown during fetch

### Test 7.3: Use Cloud Model Stub
- [ ] Select a cloud model (if any)
- [ ] Trigger "Use" action
- [ ] **Expected:**
  - Console logs: "Use cloud model: {id}"
  - No crash

### Test 7.4: Update Cloud Model Stub
- [ ] Trigger "Update" action on cloud model
- [ ] **Expected:**
  - Console logs: "Update cloud model: {id}"
  - No crash

### Test 7.5: Delete Cloud Model Stub
- [ ] Trigger "Delete" action on cloud model
- [ ] **Expected:**
  - Console logs: "Delete cloud model: {id}"
  - Model removed from list immediately (optimistic update)
  - No crash

### Test 7.6: Cloud Models - Auth Token
- [ ] Check console during cloud model fetch
- [ ] **Expected:**
  - In DEBUG mode: no Bearer token sent
  - In RELEASE mode: Bearer token sent if available

---

## Edge Cases & Error Recovery

### Test 8.1: Rapid Actions
- [ ] Rapidly switch workspaces (Cmd+1,2,3,4,5 repeatedly)
- [ ] **Expected:** No crashes, smooth transitions

### Test 8.2: Concurrent Operations
- [ ] Start a model pull
- [ ] Immediately send a chat message
- [ ] Switch workspaces
- [ ] **Expected:** Both operations complete, no interference

### Test 8.3: Network Interruption
- [ ] Start streaming chat message
- [ ] Disconnect WiFi mid-stream
- [ ] **Expected:**
  - Error caught gracefully
  - Partial message visible
  - No crash

### Test 8.4: Memory Pressure
- [ ] Open multiple chat sessions (10+)
- [ ] Pull multiple large models
- [ ] Switch workspaces rapidly
- [ ] **Expected:**
  - No memory leaks
  - Performance remains acceptable

---

## Regression Tests

### Test 9.1: Existing Features Still Work
- [ ] Database query execution
- [ ] Kanban board operations
- [ ] Team chat (if implemented)
- [ ] Dark mode / light mode toggle

### Test 9.2: Auth Flow (if applicable)
- [ ] Login screen appears if not authenticated
- [ ] Login with valid credentials
- [ ] Token stored and reused

---

## Performance Validation

### Test 10.1: Chat Streaming Performance
- [ ] Send prompt requesting long response (1000+ tokens)
- [ ] **Expected:**
  - Smooth token streaming
  - No UI lag
  - Memory usage stable

### Test 10.2: Models List Performance
- [ ] Install 20+ Ollama models
- [ ] Navigate to MagnetarHub
- [ ] **Expected:**
  - List loads quickly (< 2 seconds)
  - Scrolling smooth
  - Search/filter responsive

---

## Bug Report Template

If any test fails, document using this template:

```markdown
### Bug: [Short Description]

**Test:** [Test number, e.g., Test 1.2]
**Steps to Reproduce:**
1.
2.
3.

**Expected Result:**
[What should happen]

**Actual Result:**
[What actually happened]

**Console Output:**
```
[Paste relevant console logs]
```

**Environment:**
- macOS Version:
- Xcode Version:
- Backend Commit:
- Frontend Commit:

**Screenshots:**
[Attach if applicable]
```

---

## Success Criteria

All tests pass with:
- ✅ Zero crashes
- ✅ Graceful error handling
- ✅ Clear user feedback
- ✅ Console logs helpful for debugging
- ✅ No data loss or corruption
- ✅ Performance acceptable (< 2s response times)
- ✅ UI remains responsive during operations

---

## Post-Testing Actions

After validation:
1. [ ] Document any bugs found in GitHub issues
2. [ ] Update TODO_WIRING.md with completed items
3. [ ] Create PR if working on branch
4. [ ] Tag release if all tests pass
5. [ ] Update user documentation with new features
