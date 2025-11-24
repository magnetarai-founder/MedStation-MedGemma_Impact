# MagnetarStudio: macOS 26 Roadmap
**Native Mac App - Flagship Edition**

---

## Vision Statement

MagnetarStudio for macOS 26 is the **flagship showcase** of Apple's latest platform capabilities—a professional-grade, offline-first AI operating system that takes full advantage of:

- **Liquid Glass design language** - Transparent menu bar, fluid glass panels, gorgeous
- **Apple FM (Foundation Models)** - Built-in 3B on-device LLM orchestrator
- **M5 Neural Accelerators** - 4x AI performance via MLX framework
- **Metal 4** - First-class ML support, neural rendering, GPU visualization
- **Secure Enclave** - Hardware-level encryption & biometric authentication
- **Native P2P Mesh** - Network Framework + Bonjour, no external dependencies

**This is the jewel of the ball.** Professional. Powerful. Gorgeous.

---

## Product Positioning

### MagnetarStudio macOS Edition

**Target Audience:**
- Creative professionals (developers, data scientists, researchers)
- Teams requiring offline-first collaboration
- Privacy-conscious users (government, healthcare, finance)
- Power users with Mac Studios, MacBook Pros (M5, M4, M3)

**Unique Selling Points:**
1. **Offline-first AI** - Full functionality without internet
2. **Hardware-accelerated ML** - Direct access to Neural Engine via MLX
3. **Liquid Glass UI** - Most beautiful AI platform ever built
4. **Zero-knowledge security** - Keys never leave Secure Enclave
5. **Native P2P mesh** - Device-to-device collaboration without servers
6. **Metal 4 powered** - Silky smooth 60fps visualizations

**Pricing Strategy:**
- Premium pricing ($99-199/year or one-time purchase $299)
- Showcases value of native Mac development
- Sets benchmark for MagnetarPro Mac edition (enterprise, discounted)

---

## Platform-Specific Features

### macOS 26 Exclusive Capabilities

#### 1. Transparent Menu Bar
```swift
// Full-height windows with transparent menu bar
window.titlebarAppearsTransparent = true
window.titlebarSeparatorStyle = .none
window.toolbarStyle = .unified
window.backgroundColor = .clear
```

**UX Impact:**
- Display feels larger (no visual barrier)
- Content flows seamlessly to top edge
- Liquid Glass effect extends to title bar
- Professional, modern aesthetic

#### 2. Desktop Widgets Integration
```swift
// Widget for quick AI access
struct MagnetarQuickPromptWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "QuickPrompt", provider: Provider()) { entry in
            LiquidGlassWidgetView(entry: entry)
        }
        .configurationDisplayName("Quick AI Prompt")
        .description("Ask Magnetar AI from your desktop")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
```

**Features:**
- Desktop widgets for quick prompts
- Query execution from widget
- File upload via widget drop zone
- System-wide AI access

#### 3. Stage Manager & Window Management
- Full Stage Manager support
- Multiple window instances (different workspaces)
- Window tiling integration
- Snap areas for drag-and-drop organization

#### 4. Keyboard Shortcuts (Native Mac Experience)
```
⌘N - New chat session
⌘T - New database query tab
⌘O - Open file in Vault
⌘K - Quick command palette
⌘⇧F - Global search
⌘, - Settings
⌘W - Close tab
⌘⌥← → - Switch workspaces
```

#### 5. Menu Bar Integration
```swift
// Native macOS menu bar
NSMenu.setApplicationMenu() with:
- File (New, Open, Save, Export)
- Edit (Undo, Redo, Cut, Copy, Paste, Find)
- View (Workspace switcher, Zoom, Full Screen)
- Tools (Agent, Workflow Designer, Terminal)
- Window (Minimize, Zoom, Bring All to Front)
- Help (Documentation, Report Issue)
```

#### 6. Touch Bar Support (Intel MacBook Pros)
- Context-sensitive controls
- Quick model switcher
- Query execution button
- File upload shortcut

#### 7. Multi-Display Support
- Different workspaces on different displays
- Drag files between displays
- Independent window management per display

#### 8. Finder Integration
```swift
// Quick Look plugin for .magnetar files
class MagnetarQuickLookGenerator: QLPreviewProvider {
    func providePreview(for request: QLFilePreviewRequest) async throws -> QLPreviewReply {
        // Generate preview of Magnetar workflows, queries, etc.
    }
}
```

**Features:**
- Quick Look for workflow files (.magnetar-workflow)
- Finder extension for file tagging
- Share extension (share to Magnetar Vault)
- Context menu integration (right-click → Analyze in Magnetar)

#### 9. Spotlight Integration
```swift
// Index Magnetar data for Spotlight search
CSSearchableItemAttributeSet with:
- Chat conversations
- Saved queries
- Vault files
- Workflow definitions
```

**UX:**
- Search Magnetar data from Spotlight (⌘Space)
- Quick open chat sessions
- Jump to saved query by name

#### 10. Handoff & Continuity
```swift
// Handoff to/from iPad
NSUserActivity(activityType: "com.magnetar.chat")
userActivity.title = "Continue chat on Mac"
userActivity.isEligibleForHandoff = true
```

**Features:**
- Start chat on iPad, continue on Mac
- Start query on Mac, continue on iPad
- Universal Clipboard for code snippets
- AirDrop integration for file sharing

---

## Architecture Deep Dive

### SwiftUI + AppKit Hybrid Approach

**Why Hybrid?**
- **SwiftUI** - Perfect for Liquid Glass UI, modern components
- **AppKit** - Required for advanced controls (code editor, terminal, multi-window)

```swift
// Main App Structure
@main
struct MagnetarStudioApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        // Primary window (SwiftUI)
        WindowGroup {
            ContentView()
                .environment(appState)
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)

        // Settings window
        Settings {
            SettingsView()
        }

        // Menu commands
        .commands {
            MagnetarCommands()
        }
    }
}

// Advanced controls via AppKit
class CodeEditorViewController: NSViewController {
    // Use AppKit NSTextView for code editing
    // Or integrate SourceKit LSP
}
```

### State Management (Observation Framework)

**Architecture:**

```
┌─────────────────────────────────────────┐
│         App-Wide State                  │
│  (@Observable classes)                  │
├─────────────────────────────────────────┤
│ • AppState (global)                     │
│ • UserStore (auth, profile)             │
│ • NavigationStore (routing)             │
│ • SettingsStore (preferences)           │
│ • NetworkStore (connectivity)           │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│    Feature-Specific Stores              │
│  (@Observable classes)                  │
├─────────────────────────────────────────┤
│ • ChatStore (messages, sessions)        │
│ • DatabaseStore (queries, results)      │
│ • VaultStore (files, folders)           │
│ • TeamStore (channels, members)         │
│ • AgentStore (sessions, plans)          │
│ • WorkflowStore (definitions, runs)     │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│      Local Persistence                  │
│  (SwiftData + Keychain)                 │
├─────────────────────────────────────────┤
│ • SwiftData models (queries, settings)  │
│ • Keychain (JWT, encryption keys)       │
│ • UserDefaults (UI state)               │
│ • FileManager (file cache)              │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│      Backend Sync                       │
│  (URLSession + WebSocket)               │
├─────────────────────────────────────────┤
│ • REST API (localhost:8000)             │
│ • WebSocket (real-time updates)         │
│ • P2P mesh (Network Framework)          │
└─────────────────────────────────────────┘
```

**Example Store:**

```swift
import Observation
import SwiftData

@Observable
class ChatStore {
    // Published properties
    var sessions: [ChatSession] = []
    var currentSession: ChatSession?
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false

    // Dependencies (not observed)
    @ObservationIgnored
    private let apiClient: ChatAPIClient

    @ObservationIgnored
    private let appleFM: AppleFMClient

    @ObservationIgnored
    private var webSocket: WebSocketConnection?

    init(apiClient: ChatAPIClient, appleFM: AppleFMClient) {
        self.apiClient = apiClient
        self.appleFM = appleFM
    }

    @MainActor
    func sendMessage(_ text: String) async throws {
        guard let session = currentSession else { return }

        // Add user message immediately (optimistic update)
        let userMsg = ChatMessage(role: .user, content: text)
        messages.append(userMsg)

        // Route via Apple FM
        let intent = try await appleFM.classifyIntent(text)

        if intent.confidence > 0.85 && intent.complexity == .low {
            // Handle with Apple FM
            let response = try await appleFM.generate(prompt: text)
            messages.append(ChatMessage(role: .assistant, content: response))
        } else {
            // Stream from backend
            isStreaming = true
            for try await chunk in apiClient.streamMessage(text, sessionId: session.id) {
                // Update last message with streaming text
                if let lastIndex = messages.lastIndex(where: { $0.role == .assistant }) {
                    messages[lastIndex].content += chunk
                } else {
                    messages.append(ChatMessage(role: .assistant, content: chunk))
                }
            }
            isStreaming = false
        }
    }
}
```

### Modular Backend Architecture

**Goal:** Clean, maintainable Python backend ready for future React port

#### File Structure (Refactored)

```
apps/backend/
├── api/
│   ├── __init__.py
│   ├── app_factory.py              # FastAPI app creation
│   ├── config/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base configuration
│   │   ├── development.py          # Dev settings
│   │   ├── production.py           # Prod settings
│   │   └── testing.py              # Test settings
│   │
│   ├── core/                       # Core utilities
│   │   ├── __init__.py
│   │   ├── database.py             # DB session management
│   │   ├── security.py             # JWT, password hashing
│   │   ├── dependencies.py         # FastAPI dependencies
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── events.py               # Event bus
│   │
│   ├── models/                     # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── team.py
│   │   ├── vault.py
│   │   ├── workflow.py
│   │   └── chat.py
│   │
│   ├── schemas/                    # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py                 # UserCreate, UserResponse, etc.
│   │   ├── team.py
│   │   ├── vault.py
│   │   ├── workflow.py
│   │   └── chat.py
│   │
│   ├── services/                   # Business logic (REFACTORED)
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # < 400 lines
│   │   │   ├── jwt_handler.py      # Token management
│   │   │   ├── password.py         # Password hashing
│   │   │   └── permissions.py      # Permission checks
│   │   │
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # < 400 lines
│   │   │   ├── repository.py       # DB operations
│   │   │   ├── ollama_client.py    # Ollama integration
│   │   │   ├── memory.py           # Conversation memory
│   │   │   └── streaming.py        # WebSocket streaming
│   │   │
│   │   ├── vault/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # < 500 lines
│   │   │   ├── repository.py       # DB operations
│   │   │   ├── encryption.py       # File encryption
│   │   │   ├── storage.py          # File storage backend
│   │   │   ├── websocket.py        # Real-time file events
│   │   │   └── permissions.py      # File access control
│   │   │
│   │   ├── team/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          # < 500 lines
│   │   │   ├── repository.py
│   │   │   ├── permissions.py      # RBAC logic
│   │   │   ├── presence.py         # User presence tracking
│   │   │   └── channels.py         # Chat channel management
│   │   │
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py     # Main routing logic
│   │   │   ├── planner.py          # Plan generation
│   │   │   ├── context.py          # Context building
│   │   │   ├── executor.py         # Plan execution
│   │   │   ├── engines/
│   │   │   │   ├── aider.py
│   │   │   │   ├── continue.py
│   │   │   │   └── codex.py
│   │   │   └── sessions.py         # Session management
│   │   │
│   │   └── workflow/
│   │       ├── __init__.py
│   │       ├── service.py          # < 400 lines
│   │       ├── repository.py
│   │       ├── engine.py           # Execution engine
│   │       ├── scheduler.py        # Cron scheduling
│   │       └── nodes.py            # Node type definitions
│   │
│   ├── routes/                     # API endpoints
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # /api/v1/auth/*
│   │   │   ├── chat.py             # /api/v1/chat/*
│   │   │   ├── vault.py            # /api/v1/vault/*
│   │   │   ├── team.py             # /api/v1/team/*
│   │   │   ├── agent.py            # /api/v1/agent/*
│   │   │   ├── workflow.py         # /api/v1/workflow/*
│   │   │   ├── analytics.py        # /api/v1/analytics/*
│   │   │   └── admin.py            # /api/v1/admin/*
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                 # JWT validation
│   │   ├── rate_limit.py           # Rate limiting
│   │   ├── error_handler.py        # Global error handling
│   │   ├── logging.py              # Request/response logging
│   │   └── cors.py                 # CORS configuration
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py           # Input validation
│   │   ├── formatters.py           # Response formatting
│   │   ├── crypto.py               # Cryptography helpers
│   │   └── async_helpers.py        # Async utilities
│   │
│   └── migrations/                 # Alembic migrations
│       ├── alembic.ini
│       ├── env.py
│       └── versions/
│           ├── 001_initial_schema.py
│           ├── 002_add_vault_encryption.py
│           └── ...
│
├── tests/                          # Test suite
│   ├── unit/
│   │   ├── services/
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_chat_service.py
│   │   │   └── ...
│   │   └── utils/
│   │       └── test_validators.py
│   ├── integration/
│   │   ├── test_auth_flow.py
│   │   ├── test_file_upload.py
│   │   └── ...
│   ├── e2e/
│   │   └── test_complete_workflow.py
│   └── conftest.py                 # Pytest configuration
│
├── scripts/
│   ├── seed_data.py                # Generate test data
│   ├── migrate.py                  # Run migrations
│   └── backup.py                   # Backup utilities
│
├── pyproject.toml                  # Python dependencies
├── requirements.txt                # Locked dependencies
├── pytest.ini                      # Test configuration
└── README.md                       # Backend documentation
```

#### Key Principles

**1. Single Responsibility**
- Each service file < 500 lines
- Clear separation: service, repository, permissions
- Easy to understand and modify

**2. Dependency Injection**
```python
from fastapi import Depends

# Dependency
def get_chat_service(
    db: Session = Depends(get_db),
    ollama_client: OllamaClient = Depends(get_ollama_client)
) -> ChatService:
    return ChatService(db=db, ollama_client=ollama_client)

# Usage in route
@router.post("/send")
async def send_message(
    message: MessageCreate,
    chat_service: ChatService = Depends(get_chat_service),
    current_user: User = Depends(get_current_user)
):
    return await chat_service.send_message(message, current_user)
```

**3. Consistent API Responses**
```python
# utils/formatters.py

def success_response(data: Any, meta: dict = None) -> dict:
    return {
        "success": True,
        "data": data,
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": get_request_id(),
            **(meta or {})
        }
    }

def error_response(code: str, message: str, details: dict = None) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": get_request_id()
        }
    }
```

**4. Comprehensive Tests**
```python
# tests/unit/services/test_chat_service.py

import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_send_message_success():
    # Arrange
    db_mock = Mock()
    ollama_mock = AsyncMock()
    ollama_mock.generate.return_value = "AI response"

    service = ChatService(db=db_mock, ollama_client=ollama_mock)

    # Act
    result = await service.send_message(
        message="Hello",
        session_id=UUID("..."),
        user_id=UUID("...")
    )

    # Assert
    assert result.content == "AI response"
    ollama_mock.generate.assert_called_once()
```

**5. OpenAPI Documentation**
```python
# routes/v1/chat.py

@router.post(
    "/send",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="""
    Send a message to an AI chat session.

    - **message**: The text content to send
    - **session_id**: The chat session identifier
    - **model**: (Optional) Override the default model

    Returns the AI's response.
    """,
    responses={
        200: {"description": "Message sent successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"}
    }
)
async def send_message(...):
    pass
```

**Benefits:**
- Auto-generated Swagger UI at `/docs`
- TypeScript types for React (future MagnetarPro)
- Swift models for native app (via openapi-generator)
- Clear API contracts

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

#### Week 1: Project Setup & Design System

**macOS App Setup:**
- [ ] Create Xcode project (macOS 26 target, Swift 6)
- [ ] Configure build settings (Apple Silicon, macOS 26+)
- [ ] Set up Swift Package Manager dependencies
- [ ] Configure code signing & provisioning
- [ ] Set up Git repo structure

**Liquid Glass Design System:**
- [ ] Create `LiquidGlassPanel` component
  ```swift
  struct LiquidGlassPanel<Content: View>: View {
      let content: Content

      var body: some View {
          content
              .padding()
              .background(.ultraThinMaterial)
              .background(.regularMaterial.opacity(0.5))
              .cornerRadius(16)
              .shadow(color: .black.opacity(0.1), radius: 20, y: 10)
      }
  }
  ```

- [ ] Implement transparent menu bar
  ```swift
  window.titlebarAppearsTransparent = true
  window.titlebarSeparatorStyle = .none
  window.backgroundColor = .clear
  ```

- [ ] Create adaptive tinting system
- [ ] Design icon set (light, dark, tinted variants)
- [ ] Build reusable UI components library

**Deliverables:**
- Xcode project configured
- Design system components ready
- Beautiful empty app shell

#### Week 2: Authentication & Navigation

**Authentication Flow:**
- [ ] Design login/register UI (Liquid Glass)
- [ ] Implement URLSession API client
  ```swift
  class APIClient {
      private let baseURL = URL(string: "http://localhost:8000/api/v1")!
      private let session: URLSession

      func login(username: String, password: String) async throws -> AuthResponse {
          let url = baseURL.appendingPathComponent("auth/login")
          var request = URLRequest(url: url)
          request.httpMethod = "POST"
          request.setValue("application/json", forHTTPHeaderField: "Content-Type")

          let body = ["username": username, "password": password]
          request.httpBody = try JSONEncoder().encode(body)

          let (data, response) = try await session.data(for: request)

          guard let httpResponse = response as? HTTPURLResponse,
                httpResponse.statusCode == 200 else {
              throw APIError.unauthorized
          }

          return try JSONDecoder().decode(AuthResponse.self, from: data)
      }
  }
  ```

- [ ] JWT storage in Keychain (biometric-protected)
  ```swift
  class KeychainManager {
      func store(token: String, for key: String) throws {
          let data = token.data(using: .utf8)!

          let query: [String: Any] = [
              kSecClass as String: kSecClassGenericPassword,
              kSecAttrAccount as String: key,
              kSecValueData as String: data,
              kSecAttrAccessControl as String: SecAccessControlCreateWithFlags(
                  nil,
                  kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
                  [.biometryCurrentSet],
                  nil
              )!
          ]

          SecItemAdd(query as CFDictionary, nil)
      }
  }
  ```

- [ ] Biometric authentication (Face ID)
- [ ] Session management with auto-refresh

**Navigation Shell:**
- [ ] Create main tab bar (Team, Chat, Database, Kanban)
- [ ] Implement settings window
- [ ] Add menu bar commands
- [ ] Build navigation store

**Deliverables:**
- Users can log in with biometric auth
- See main app shell with tabs
- Navigate between workspaces

#### Week 3: State Management & Persistence

**@Observable Stores:**
- [ ] `UserStore` - Authentication & profile
- [ ] `NavigationStore` - Active workspace
- [ ] `SettingsStore` - Preferences
- [ ] `NetworkStore` - Connection status

**SwiftData Models:**
- [ ] `SavedQuery` model
- [ ] `AppSettings` model
- [ ] `ChatSession` model (local cache)
- [ ] Set up model container

**Deliverables:**
- State management foundation ready
- Local persistence working
- Settings persist across launches

---

### Phase 2: Core Features (Weeks 4-7)

#### Week 4: Chat Workspace

**UI Components:**
- [ ] Message list (virtualized scrolling)
- [ ] Markdown rendering with syntax highlighting
- [ ] Model selector dropdown
- [ ] Input field with send button

**Apple FM Integration:**
- [ ] Import Foundation Models framework
- [ ] Implement intent classification
- [ ] Build hybrid routing (FM vs Ollama)
- [ ] Add guided generation

**WebSocket Streaming:**
- [ ] Connect to `/api/v1/chat/stream`
- [ ] Handle streaming responses
- [ ] Typewriter effect for AI responses
- [ ] Reconnection logic

**Deliverables:**
- Functional chat with AI
- Apple FM routing lightweight tasks
- Backend Ollama handling complex tasks
- Smooth streaming responses

#### Week 5: Database Workspace

**SQL Editor:**
- [ ] Syntax highlighting (AppKit NSTextView or SourceEditor framework)
- [ ] Auto-completion for keywords
- [ ] Query history (up/down arrows)
- [ ] Format SQL button

**Query Execution:**
- [ ] Call `/api/v1/data/query`
- [ ] Display loading state
- [ ] Show results in table
- [ ] Error handling with helpful messages

**Results Table:**
- [ ] Virtualized table (lazy loading)
- [ ] Column sorting
- [ ] Column resizing
- [ ] Copy cell/row/column

**Export:**
- [ ] Excel, CSV, JSON, Parquet via backend
- [ ] Download progress indicator

**Deliverables:**
- Execute SQL queries against backend DuckDB
- View results in fast, responsive table
- Export in multiple formats

#### Week 6-7: Vault / File Management

**File Browser:**
- [ ] Hierarchical folder view (AppKit NSOutlineView)
- [ ] Grid/list toggle
- [ ] QuickLook thumbnails
- [ ] Search with filters

**Drag & Drop:**
- [ ] Drop zone with visual feedback
- [ ] Multiple file selection
- [ ] Upload progress bars

**Encryption:**
- [ ] CryptoKit AES-256-GCM encryption before upload
- [ ] Generate file keys in Secure Enclave
- [ ] Store keys in Keychain

**WebSocket Events:**
- [ ] Connect to `/api/v1/vault/ws/<user_id>`
- [ ] Real-time file updates
- [ ] User presence indicators

**File Preview:**
- [ ] QuickLook integration
- [ ] Image preview
- [ ] PDF viewer
- [ ] Code syntax highlighting

**Deliverables:**
- Upload/download files with encryption
- Browse vault with Finder-like experience
- Real-time sync across devices

---

### Phase 3: Advanced Features (Weeks 8-11)

#### Week 8: P2P Mesh Networking

**Network Framework Setup:**
```swift
import Network

class P2PMeshService: ObservableObject {
    @Published var peers: [Peer] = []
    private var browser: NWBrowser?
    private var listener: NWListener?

    func startDiscovery() {
        // Advertise service
        let parameters = NWParameters.tcp
        let txtRecord = NWTXTRecord([
            "name": deviceName,
            "id": deviceID.uuidString
        ])
        parameters.includePeerToPeer = true

        listener = try? NWListener(using: parameters)
        listener?.service = NWListener.Service(
            name: "MagnetarStudio",
            type: "_magnetar._tcp"
        )
        listener?.start(queue: .main)

        // Browse for peers
        browser = NWBrowser(
            for: .bonjour(type: "_magnetar._tcp", domain: nil),
            using: .tcp
        )
        browser?.browseResultsChangedHandler = { [weak self] results, changes in
            self?.handlePeerDiscovery(results, changes: changes)
        }
        browser?.start(queue: .main)
    }

    func connectToPeer(_ endpoint: NWEndpoint) {
        let connection = NWConnection(to: endpoint, using: .quic)
        connection.stateUpdateHandler = { state in
            // Handle connection state
        }
        connection.start(queue: .main)
    }
}
```

**Tasks:**
- [ ] Bonjour service discovery
- [ ] QUIC connections for P2P
- [ ] Direct file transfer
- [ ] Team chat channels over P2P
- [ ] User presence tracking

**Deliverables:**
- Discover nearby Macs running MagnetarStudio
- Direct device-to-device file sharing
- P2P team chat (no server needed)

#### Week 9-10: Agent Orchestration

**Apple FM Orchestrator:**
- [ ] Intent classification UI
- [ ] Plan generation display
- [ ] Context visualization (file tree)
- [ ] Approve/reject plan steps
- [ ] Execute via `/api/v1/agent/apply`
- [ ] Real-time progress updates
- [ ] Diff view for changes

**Deliverables:**
- Apple FM handles routing and planning
- User reviews multi-step plans
- Backend applies changes (Aider/Continue/Codex)
- Git-aware file modifications

#### Week 11: Workflow Designer

**Node Editor (Metal 4):**
- [ ] Canvas with pan/zoom
- [ ] Drag nodes from palette
- [ ] Connect nodes (bezier curves)
- [ ] Properties panel
- [ ] Real-time execution visualization

**Workflow Types:**
- [ ] Trigger nodes (schedule, webhook)
- [ ] Action nodes (query, API, file op)
- [ ] Logic nodes (if/else, loop)
- [ ] AI nodes (prompt, generate)

**Deliverables:**
- Visual workflow designer
- Schedule recurring workflows
- Monitor execution in real-time

---

### Phase 4: ML Acceleration & Polish (Weeks 12-14)

#### Week 12: MLX Integration

**MLX Setup:**
```swift
import MLX

class MLXEngine {
    private var embeddingModel: MLXModel?

    func loadEmbeddingModel() async throws {
        embeddingModel = try await MLXModel.load(
            "all-minilm-l6-v2",
            device: .neuralAccelerator
        )
    }

    func generateEmbedding(text: String) async throws -> [Float] {
        guard let model = embeddingModel else {
            throw MLXError.modelNotLoaded
        }

        return try await model.encode(text).toArray()
    }
}
```

**Tasks:**
- [ ] Load quantized models (4-bit, 8-bit)
- [ ] Embeddings for semantic search
- [ ] Lightweight completions
- [ ] Hybrid routing (MLX vs Ollama)

**Deliverables:**
- 4x faster inference on M5 Macs
- On-device semantic search
- Battery-efficient ML

#### Week 13: Metal 4 GPU Acceleration

**Workflow Canvas Rendering:**
```metal
#include <metal_stdlib>
using namespace metal;

vertex VertexOut nodeVertex(
    uint vertexID [[vertex_id]],
    constant NodeVertex* vertices [[buffer(0)]],
    constant Uniforms& uniforms [[buffer(1)]]
) {
    VertexOut out;
    out.position = uniforms.projectionMatrix * vertices[vertexID].position;
    return out;
}

fragment float4 nodeFragment(
    VertexOut in [[stage_in]],
    constant NodeStyle& style [[buffer(0)]]
) {
    // Render node with glass effect
    return style.glassTint;
}
```

**Tasks:**
- [ ] GPU-rendered workflow canvas (60fps)
- [ ] Real-time glass blur effects
- [ ] MetalFX smooth animations
- [ ] Data viz GPU acceleration

**Deliverables:**
- Silky smooth 60fps UI
- Gorgeous liquid glass effects
- Fast data visualizations

#### Week 14: UI Polish

**Tasks:**
- [ ] Perfect Liquid Glass materials
- [ ] Transparent menu bar refinement
- [ ] Adaptive tinting
- [ ] Smooth spring animations
- [ ] Dark mode perfection
- [ ] Accessibility (VoiceOver, Dynamic Type)
- [ ] Keyboard shortcuts
- [ ] Touch Bar controls

**Deliverables:**
- Pixel-perfect Liquid Glass design
- Accessible to all users
- Professional Mac app feel

---

### Phase 5: Testing & Launch (Weeks 15-16)

#### Week 15: Testing

**Unit Tests:**
- [ ] API client tests (80% coverage)
- [ ] State management tests
- [ ] Encryption tests
- [ ] Model tests

**UI Tests:**
- [ ] Login flow
- [ ] Chat workflow
- [ ] File upload/download
- [ ] Query execution

**Performance:**
- [ ] App launch < 1 second
- [ ] Memory < 100MB idle
- [ ] Battery < 5% per hour
- [ ] 60fps UI consistently

**Deliverables:**
- Comprehensive test suite
- Performance benchmarks met
- Zero critical bugs

#### Week 16: App Store Launch

**Preparation:**
- [ ] App Store screenshots
- [ ] Promotional video
- [ ] App description
- [ ] Privacy policy
- [ ] Code signing & notarization

**Launch:**
- [ ] TestFlight beta (100 users)
- [ ] Collect feedback
- [ ] Fix critical issues
- [ ] Submit to App Store
- [ ] 🎉 Launch!

---

## Performance Targets (macOS)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Cold Launch** | < 1 second | Time to first frame |
| **Warm Launch** | < 0.3 seconds | From dock click |
| **Memory (Idle)** | < 80MB | Instruments |
| **Memory (Active)** | < 250MB | 10 files open, chat active |
| **CPU (Idle)** | < 1% | Activity Monitor |
| **Battery Impact** | < 4% / hour | Energy Impact (low) |
| **UI Frame Rate** | 60fps locked | Metal frame time |
| **API Latency (p95)** | < 80ms | Local backend |
| **WebSocket Ping** | < 30ms | Roundtrip |
| **File Upload (10MB)** | < 1.5 seconds | Local network |
| **MLX Inference (512 tokens)** | < 800ms | M5 chip |

---

## Success Metrics

### User Experience
- **Gorgeous** - Best looking AI app on macOS
- **Fast** - Instant responses, smooth animations
- **Offline-first** - Works everywhere
- **Secure** - Hardware-level encryption
- **Professional** - Feels like a native Mac app

### Business
- **App Store Featured** - Showcased by Apple
- **5-star reviews** - User delight
- **High retention** - Daily active usage
- **Premium pricing** - $99-199/year sustainable
- **Enterprise ready** - Foundation for MagnetarPro

---

## Risk Mitigation (macOS-Specific)

| Risk | Mitigation |
|------|------------|
| **Metal 4 complexity** | Start with SwiftUI, add Metal later |
| **AppKit integration** | Use hybrid approach, test early |
| **Code editor performance** | Evaluate SourceEditor vs NSTextView vs custom |
| **Large file handling** | Streaming encryption, chunked uploads |
| **Multi-window state** | Clear state management per window |

---

## Post-Launch Roadmap

### Version 1.1 (Q1 2026)
- [ ] Siri Shortcuts integration
- [ ] Apple Script support
- [ ] Automator actions
- [ ] CLI tool for power users

### Version 1.2 (Q2 2026)
- [ ] Multi-user collaboration (enhanced)
- [ ] Advanced workflow templates
- [ ] Plugin system (Swift packages)
- [ ] Performance dashboard

### Version 2.0 (Q3 2026)
- [ ] Vision Pro support
- [ ] Advanced AI features (Apple FM 2.0)
- [ ] Enterprise SSO
- [ ] Advanced analytics

---

## Conclusion

MagnetarStudio for macOS 26 is the **flagship showcase** that demonstrates:
- Mastery of Apple's latest platform capabilities
- Professional-grade native Mac development
- Beautiful, powerful, and secure AI platform
- Foundation for MagnetarPro enterprise edition

**This is the jewel of the ball.** 💎

**Timeline:** 16 weeks from start to App Store launch
**Team:** 1-2 Swift developers + backend engineer (for refactoring)
**Outcome:** Production-ready, gorgeous native Mac app leveraging M5, Metal 4, Apple FM, and Liquid Glass design
