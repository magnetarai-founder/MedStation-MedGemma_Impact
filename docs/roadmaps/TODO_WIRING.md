# MagnetarStudio - Backend Wiring TODO List

**Status:** PARTIALLY COMPLETE - Some items remain for future development
**Last Review:** 2025-12-27

This document tracks all unwired/mocked features that need backend integration.

## ✅ COMPLETED

### Performance
- [x] **Lazy workspace loading** - Switched from ZStack to conditional rendering (5x faster navigation)
- [x] **Model integration** - Chat and MagnetarHub now fetch real Ollama models from backend
- [x] **Auth bypass** - DEBUG mode skips authentication for rapid development

### Authentication
- [x] **Keychain bypass** - No macOS keychain prompts in DEBUG builds
- [x] **ATS configuration** - localhost HTTP exceptions added to Info.plist

## 🔴 HIGH PRIORITY - Core Functionality

### 1. Chat Messaging (ChatStore.swift:79-88)
**Status:** Completely mocked
**File:** `apps/native/Shared/Stores/ChatStore.swift`
**Current:** Returns "This is a simulated AI response"
**Needed:**
- POST to `/api/v1/chat/completions` with streaming
- Handle SSE (Server-Sent Events) for streaming responses
- Save messages to backend/local storage
- Error handling for network failures

**Backend Endpoint:** Already exists at `/api/v1/chat/completions`

### 2. Setup Wizard (SetupWizardView.swift:173)
**Status:** No backend call
**File:** `apps/native/Shared/Views/Auth/SetupWizardView.swift`
**Current:** Just marks local state as complete
**Needed:**
- POST to `/api/v1/users/me/setup/complete` with user data
- Send displayName, teamName, preferences
- Handle success/error states
- Store returned user profile

**Backend Endpoint:** Need to implement `/api/v1/users/me/setup/complete`

### 3. Models Store - Pull/Delete (ModelsStore.swift:56-65)
**Status:** Stub implementations
**File:** `apps/native/Shared/Stores/ModelsStore.swift`
**Current:** Just prints to console
**Needed:**
- `pullModel(name:)` → POST `/api/v1/models/pull` with streaming progress
- `deleteModel(name:)` → DELETE `/api/v1/models/{name}`
- Update models array after operations
- Show progress/errors in UI

**Backend Endpoints:** Check if they exist in backend

## 🟡 MEDIUM PRIORITY - User Experience

### 4. Menu Commands (MagnetarStudioApp.swift)
**Status:** Multiple TODO stubs
**File:** `apps/native/macOS/MagnetarStudioApp.swift`
**TODOs:**
- Open tabs (⌘T, ⌘W, ⌘⇧T)
- Agent workspace (⌘⇧A)
- Workflow designer (⌘⇧W)
- Command palette (⌘K)
- Help → Documentation (⌘?)
- Help → Report Issue
- Help → About

**Needed:**
- Wire to NavigationStore for workspace switching
- Open external URLs for docs/issues
- Present About panel with NSApp.orderFrontStandardAboutPanel

### 5. Settings Actions (SettingsView.swift)
**Status:** Multiple unimplemented actions
**File:** `apps/native/macOS/SettingsView.swift`
**TODOs:**
- Test API connection
- Clear cache
- Reset keychain
- Supabase auth flow
- Subscription management

**Needed:**
- API test: GET `/health` and show result
- Clear cache: Remove app caches + reset stores
- Reset keychain: Call KeychainService.deleteToken()
- Supabase: Open auth URL
- Subscriptions: Open URL or present sheet

### 6. Vault Status Check (TeamWorkspace.swift)
**Status:** Mock vault status
**File:** `apps/native/macOS/Workspaces/TeamWorkspace.swift`
**TODO:** Check vault setup status
**Needed:**
- GET `/api/v1/vault/status`
- Display real encryption status
- Disable actions until vault ready

### 7. MagnetarHub Cloud Models
**Status:** Empty stub
**File:** `apps/native/macOS/Workspaces/MagnetarHubWorkspace.swift`
**TODOs:**
- Fetch cloud models
- Use cloud model
- Update cloud model
- Delete cloud model

**Needed:**
- GET `/api/v1/cloud/models`
- POST `/api/v1/cloud/models/{id}/use`
- PUT `/api/v1/cloud/models/{id}`
- DELETE `/api/v1/cloud/models/{id}`

## 🟢 LOW PRIORITY - Backend Features

### 8. Progress Streaming (main.py)
**Status:** TODO comment
**File:** `apps/backend/api/main.py`
**Needed:** Server-Sent Events for long operations

### 9. P2P Workflow Sync (workflow_p2p_sync.py)
**Status:** Broadcast not integrated
**File:** `apps/backend/api/workflow_p2p_sync.py`
**Needed:** Integrate with p2p_chat_service

### 10. P2P Chat Features (p2p_chat_router.py)
**Status:** Missing invites/read receipts
**File:** `apps/backend/api/p2p_chat_router.py`
**Needed:** Implement invitation and read receipt system

### 11. Memory Embeddings (elohimos_memory.py)
**Status:** Cosine similarity placeholder
**File:** `apps/backend/api/elohimos_memory.py`
**Needed:** Use real embedding-based cosine similarity

## 📦 Frontend (React) - Optional

**Files with mocked APIs:**
- `apps/frontend/src/components/security/QRCodePairing.tsx`
- `apps/frontend/src/components/security/RecipientFileShare.tsx`
- `apps/frontend/src/components/security/DeviceFingerprints.tsx`
- `apps/frontend/src/components/ProfileSettings/index.tsx`
- `apps/frontend/src/components/docs/CommentSidebar.tsx`
- `apps/frontend/src/components/docs/CommentThread.tsx`
- `apps/frontend/src/components/docs/CollaborativeEditor.tsx`
- `apps/frontend/src/components/docs/MentionInput.tsx`
- `apps/frontend/src/components/docs/VersionHistory.tsx`

## 🎯 Recommended Implementation Order

1. **Chat messaging** (users will immediately notice)
2. **Models pull/delete** (completes the model management story)
3. **Menu commands** (keyboard shortcuts improve UX)
4. **Settings actions** (API test helps debugging)
5. **Setup wizard** (only seen once per user)
6. **Vault status** (team features)
7. **Cloud models** (if cloud integration is planned)
8. **Backend P2P/streaming** (advanced features)

## 📝 Notes

- All Swift files use `ApiClient.shared` for requests
- Backend runs on `http://localhost:8000`
- Ollama runs on `http://localhost:11434`
- Auth uses JWT tokens stored in KeychainService
- DEBUG builds bypass auth and keychain

## 🚀 Quick Win Opportunities

**Easiest to implement** (< 30 min each):
1. Menu commands → Just NavigationStore.navigate()
2. Settings API test → Single GET /health
3. Settings clear cache → FileManager.default.removeItem()
4. About panel → NSApp.orderFrontStandardAboutPanel()

**Medium effort** (1-2 hours each):
1. Chat messaging with streaming
2. Model pull/delete
3. Setup wizard POST

**Larger effort** (3+ hours):
1. P2P features
2. Cloud model management
3. Frontend React mocks
