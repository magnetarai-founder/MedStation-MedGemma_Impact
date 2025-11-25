# Chat Workspace Wiring Complete ✓

## Overview
Step 3 (Chat Workspace) has been fully implemented with SSE streaming, all endpoints, models, service layer, and state management wired to the FastAPI backend.

## Components Created

### 1. Chat Models
**Location**: `apps/native/Shared/Models/ChatModels.swift`

#### ApiChatSession (renamed to avoid SwiftData conflict)
```swift
struct ApiChatSession: Codable, Identifiable {
    let id: String
    let title: String?
    let model: String?
    let createdAt: String
    let updatedAt: String
    let messageCount: Int?
}
```

#### ApiChatMessage
```swift
struct ApiChatMessage: Codable, Identifiable {
    let id: String
    let role: String  // "user" | "assistant"
    let content: String
    let timestamp: String
    let model: String?
    let tokens: Int?
    let files: [ChatFile]?
}
```

#### ChatFile
```swift
struct ChatFile: Codable, Identifiable {
    let id: String
    let originalName: String
    let size: Int
    let type: String
}
```

#### SendMessageRequest
```swift
struct SendMessageRequest: Codable {
    let content: String
    let model: String?
    let temperature: Double?
    let topP: Double?
    let topK: Int?
    let repeatPenalty: Double?
    let systemPrompt: String?
}
```

#### TokenResponse
```swift
struct TokenResponse: Codable {
    let tokensUsed: Int
    let tokensLimit: Int?
}
```

### 2. Streaming Support in ApiClient
**Location**: `apps/native/Shared/Networking/APIClient.swift`

#### StreamingTask
```swift
struct StreamingTask {
    let task: URLSessionDataTask
    let cancel: () -> Void
}
```

#### makeStreamingTask Method
- Creates URLRequest with 300s timeout
- Auto-injects auth token
- Uses custom `StreamingDelegate` for SSE parsing
- Returns cancellable task

#### StreamingDelegate
- Buffers incoming data
- Splits by newline (`\n`)
- Parses `data:` prefixed lines
- Ignores `[START]` marker
- Extracts `{ "content": "...", "done": true|false }`
- Calls callbacks: `onContent`, `onDone`, `onError`

### 3. ChatService
**Location**: `apps/native/Shared/Services/ChatService.swift`

All endpoints wired:

| Method | Endpoint | Returns |
|--------|----------|---------|
| `listSessions()` | `GET /v1/chat/sessions` | `[ApiChatSession]` |
| `createSession(title:model:)` | `POST /v1/chat/sessions` | `ApiChatSession` |
| `uploadAttachment(sessionId:fileURL:)` | `POST /v1/chat/sessions/{id}/upload` | `ChatFile` |
| `changeModel(sessionId:model:)` | `PATCH /v1/chat/sessions/{id}/model` | `EmptyResponse` |
| `fetchTokens(sessionId:)` | `GET /v1/chat/sessions/{id}/tokens` | `TokenResponse` |
| `sendMessageStream(...)` | `POST /v1/chat/sessions/{id}/messages` | `StreamingTask` |
| `checkHealth()` | `GET /v1/chat/health` | `Bool` |

### 4. NetworkChatStore
**Location**: `apps/native/Shared/Stores/NetworkChatStore.swift`

State management with streaming message support:

#### Published State
```swift
@Published var sessions: [ApiChatSession] = []
@Published var activeSession: ApiChatSession?
@Published var messages: [ApiChatMessage] = []
@Published var streamingContent: String = ""
@Published var isSending = false
@Published var isLoading = false
@Published var error: String?
@Published var selectedModel: String = "mistral"
@Published var tokensUsed: Int = 0
@Published var tokensLimit: Int?
```

#### Public Methods
- `bootstrapSessions()` - Lists sessions, selects most recent
- `createSession(title:model:)` - Creates new chat session
- `selectSession(_:)` - Switches active session
- `uploadFile(url:)` - Uploads attachment, returns ChatFile
- `sendMessage(content:files:temperature:topP:topK:repeatPenalty:systemPrompt:)` - Sends message with streaming
- `cancelStreaming()` - Cancels active stream
- `changeModel(_:)` - Changes model for current session
- `fetchTokens()` - Updates token usage
- `checkHealth()` - Checks chat service health

#### Streaming Send Flow
1. **Upload files**: Loop through file URLs, upload each
2. **Append user message**: Add to local messages array
3. **Create request**: Build SendMessageRequest with params
4. **Start stream**:
   - `onContent`: Appends chunks to `streamingContent`
   - `onDone`: Creates final assistant message, clears streaming state, fetches tokens
   - `onError`: Sets error, clears streaming state
5. **Resume task**: Starts URLSessionDataTask

## API Endpoints Wired

### Session Management
```
GET /api/v1/chat/sessions
→ [ApiChatSession]

POST /api/v1/chat/sessions
Body: { title?: String, model?: String }
→ ApiChatSession
```

### File Upload
```
POST /api/v1/chat/sessions/{id}/upload
Content-Type: multipart/form-data
Field: file
→ ChatFile
```

### Model Management
```
PATCH /api/v1/chat/sessions/{id}/model
Body: { model: String }
→ EmptyResponse
```

### Token Tracking
```
GET /api/v1/chat/sessions/{id}/tokens
→ { tokens_used: Int, tokens_limit?: Int }
```

### Streaming Messages
```
POST /api/v1/chat/sessions/{id}/messages
Body: SendMessageRequest
Stream: data: { "content": "...", "done": false|true }
→ SSE stream
```

### Health Check
```
GET /api/v1/chat/health
→ { status: "ok" }
```

## Streaming Protocol

### Server-Sent Events (SSE) Format
```
data: [START]
data: {"content": "Hello", "done": false}
data: {"content": " world", "done": false}
data: {"content": "!", "done": true}
```

### Parsing Logic
1. Buffer incoming data
2. Split by newline (`\n`)
3. Extract lines starting with `data:`
4. Strip `data:` prefix
5. Ignore `[START]` marker
6. Parse JSON: `{ content?, done? }`
7. Append `content` to streaming buffer
8. When `done == true`, finalize message

## UI Binding Checklist

✓ **Session sidebar**:
  - List: `networkChatStore.sessions`
  - Active: `networkChatStore.activeSession`
  - Create: `networkChatStore.createSession(title:model:)`
  - Select: `networkChatStore.selectSession(_:)`

✓ **Chat window**:
  - Messages list: `networkChatStore.messages`
  - Streaming bubble: `networkChatStore.streamingContent` (append to last assistant message)
  - Send button: `networkChatStore.sendMessage(content:files:)`
  - Sending state: `networkChatStore.isSending`

✓ **Model selector**:
  - Selected: `networkChatStore.selectedModel`
  - Change: `networkChatStore.changeModel(_:)`

✓ **File picker**:
  - Upload: `networkChatStore.uploadFile(url:)` → returns `ChatFile`
  - Pass files to `sendMessage(files: [URL])`

✓ **Token meter**:
  - Used: `networkChatStore.tokensUsed`
  - Limit: `networkChatStore.tokensLimit`
  - Refresh: `networkChatStore.fetchTokens()`

✓ **Error display**:
  - Bind to: `networkChatStore.error`

## State Flow Examples

### Create Session → Send Message → Stream Response
```swift
// 1. Create session
await networkChatStore.createSession(title: "New Chat", model: "mistral")
// → activeSession set, messages cleared

// 2. Send message with files
await networkChatStore.sendMessage(
    content: "Hello AI",
    files: [fileURL],
    temperature: 0.7
)
// → uploadFile(fileURL) → userMessage appended → stream starts

// 3. Watch streaming
// streamingContent updates in real-time as chunks arrive

// 4. On done
// → assistantMessage appended, streamingContent cleared, tokens fetched
```

### Cancel Streaming
```swift
// User navigates away or stops generation
networkChatStore.cancelStreaming()
// → task cancelled, streamingContent cleared, isSending = false
```

### Change Model Mid-Session
```swift
await networkChatStore.changeModel("llama")
// → Backend updated, selectedModel = "llama"
// → Next messages use new model
```

## Error Handling

All errors surfaced via `@Published var error: String?`:
- Network errors
- 401/403 auth errors (triggers logout in ApiClient)
- Upload failures
- Stream errors
- API errors (4xx, 5xx)

UI should bind to `networkChatStore.error` for toast/banner display.

## Integration with ContentView

Add to ContentView:
```swift
@StateObject private var networkChatStore = NetworkChatStore.shared

// In .authenticated case:
MainAppView()
    .environmentObject(networkChatStore)

// On auth success:
.onChange(of: authStore.authState) { _, newState in
    if newState == .authenticated {
        Task {
            await networkChatStore.bootstrapSessions()
        }
    }
}
```

## Key Differences from Existing ChatStore

| Feature | Existing ChatStore | NetworkChatStore |
|---------|-------------------|------------------|
| Models | SwiftData (class) | API (struct) |
| Observation | `@Observable` | `ObservableObject` |
| Streaming | Not implemented | Full SSE support |
| Backend | Simulated | Real FastAPI |
| Files | Not supported | Full upload support |
| Tokens | Not tracked | Real-time tracking |
| Sessions | Local only | Server-backed |

## Next Steps

Chat workspace is fully wired with streaming! Ready for:

### Step 4: Workflows
- List: `GET /api/v1/workflows`
- Templates: `GET /api/v1/workflow/templates`
- Save/Run: `POST /api/v1/automation/save`, `POST /api/v1/automation/run`
- Queue: Work items endpoints
- Analytics: `GET /api/v1/workflows/{id}/analytics`

### Step 5: Vault
- Unlock: `POST /api/v1/vault/unlock`
- Files: `GET /api/v1/vault/files`, `GET /api/v1/vault/files/{id}/download`
- Upload: `POST /api/v1/vault/files`
- Folders: `GET /api/v1/vault/folders`, `POST /api/v1/vault/folders`

### Step 6: Settings
- Saved queries: `GET/POST/PUT/DELETE /api/v1/settings/saved-queries`
- Metal4 monitoring: `GET /api/v1/monitoring/metal4`

## Notes

- SSE streaming uses URLSessionDataDelegate for incremental parsing
- Streaming task cancellation properly cleans up session
- Auth token auto-injected with 300s timeout for long responses
- Files uploaded before message send
- Token usage fetched after each message completion
- Model changes apply to subsequent messages
- Named `NetworkChatStore` to avoid conflict with existing SwiftData-backed `ChatStore`
- All API models prefixed with `Api` (ApiChatSession, ApiChatMessage) to avoid SwiftData conflicts
- All snake_case API fields auto-converted via JSONDecoder
