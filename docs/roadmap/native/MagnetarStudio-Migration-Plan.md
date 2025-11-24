# MagnetarStudio: Swift Migration Master Plan
**From React Web to Native macOS 26 & iPadOS 26**

---

## Executive Summary

MagnetarStudio is transitioning from a React/TypeScript web frontend to a **native Swift application** leveraging the full power of Apple's ecosystem. This document outlines the comprehensive migration strategy for the **flagship AI operating system platform**.

### Product Strategy Context

**MagnetarStudio** is the centerpiece of a three-product ecosystem:

- **MagnetarData** - Cross-platform data analytics (separate product line)
- **MagnetarStudio** - Mac + iPad native flagship (THIS PROJECT)
  - Showcase for SwiftUI mastery
  - Takes full advantage of Apple Neural Engine, Apple FM, Metal 4, MLX
  - Premium, gorgeous, liquid glass design
- **MagnetarPro** - Enterprise edition
  - Cross-platform (React/Electron)
  - Mac version: native Swift (discounted for premium experience)
  - Future expansion target for engineering team

### Migration Philosophy

**"Do it right, do it once"**

This migration prioritizes:
1. **Backend modularity** - Clean architecture for easy expansion
2. **Native excellence** - Full Apple platform integration
3. **Future-proof foundation** - Easy React port for MagnetarPro cross-platform
4. **Flagship quality** - MagnetarStudio sets the standard

---

## Current State Analysis

### Frontend (React + TypeScript)
- 212 React components
- 18 Zustand stores (state management)
- Vite build system
- Real-time collaboration via Yjs CRDT + WebSocket
- Offline-first with IndexedDB persistence
- ~50,000-60,000 lines of code

### Backend (FastAPI + Python)
- 387 Python files
- 40+ modular service routers
- SQLite + DuckDB databases
- JWT authentication (7-day tokens)
- P2P mesh networking (libp2p)
- Metal GPU acceleration (Apple Silicon)
- Ollama integration (local AI on port 11434)
- ~200,000+ lines of code

### Integration Points
- REST API (`/api/v1/*`) + WebSocket
- JWT-based authentication
- File upload/download with encryption
- Real-time sync via Yjs CRDT
- P2P mesh for offline collaboration

**Critical Decision:** Backend remains 100% intact during migration

---

## Platform Capabilities: macOS 26 & iPadOS 26

### 1. Liquid Glass Design Language

**Most significant visual overhaul since iOS 7**

- Fluid, translucent glass-like UI that reflects/refracts backgrounds
- **Completely transparent menu bar** (macOS)
- Dynamic transformation for content focus
- Unified design across all Apple platforms
- Customizable widgets, app icons with light/dark/tinted appearances
- System-wide adaptive tinting

**Why it matters:** MagnetarStudio will be GORGEOUS - perfect for pro workflows

### 2. Foundation Models Framework (Apple FM)

**Direct access to on-device 3B parameter LLM**

```swift
import FoundationModels

let model = try await FMInferenceModel()
let response = try await model.generate(prompt: userInput)
```

**Key Benefits:**
- **3 lines of Swift code** to integrate
- Works **100% offline** - perfect for offline-first architecture
- Zero inference costs, privacy-first
- Built-in guided generation & tool calling
- Native Swift support

**Use Cases:**
- Intent classification (routing)
- Quick suggestions
- Text summarization
- Inline completions
- Context extraction
- **Replaces Ollama for lightweight tasks**

### 3. Apple Neural Engine (ANE)

**M5 & A19 Pro Capabilities:**
- 16-core Neural Engine in M5 chips
- Neural Accelerators in each GPU core (M5)
- **4x AI performance** vs M4 for machine learning
- Direct API access via Core ML & MLX

**Powered Features:**
- On-device embeddings
- Semantic search
- Image processing
- Model inference
- Face detection
- Spatial reasoning

### 4. MLX Framework

**Apple's Machine Learning Framework for Apple Silicon**

```swift
import MLX
import MLXNN

let model = try MLXModel.load("mistral-7b-instruct")
let output = model.generate(prompt: userInput, maxTokens: 512)
```

**Key Features:**
- Native Swift integration
- Full access to M5 Neural Accelerators (macOS 26.2+)
- **4x performance boost** over M4 for LLM inference
- **19-27% faster** than Python implementations
- Tensor operations in Metal shading language
- Thunderbolt 5 clustering - chain Mac Studios for AI clusters

**Why it matters:** Direct hardware acceleration, no Python IPC overhead

### 5. Metal 4

**Apple Silicon-Only Graphics & Compute API**

- **First-class machine learning support** with native tensors
- Execute large networks via command line OR inline in shaders
- MetalFX Frame Interpolation & Denoising
- Full Swift compatibility
- Unified command encoder system
- Perfect for workflow visualizations, data viz, real-time effects

**New in Metal 4:**
- Neural rendering support
- Native tensor types in shading language
- Inline ML inference in shaders
- Real-time ray tracing denoiser

### 6. Native Networking APIs

**Network Framework + Bonjour**

```swift
import Network
import MultipeerConnectivity

// Auto-discovery via Bonjour
let browser = NWBrowser(for: .bonjour(type: "_magnetar._tcp", domain: nil))

// P2P connection via QUIC
let connection = NWConnection(to: endpoint, using: .quic)
```

**Benefits:**
- Zero external dependencies (replaces libp2p)
- Happy Eyeballs - automatic fastest path selection
- QUIC built-in - secure, fast
- MultipeerConnectivity - handles mesh logic
- Bluetooth + Wi-Fi Direct fallback

### 7. Secure Enclave Integration

**Hardware-Level Security**

```swift
import CryptoKit
import LocalAuthentication

// Generate key in Secure Enclave (unextractable!)
let key = SecureEnclave.P256.KeyAgreement.PrivateKey()

// Encrypt with AES-256-GCM
let sealedBox = try AES.GCM.seal(data, using: symmetricKey)
```

**Features:**
- Native biometric authentication (Face ID, Touch ID)
- Hardware-level key storage - unextractable
- CryptoKit for AES-256-GCM (replaces PyNaCl)
- Data Protection API for file-level encryption
- Keychain with biometric access control

---

## Proposed Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                  MagnetarStudio.app                         │
│              (macOS 26 / iPadOS 26)                         │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         Liquid Glass UI Layer (SwiftUI)               │ │
│  │  - Transparent menu bar (macOS)                       │ │
│  │  - Fluid glass panels with blur/refraction            │ │
│  │  - Dynamic widgets & adaptive icons                   │ │
│  │  - System-wide tints & themes                         │ │
│  │  - MetalFX animations                                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │          AI Orchestration Layer                       │ │
│  │  - Apple FM (Foundation Models) - PRIMARY             │ │
│  │  - Intent routing & planning                          │ │
│  │  - Context management                                 │ │
│  │  - Coordinates with backend Ollama for heavy lifting  │ │
│  │  - Tool calling & guided generation                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │       ML & Hardware Acceleration Layer                │ │
│  │  - MLX for model inference (M5 Neural Accelerators)   │ │
│  │  - Core ML for embeddings & semantic search           │ │
│  │  - Metal 4 for GPU compute & visualization            │ │
│  │  - Neural Engine direct API access                    │ │
│  │  - On-device inference (privacy-first)                │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │            State Management Layer                     │ │
│  │  - Observation framework (@Observable)                │ │
│  │  - SwiftData for local persistence                    │ │
│  │  - Combine for reactive streams                       │ │
│  │  - Actor isolation for concurrency (Swift 6)          │ │
│  │  - Main actor default for single-threaded safety      │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Networking Layer                         │ │
│  │  - URLSession for REST API (FastAPI backend)          │ │
│  │  - WebSocket (NWConnection + NWProtocolWebSocket)     │ │
│  │  - Network Framework for P2P mesh                     │ │
│  │  - Bonjour for zero-config device discovery           │ │
│  │  - QUIC for secure P2P file transfer                  │ │
│  │  - MultipeerConnectivity for seamless mesh            │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Security Layer                           │ │
│  │  - Secure Enclave for encryption key storage          │ │
│  │  - CryptoKit for encryption (AES-256-GCM)             │ │
│  │  - Keychain for JWT tokens & credentials              │ │
│  │  - LocalAuthentication for biometrics                 │ │
│  │  - Data Protection API for file-level encryption      │ │
│  └───────────────────────────────────────────────────────┘ │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │          Backend Communication Layer                  │ │
│  │  - FastAPI at localhost:8000                          │ │
│  │  - All /api/v1/* endpoints (UNCHANGED)                │ │
│  │  - JWT authentication (same contracts)                │ │
│  │  - WebSocket for real-time sync                       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
           ┌───────────────────────────────┐
           │   FastAPI Backend (Python)    │
           │   - 100% UNCHANGED            │
           │   - All business logic intact │
           │   - SQLite + DuckDB           │
           │   - Ollama for heavy ML       │
           │   - Agent orchestration       │
           │   - Workflow engine           │
           │   - P2P coordination          │
           └───────────────────────────────┘
```

### Technology Stack

#### Swift Application

**Core Frameworks:**
- **SwiftUI** - Primary UI layer (Liquid Glass design)
- **AppKit** - Advanced controls (code editor, terminal) on macOS
- **UIKit** - Advanced controls on iPadOS
- **Observation** - State management (Swift 6)
- **SwiftData** - Local persistence & offline cache
- **Combine** - Reactive streams for async operations

**Networking:**
- **URLSession** - REST API client for FastAPI backend
- **Network Framework** - WebSocket, P2P mesh networking
- **MultipeerConnectivity** - Simplified P2P device discovery
- **Bonjour** - Zero-configuration service discovery

**ML & Acceleration:**
- **Foundation Models Framework** - On-device 3B LLM (Apple FM)
- **MLX** - ML inference optimized for M5 Neural Accelerators
- **Core ML** - Embeddings, image processing, semantic search
- **Metal 4** - GPU compute, visualization, neural rendering
- **Create ML** - Optional model training/fine-tuning

**Security:**
- **CryptoKit** - Modern Swift cryptography (AES-256-GCM, ChaCha20-Poly1305)
- **Secure Enclave** - Hardware key storage (unextractable)
- **LocalAuthentication** - Face ID, Touch ID biometrics
- **Keychain** - Secure credential storage
- **Data Protection** - File-level encryption with hardware keys

**UI Components:**
- **swift-markdown** - Markdown rendering with syntax highlighting
- **SourceEditor** or **CodeEditor** - Code editing with LSP
- **Charts** - Data visualization (Swift Charts framework)
- **QuickLook** - Native file preview
- **PhotosUI** - Image/media picker
- **UniformTypeIdentifiers** - File type handling

**Third-Party (Minimal):**
- **Alamofire** (optional - URLSession may suffice)
- TBD: Node-based workflow editor (may build custom with Metal 4)

#### Backend (Unchanged)

- **FastAPI** - Web framework
- **SQLite** - Primary database
- **DuckDB** - Query engine
- **Ollama** - Heavy ML inference
- **libp2p** - P2P networking (coordination only)
- All existing services remain intact

---

## Key Architectural Decisions

### 1. Hybrid AI: Apple FM + Backend Ollama

**Apple FM (Foundation Models Framework) handles:**
- Intent classification & routing
- Quick suggestions & completions
- Text summarization & extraction
- Context analysis
- Inline inference (< 1 second response time)
- **Offline, zero cost, privacy-first**

**Backend Ollama handles:**
- Heavy code generation & refactoring
- Long-form AI responses
- Specialized models (Mistral, Llama, CodeLlama, etc.)
- Multi-turn complex reasoning
- **Coordinated by Apple FM as intelligent router**

**Why This Works:**
- Apple FM built into macOS 26 - instant availability
- Lightweight tasks happen instantly on-device
- Heavy tasks delegated to powerful backend
- Best of both worlds: speed + power

**Example Flow:**
```swift
// User: "Refactor this function to use async/await"

// 1. Apple FM analyzes intent (on-device, instant)
let intent = try await appleFM.classifyIntent(userInput)
// -> Intent: code_refactoring, confidence: 0.95

// 2. If lightweight, FM handles directly
if intent.confidence > 0.9 && intent.estimatedComplexity == .low {
    return try await appleFM.generate(prompt: userInput)
}

// 3. If complex, delegate to backend Ollama
else {
    let context = try await appleFM.extractContext(userInput)
    return try await backendAPI.agentRoute(
        input: userInput,
        context: context,
        suggestedModel: "codellama"
    )
}
```

### 2. Replace libp2p with Native Network Framework

**Current (Python libp2p):**
```python
from libp2p import new_host
from libp2p.peer.peerinfo import info_from_p2p_addr

host = new_host()
# Complex setup, wrapper overhead
```

**New (Swift Native):**
```swift
import Network
import MultipeerConnectivity

// Option 1: Network Framework (low-level control)
let browser = NWBrowser(for: .bonjour(type: "_magnetar._tcp", domain: nil))
browser.browseResultsChangedHandler = { results, changes in
    // Handle peer discovery
}
browser.start(queue: .main)

let connection = NWConnection(to: endpoint, using: .quic)

// Option 2: MultipeerConnectivity (high-level, easier)
let session = MCSession(peer: myPeerID, securityIdentity: nil, encryptionPreference: .required)
let browser = MCNearbyServiceBrowser(peer: myPeerID, serviceType: "magnetar")
```

**Benefits:**
- **Native Apple API** - zero external dependencies
- **Happy Eyeballs** - automatically selects fastest connection path
- **QUIC built-in** - secure, low-latency transport
- **Bluetooth + Wi-Fi Direct** - automatic fallback
- **Simpler code** - less abstraction layers
- **Better battery life** - optimized for Apple hardware

### 3. Security: CryptoKit + Secure Enclave

**Current (Python):**
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nacl.public import PrivateKey, Box

# Keys stored in filesystem
key = AESGCM.generate_key(bit_length=256)
```

**New (Swift):**
```swift
import CryptoKit

// Generate encryption key in Secure Enclave (UNEXTRACTABLE)
let privateKey = try SecureEnclave.P256.KeyAgreement.PrivateKey()

// Derive symmetric key for file encryption
let symmetricKey = SymmetricKey(size: .bits256)

// Encrypt file with AES-256-GCM
let sealedBox = try AES.GCM.seal(fileData, using: symmetricKey)

// Store key in Keychain with biometric protection
let query: [String: Any] = [
    kSecClass: kSecClassKey,
    kSecAttrApplicationTag: "com.magnetar.vault.key",
    kSecValueData: symmetricKey.dataRepresentation,
    kSecAttrAccessControl: SecAccessControlCreateWithFlags(
        nil,
        kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        [.biometryCurrentSet, .privateKeyUsage],
        nil
    )!
]
SecItemAdd(query as CFDictionary, nil)
```

**Security Benefits:**
- Keys **never leave Secure Enclave** hardware
- Biometric unlock required (Face ID / Touch ID)
- Hardware-level protection against extraction
- Zero-knowledge architecture possible
- Automatic key rotation support
- Compliance-ready (HIPAA, SOC2, etc.)

### 4. State Management: Observation Framework

**Current (React + Zustand):**
```typescript
const useUserStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      login: async (credentials) => { /* ... */ }
    }),
    { name: 'user-storage' }
  )
)
```

**New (Swift Observation):**
```swift
import Observation

@Observable
class UserStore {
    var user: User?
    var isAuthenticated: Bool = false

    @ObservationIgnored
    @Dependency(\.apiClient) private var apiClient

    @ObservationIgnored
    @Dependency(\.keychain) private var keychain

    @MainActor
    func login(username: String, password: String) async throws {
        let response = try await apiClient.login(username: username, password: password)

        // Store token in Keychain (biometric-protected)
        try keychain.store(token: response.token, for: "jwt")

        self.user = response.user
        self.isAuthenticated = true
    }
}

// Usage in SwiftUI - automatic view updates
struct ContentView: View {
    @Environment(UserStore.self) private var userStore

    var body: some View {
        if userStore.isAuthenticated {
            MainAppView()
        } else {
            LoginView()
        }
    }
}
```

**Benefits:**
- **Native to Swift 6** - no external dependencies
- **Compile-time safety** - type checking catches errors early
- **Actor isolation** - thread-safe by design
- **Automatic view updates** - SwiftUI observes changes
- **Testable** - dependency injection makes testing easy
- **Performance** - optimized by compiler

### 5. Local Persistence: SwiftData + SQLite

**For App State (queries, settings, UI state):**
```swift
import SwiftData

@Model
class SavedQuery {
    @Attribute(.unique) var id: UUID
    var sql: String
    var name: String
    var createdAt: Date
    var tags: [String]
    var folder: String?

    init(sql: String, name: String, tags: [String] = []) {
        self.id = UUID()
        self.sql = sql
        self.name = name
        self.createdAt = Date()
        self.tags = tags
    }
}

// Automatic persistence to disk
@Query(sort: \SavedQuery.createdAt, order: .reverse)
var savedQueries: [SavedQuery]
```

**For Backend Data:**
- Backend continues using SQLite databases
- Swift app queries via REST API (`/api/v1/*`)
- **Optional:** Local SQLite cache for offline read access
- SwiftData models mirror backend schemas for offline-first UX

**Sync Strategy:**
- Changes made in app → sent to backend API → persisted to backend SQLite
- Local SwiftData cache updated optimistically
- Conflict resolution handled by backend (existing CRDT logic)
- P2P mesh syncs via backend coordination

### 6. MLX for On-Device Inference

**Replace Python ML pipeline with Swift MLX:**

```swift
import MLX
import MLXNN

class LocalInferenceEngine {
    private var model: MLXModel?

    func loadModel(name: String) async throws {
        // Load quantized model optimized for M5
        self.model = try await MLXModel.load(
            name,
            quantization: .bits4, // 4-bit quantization for speed
            device: .gpu // Use Neural Accelerators
        )
    }

    func generate(prompt: String, maxTokens: Int = 512) async throws -> String {
        guard let model = model else {
            throw InferenceError.modelNotLoaded
        }

        let output = try await model.generate(
            prompt: prompt,
            maxTokens: maxTokens,
            temperature: 0.7,
            topP: 0.9
        )

        return output.text
    }
}
```

**Benefits:**
- **19-27% faster** than Python implementation (M5 vs M4 benchmarks)
- **4x peak AI performance** with M5 Neural Accelerators
- **Zero IPC overhead** - no FastAPI calls for lightweight inference
- **Battery efficient** - optimized for Apple Silicon power management
- **Can still delegate to backend Ollama** for heavy models

**Use Cases:**
- Embeddings for semantic search
- Quick code completions
- Text summarization
- Intent classification
- Context extraction

---

## Migration Phases

### Phase 1: Foundation (2-3 weeks)
**Goal: Basic Swift app with authentication**

#### Tasks

**1.1 Project Setup**
- [ ] Create macOS 26 + iPadOS 26 SwiftUI app targets
- [ ] Configure build settings for Apple Silicon
- [ ] Set up Swift Package Manager dependencies
- [ ] Configure Xcode project structure
- [ ] Set up development certificates & provisioning

**1.2 Liquid Glass Design System**
- [ ] Implement transparent menu bar (macOS)
- [ ] Create reusable glass panel components
- [ ] Set up system-wide tinting & themes
- [ ] Implement Material effects (ultra-thin, regular, thick)
- [ ] Create adaptive icon system
- [ ] Design fluid transition animations

**1.3 Authentication Flow**
- [ ] Design login/register UI (Liquid Glass styling)
- [ ] Implement URLSession API client for `/api/v1/auth/*`
- [ ] JWT token storage in Keychain (biometric-protected)
- [ ] Session management with auto-refresh
- [ ] Biometric enrollment (Face ID / Touch ID)
- [ ] Device fingerprinting

**1.4 Navigation Shell**
- [ ] Create main tab navigation (Team, Chat, Database, Kanban)
- [ ] Implement settings modal
- [ ] Add navigation state persistence
- [ ] Design tab bar with Liquid Glass effects
- [ ] Create adaptive sidebar (macOS) / tab bar (iPadOS)

**1.5 State Management**
- [ ] Create @Observable stores:
  - `UserStore` - Authentication & profile
  - `NavigationStore` - Active tab & routing
  - `SettingsStore` - App preferences
  - `NetworkStore` - Connection status
- [ ] Set up dependency injection system
- [ ] Configure SwiftData model container
- [ ] Implement local persistence for settings

**Deliverable:** ✅ User can log in, see app shell, navigate tabs

---

### Phase 2: Core Features (3-4 weeks)
**Goal: Chat, Database, File Management functional**

#### 2.1 Chat Workspace

**Tasks:**
- [ ] **Message List View**
  - Virtualized scrolling (LazyVStack)
  - Markdown rendering with syntax highlighting
  - Code blocks with copy button
  - Auto-scroll to bottom on new messages
  - Pull-to-refresh for history

- [ ] **Apple FM Integration**
  - Import Foundation Models framework
  - Implement intent classification
  - Create hybrid routing (FM vs backend)
  - Add guided generation for completions
  - Tool calling for agent actions

- [ ] **Model Selector**
  - Dropdown with available models
  - Ollama status indicator
  - Model capabilities display
  - Per-conversation model switching

- [ ] **Message Streaming**
  - WebSocket connection for real-time responses
  - Streaming text display (typewriter effect)
  - Cancel generation support
  - Reconnection logic with exponential backoff

- [ ] **Message Actions**
  - Copy message
  - Regenerate response
  - Edit user message
  - Delete conversation
  - Export conversation (Markdown, PDF)

**API Integration:**
```swift
// Chat API client
class ChatAPIClient {
    func sendMessage(_ message: String, sessionId: UUID, model: String) async throws -> ChatResponse
    func streamMessage(_ message: String, sessionId: UUID) -> AsyncThrowingStream<String, Error>
    func getSessions() async throws -> [ChatSession]
    func deleteSession(_ id: UUID) async throws
}
```

#### 2.2 Database Workspace

**Tasks:**
- [ ] **SQL Editor**
  - Syntax highlighting (AppKit NSTextView or SourceEditor)
  - Auto-completion for SQL keywords
  - Query history navigation (up/down arrows)
  - Multi-query support (split by semicolon)
  - Format SQL button

- [ ] **Query Execution**
  - Execute via `/api/v1/data/query`
  - Loading state with progress indicator
  - Error display with helpful messages
  - Execution time tracking

- [ ] **Results Table**
  - Lazy loading for large datasets
  - Column sorting (tap header)
  - Column resizing (drag header edge)
  - Row selection (multi-select)
  - Copy cell / row / column
  - Virtualized scrolling (Table on macOS, List on iPadOS)

- [ ] **Export Options**
  - Excel (.xlsx) via backend
  - CSV (.csv)
  - TSV (.tsv)
  - JSON (.json)
  - Parquet (.parquet)
  - Copy to clipboard

- [ ] **Query Library**
  - SwiftData models for saved queries
  - Folder organization
  - Tagging system
  - Search saved queries
  - Quick run from library

**API Integration:**
```swift
class DataAPIClient {
    func executeQuery(_ sql: String, limit: Int?) async throws -> QueryResult
    func exportResults(_ queryId: UUID, format: ExportFormat) async throws -> Data
    func getQueryHistory() async throws -> [QueryHistoryItem]
    func saveQuery(_ query: SavedQuery) async throws
}
```

#### 2.3 Vault / File Management

**Tasks:**
- [ ] **File Browser**
  - Hierarchical folder navigation (OutlineView on macOS, List on iPadOS)
  - Grid / List view toggle
  - File icons with QuickLook thumbnails
  - Sorting (name, date, size, type)
  - Search with filters

- [ ] **Drag & Drop Upload**
  - Drop zone with visual feedback
  - Multiple file selection
  - Upload progress indicators
  - Batch upload support

- [ ] **Encryption Before Upload**
  - CryptoKit AES-256-GCM encryption
  - Generate file-specific keys
  - Store keys in Keychain (Secure Enclave)
  - Metadata encryption

- [ ] **WebSocket Real-Time Events**
  - Connect to `/api/v1/vault/ws/<user_id>`
  - Handle file_event (uploaded, deleted, renamed)
  - Update UI in real-time
  - Presence indicators (who's viewing what)

- [ ] **File Preview**
  - QuickLook integration for native preview
  - Image thumbnails
  - PDF preview
  - Video playback
  - Code syntax highlighting

- [ ] **File Operations**
  - Download (decrypt on client)
  - Rename
  - Move to folder
  - Delete (move to trash)
  - Restore from trash
  - Share via P2P

**API Integration:**
```swift
class VaultAPIClient {
    func uploadFile(_ data: Data, name: String, folderId: UUID?) async throws -> VaultFile
    func downloadFile(_ id: UUID) async throws -> Data
    func listFiles(folder: UUID?) async throws -> [VaultFile]
    func deleteFile(_ id: UUID) async throws
    func renameFile(_ id: UUID, newName: String) async throws
}
```

**Deliverable:** ✅ Core workflows functional - chat with AI, execute SQL queries, manage files

---

### Phase 3: Advanced Features (3-4 weeks)
**Goal: Team collaboration, P2P mesh, agent orchestration, workflows**

#### 3.1 Team Workspace & P2P Mesh

**Tasks:**
- [ ] **P2P Discovery (Bonjour)**
  - Network Framework browser for `_magnetar._tcp`
  - Advertise local device as Bonjour service
  - Display discovered peers with metadata
  - Connection state indicators

- [ ] **MultipeerConnectivity Integration**
  - MCSession for mesh networking
  - Automatic peer-to-peer connections
  - Bluetooth + Wi-Fi Direct fallback
  - Handle join/leave events

- [ ] **Team Chat Channels**
  - Create/join channels
  - Send messages over P2P
  - Message persistence (SwiftData)
  - Sync with backend for offline peers
  - Typing indicators

- [ ] **User Presence**
  - Online/offline status
  - Last seen timestamp
  - Currently viewing file/workspace
  - Active indicator

- [ ] **P2P File Sharing**
  - Direct file transfer via QUIC
  - Progress tracking
  - Resume interrupted transfers
  - Encryption in transit (TLS 1.3)

**Network Framework P2P:**
```swift
class P2PMeshService {
    private var browser: NWBrowser?
    private var listener: NWListener?
    private var connections: [UUID: NWConnection] = [:]

    func startDiscovery() {
        browser = NWBrowser(for: .bonjour(type: "_magnetar._tcp", domain: nil), using: .quic)
        browser?.browseResultsChangedHandler = { [weak self] results, changes in
            self?.handleDiscoveryResults(results, changes: changes)
        }
        browser?.start(queue: .main)
    }

    func connectToPeer(_ endpoint: NWEndpoint) {
        let connection = NWConnection(to: endpoint, using: .quic)
        connection.start(queue: .main)
        // Handle connection state changes
    }
}
```

#### 3.2 Agent Orchestration

**Tasks:**
- [ ] **Intent Routing UI**
  - User input field with Apple FM suggestions
  - Confidence indicator for classification
  - Route display (which engine will handle this)
  - Model recommendation

- [ ] **Plan Generation**
  - Call `/api/v1/agent/plan`
  - Display multi-step plan in expandable cards
  - Show estimated complexity & time
  - Edit plan steps before execution

- [ ] **Context Visualization**
  - File tree of relevant context
  - Code snippets included in context
  - Token count estimation
  - Add/remove context files

- [ ] **Execution & Application**
  - Call `/api/v1/agent/apply` with approved plan
  - Real-time progress updates via WebSocket
  - Diff view for file changes
  - Approve/reject individual changes
  - Rollback support

- [ ] **Session Management**
  - List all agent sessions
  - Resume previous session
  - Session history & logs
  - Export session report

**Apple FM Orchestrator:**
```swift
class AgentOrchestrator {
    private let appleFM: FMInferenceModel
    private let backendAPI: AgentAPIClient

    func routeIntent(_ userInput: String, cwd: String) async throws -> AgentIntent {
        // Use Apple FM for fast intent classification
        let intent = try await appleFM.classifyIntent(userInput)

        if intent.confidence < 0.85 {
            // Fallback to backend for complex routing
            return try await backendAPI.route(userInput, cwd: cwd)
        }

        return intent
    }

    func generatePlan(_ intent: AgentIntent, context: [String]) async throws -> AgentPlan {
        // For lightweight plans, use Apple FM
        if intent.estimatedComplexity == .low {
            return try await appleFM.generatePlan(intent: intent, context: context)
        }

        // For complex plans, use backend
        return try await backendAPI.plan(intent: intent, context: context)
    }
}
```

#### 3.3 Workflow Designer

**Tasks:**
- [ ] **Node-Based Editor**
  - Canvas with pan & zoom (Metal 4 rendering)
  - Drag nodes from palette
  - Connect nodes (visual bezier curves)
  - Delete nodes/connections
  - Undo/redo support

- [ ] **Node Types**
  - Trigger nodes (schedule, webhook, file watch)
  - Action nodes (query, API call, file operation)
  - Logic nodes (condition, loop, transform)
  - AI nodes (prompt, classify, generate)

- [ ] **Properties Panel**
  - Node configuration
  - Input/output mapping
  - Validation rules
  - Test node individually

- [ ] **Execution Visualization**
  - Real-time node highlighting during run
  - Success/error indicators
  - Execution logs per node
  - Performance metrics

- [ ] **Schedule Management**
  - Cron expression builder
  - One-time vs recurring
  - Enable/disable workflows
  - Execution history

**Workflow Rendering (Metal 4):**
```swift
import Metal
import MetalKit

class WorkflowCanvasRenderer: NSObject, MTKViewDelegate {
    private var device: MTLDevice
    private var commandQueue: MTLCommandQueue

    func draw(in view: MTKView) {
        // Use Metal 4 for smooth 60fps canvas rendering
        // Bezier curves for connections
        // Node shadows and glass effects
        // GPU-accelerated pan/zoom
    }
}
```

#### 3.4 Settings & Admin

**Tasks:**
- [ ] **Settings Tabs (15+ tabs)**
  - General, Appearance, Security
  - Models, API Keys, Integrations
  - Backup/Restore, Privacy
  - Permissions, Audit Logs
  - Advanced, Developer

- [ ] **Biometric Enrollment**
  - Enable Face ID / Touch ID
  - Configure access policies
  - Test biometric unlock

- [ ] **Permission Management**
  - Role-based access control (RBAC)
  - User roles (founder, admin, member)
  - Permission sets
  - Team-level policies

- [ ] **Audit Log Viewer**
  - Filterable log table
  - Search by user, action, date
  - Export logs (CSV, JSON)
  - Real-time log streaming

- [ ] **Backup & Restore**
  - Full system backup
  - Selective restore
  - Encrypted backup files
  - Schedule automatic backups

**Deliverable:** ✅ Full feature parity with React app

---

### Phase 4: ML Acceleration & Polish (2-3 weeks)
**Goal: Leverage M5 Neural Accelerators, Metal 4, Core ML**

#### 4.1 MLX Integration

**Tasks:**
- [ ] **Model Loading**
  - Download quantized models (4-bit, 8-bit)
  - Load into MLX framework
  - Optimize for M5 Neural Accelerators
  - Model caching & versioning

- [ ] **On-Device Inference**
  - Lightweight completions (< 512 tokens)
  - Embeddings for semantic search
  - Text summarization
  - Code analysis & suggestions

- [ ] **Hybrid Inference Router**
  - Classify task complexity (Apple FM)
  - Route lightweight → MLX
  - Route heavy → backend Ollama
  - Fallback logic if MLX fails

- [ ] **Performance Monitoring**
  - Inference time tracking
  - Memory usage
  - Battery impact
  - Model accuracy metrics

**MLX Inference Engine:**
```swift
import MLX

class MLXInferenceEngine {
    private var embeddingModel: MLXModel?
    private var completionModel: MLXModel?

    func loadModels() async throws {
        // Load embedding model for semantic search
        embeddingModel = try await MLXModel.load(
            "all-minilm-l6-v2",
            device: .neuralAccelerator // Use M5 Neural Accelerators
        )

        // Load small completion model for quick tasks
        completionModel = try await MLXModel.load(
            "mistral-7b-instruct-q4", // 4-bit quantized
            device: .neuralAccelerator
        )
    }

    func generateEmbedding(text: String) async throws -> [Float] {
        guard let model = embeddingModel else {
            throw MLXError.modelNotLoaded
        }

        let embedding = try await model.encode(text)
        return embedding.toArray()
    }
}
```

#### 4.2 Metal 4 Compute & Visualization

**Tasks:**
- [ ] **Workflow Canvas GPU Acceleration**
  - Metal 4 rendering for node editor
  - Smooth pan/zoom at 60fps
  - Real-time connection drawing
  - Node shadow effects

- [ ] **Data Visualization**
  - GPU-accelerated charts (large datasets)
  - Real-time graph updates
  - Interactive visualizations

- [ ] **Glass Effects**
  - Real-time blur & refraction
  - Dynamic tinting based on content
  - Smooth transitions (MetalFX)
  - Background reflection

**Metal 4 Shader Example:**
```metal
#include <metal_stdlib>
using namespace metal;

// Liquid Glass blur shader
fragment float4 liquidGlassFragment(
    VertexOut in [[stage_in]],
    texture2d<float> colorTexture [[texture(0)]],
    constant float &blurRadius [[buffer(0)]]
) {
    // Sample background with gaussian blur
    // Apply refraction based on viewing angle
    // Add dynamic tint overlay
    return glassTint * blurredBackground;
}
```

#### 4.3 Core ML Integration

**Tasks:**
- [ ] **Semantic Search**
  - Generate embeddings for all files
  - Vector database (FAISS or custom)
  - Similarity search
  - Re-rank results

- [ ] **Image Processing**
  - Face detection for profile photos
  - Image classification for file tagging
  - OCR for scanned documents
  - Thumbnail generation

- [ ] **On-Device Analysis**
  - Code quality scoring
  - Security vulnerability detection
  - Performance profiling hints
  - Auto-tagging suggestions

**Core ML Embeddings:**
```swift
import CoreML

class SemanticSearchEngine {
    private var embeddingModel: MLModel?

    func searchFiles(query: String, files: [VaultFile]) async throws -> [VaultFile] {
        // Generate query embedding
        let queryEmbedding = try await generateEmbedding(text: query)

        // Compare with file embeddings
        let scores = files.map { file in
            cosineSimilarity(queryEmbedding, file.embedding)
        }

        // Return top results
        return zip(files, scores)
            .sorted { $0.1 > $1.1 }
            .prefix(20)
            .map { $0.0 }
    }
}
```

#### 4.4 UI Polish

**Tasks:**
- [ ] **Liquid Glass Refinements**
  - Perfect material effects (ultra-thin, regular, thick)
  - Transparent menu bar on macOS
  - Adaptive tinting based on wallpaper
  - Dynamic frosting on scroll

- [ ] **Smooth Transitions**
  - MetalFX frame interpolation
  - Spring animations everywhere
  - Fluid navigation
  - Contextual zooms

- [ ] **Adaptive Layouts**
  - Responsive to window resizing (macOS)
  - iPad multitasking support (Split View, Slide Over)
  - Keyboard shortcuts (macOS)
  - Touch gestures (iPadOS)

- [ ] **Dark Mode Perfection**
  - System appearance integration
  - Automatic switching
  - Custom tints for dark mode
  - OLED-optimized blacks (iPad Pro)

- [ ] **Accessibility**
  - VoiceOver support
  - Dynamic Type (text scaling)
  - Reduced Motion mode
  - High Contrast mode
  - Keyboard navigation

**Deliverable:** ✅ Gorgeous, blazing fast, fully native app leveraging all Apple platform capabilities

---

### Phase 5: Testing & Optimization (2 weeks)
**Goal: Production-ready, App Store submission**

#### 5.1 Testing

**Tasks:**
- [ ] **Unit Tests (XCTest)**
  - API client tests
  - State management tests
  - Encryption/decryption tests
  - Model serialization tests
  - 80%+ code coverage

- [ ] **UI Tests**
  - Critical user flows (login, chat, query, upload)
  - Accessibility testing
  - Snapshot testing for visual regressions

- [ ] **Integration Tests**
  - End-to-end workflows
  - P2P mesh connectivity
  - WebSocket reconnection
  - Offline-first scenarios

- [ ] **Performance Tests**
  - App launch time (< 1 second)
  - Memory usage (< 100MB idle)
  - Battery impact (< 5% per hour active use)
  - Large dataset handling (1M+ rows)

#### 5.2 Optimization

**Tasks:**
- [ ] **Performance Profiling (Instruments)**
  - Time Profiler - identify bottlenecks
  - Allocations - memory leaks
  - Energy Log - battery impact
  - Network - API call efficiency

- [ ] **Memory Optimization**
  - Reduce allocations
  - Lazy loading for images
  - Virtualized lists
  - Cache management

- [ ] **Battery Optimization**
  - Reduce CPU wakeups
  - Coalesce network requests
  - Optimize WebSocket keepalive
  - Background task efficiency

- [ ] **Startup Optimization**
  - Defer non-critical initialization
  - Parallelize loading
  - Optimize asset loading
  - Pre-warm caches

#### 5.3 Security Audit

**Tasks:**
- [ ] **Code Review**
  - Input validation
  - SQL injection prevention (backend, but verify client)
  - XSS prevention in Markdown rendering
  - CSRF token validation

- [ ] **Encryption Audit**
  - Verify Secure Enclave usage
  - Key rotation policies
  - Biometric access control
  - Data Protection API usage

- [ ] **Network Security**
  - TLS 1.3 enforcement
  - Certificate pinning (optional)
  - JWT validation
  - API rate limiting

#### 5.4 Offline-First Validation

**Tasks:**
- [ ] **Offline Scenarios**
  - App works without internet
  - Local data fully accessible
  - Changes queue for sync
  - P2P mesh works offline

- [ ] **Sync Testing**
  - Conflict resolution
  - Merge strategies
  - Data integrity checks

- [ ] **P2P Mesh Stress Testing**
  - 10+ devices in mesh
  - Large file transfers
  - Network interruptions
  - Reconnection logic

#### 5.5 App Store Preparation

**Tasks:**
- [ ] **App Store Assets**
  - App icon (all sizes)
  - Screenshots (macOS, iPadOS)
  - Promotional graphics
  - App preview video

- [ ] **Metadata**
  - App description
  - Keywords for SEO
  - Privacy policy
  - Support URL

- [ ] **App Store Review Preparation**
  - Demo account credentials
  - Feature explanations
  - Compliance documentation (encryption export, privacy)

- [ ] **Distribution**
  - Code signing
  - Notarization (macOS)
  - TestFlight beta testing
  - Final submission

**Deliverable:** ✅ Ship-ready macOS 26 + iPadOS 26 app, submitted to App Store

---

## Architecture Comparison

| Aspect | Current (React) | New (Swift Native) |
|--------|----------------|-------------------|
| **UI Framework** | React 18 + TypeScript | SwiftUI + AppKit/UIKit |
| **Design Language** | Custom CSS/Tailwind | Liquid Glass (macOS 26) |
| **State Management** | Zustand (localStorage) | Observation framework |
| **Persistence** | IndexedDB | SwiftData + Keychain |
| **HTTP Client** | Axios | URLSession |
| **WebSocket** | Browser WebSocket API | NWConnection (Network Framework) |
| **P2P Networking** | libp2p (Python backend) | Network Framework + MultipeerConnectivity |
| **Encryption** | PyNaCl (Python backend) | CryptoKit + Secure Enclave |
| **AI Orchestrator** | N/A | **Apple FM (3B on-device LLM)** ✨ |
| **ML Inference** | Ollama (backend only) | **MLX + Ollama (hybrid)** ✨ |
| **GPU Compute** | Metal via Python PyObjC | **Metal 4 native** ✨ |
| **Neural Engine** | Indirect (via Ollama) | **Direct ANE API access** ✨ |
| **Build Tool** | Vite | Xcode + Swift PM |
| **Bundle Size** | ~10MB gzipped | ~50MB native binary |
| **Startup Time** | ~2-3 seconds | **~0.5 seconds** ⚡ |
| **Memory Usage** | ~200MB (web view) | **~80MB (native)** ⚡ |
| **Offline-First** | Yes (IndexedDB) | **Yes (SwiftData + SQLite)** ✅ |
| **Biometric Auth** | WebAuthn (limited) | **Native Face ID/Touch ID** ✨ |
| **File Encryption** | AES (Python backend) | **Secure Enclave (unextractable keys)** ✨ |

---

## Backend Modularity Strategy

### Current Backend Structure

**Strengths:**
- 40+ modular routers (good separation)
- Service-based architecture
- Clear API boundaries

**Areas for Improvement:**
- Some services are large (2,000+ lines)
- Tight coupling in places
- Inconsistent error handling
- Limited documentation for cross-platform reuse

### Proposed Backend Refactoring

**Goal: Make backend so clean that future React team says "damn, this is solid"**

#### 1. Service Layer Refactoring

**Current:**
```
apps/backend/api/
  - services/
    - team/core.py (2,872 lines) ❌ Too large
    - vault/core.py (2,780 lines) ❌ Too large
    - chat/core.py (1,751 lines) ❌ Too large
```

**Proposed:**
```
apps/backend/api/
  - services/
    - team/
      - __init__.py
      - models.py          # Pydantic models
      - repository.py      # Database operations
      - service.py         # Business logic (< 500 lines)
      - permissions.py     # Authorization logic
      - events.py          # Event handlers
      - schemas.py         # API request/response schemas
    - vault/
      - models.py
      - repository.py
      - encryption.py      # Crypto operations
      - service.py
      - websocket.py       # Real-time updates
      - permissions.py
      - events.py
      - schemas.py
    - chat/
      - models.py
      - repository.py
      - service.py
      - ai_integration.py  # Ollama/model management
      - memory.py          # Conversation memory
      - schemas.py
```

**Benefits:**
- Each file < 500 lines (easier to understand)
- Clear separation of concerns
- Easy to test in isolation
- Simple for new engineers to navigate
- Ready for React/Electron port

#### 2. Standardized API Patterns

**Create consistent patterns across all endpoints:**

```python
# Standard success response
{
    "success": true,
    "data": { ... },
    "meta": {
        "timestamp": "2025-11-23T12:00:00Z",
        "request_id": "uuid"
    }
}

# Standard error response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable message",
        "details": { ... }
    },
    "meta": {
        "timestamp": "2025-11-23T12:00:00Z",
        "request_id": "uuid"
    }
}
```

**Benefits:**
- Predictable responses for client
- Easy to generate TypeScript types
- Simple error handling on frontend

#### 3. Comprehensive API Documentation

**Generate OpenAPI 3.1 spec:**

```python
from fastapi import FastAPI

app = FastAPI(
    title="MagnetarStudio API",
    description="Comprehensive API for offline-first AI platform",
    version="2.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication & authorization"},
        {"name": "chat", "description": "AI chat sessions"},
        {"name": "vault", "description": "File management"},
        # ... all endpoints categorized
    ]
)
```

**Auto-generate:**
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- TypeScript types for React frontend
- Swift models for native app (via openapi-generator)

#### 4. Database Migration System

**Proper Alembic setup:**

```
apps/backend/migrations/
  - versions/
    - 001_initial_schema.py
    - 002_add_vault_encryption.py
    - 003_add_workflows_table.py
    - ...
  - README.md (migration guide)
  - rollback.py (automated rollback script)
```

**Benefits:**
- Version-controlled schema
- Easy rollback
- Documented changes
- CI/CD integration

#### 5. Testing Infrastructure

**Current:** Limited tests
**Proposed:** Comprehensive test suite

```
apps/backend/tests/
  - unit/
    - services/
      - test_team_service.py
      - test_vault_service.py
      - test_chat_service.py
  - integration/
    - test_auth_flow.py
    - test_file_upload.py
    - test_p2p_sync.py
  - e2e/
    - test_complete_workflows.py
  - fixtures/
    - sample_data.py
    - mock_models.py
```

**Target:** 80%+ code coverage

#### 6. Configuration Management

**Environment-based config:**

```python
# config/base.py
class BaseConfig:
    API_VERSION = "v1"
    JWT_ALGORITHM = "HS256"

# config/development.py
class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DATABASE_URL = "sqlite:///./dev.db"

# config/production.py
class ProductionConfig(BaseConfig):
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL")
```

**Benefits:**
- Easy environment switching
- No hardcoded values
- Validated by Pydantic

#### 7. Dependency Injection

**Use FastAPI's DI system consistently:**

```python
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # JWT validation
    return user

# Usage in routes
@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

**Benefits:**
- Testable (mock dependencies)
- Clean separation
- Consistent patterns

---

## Success Metrics

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **App Launch** | < 1 second | Time to interactive |
| **Memory Usage (Idle)** | < 100MB | Instruments (Allocations) |
| **Memory Usage (Active)** | < 300MB | With 10 open files, active chat |
| **Battery Impact** | < 5% / hour | Energy Log (typical usage) |
| **API Response Time** | < 100ms (p95) | Prometheus metrics |
| **UI Frame Rate** | 60fps (consistent) | Metal frame time |
| **WebSocket Latency** | < 50ms | Ping/pong roundtrip |
| **File Upload (10MB)** | < 2 seconds | Local network |
| **Query Execution (1M rows)** | < 5 seconds | DuckDB performance |
| **Model Inference (MLX)** | < 1 second | 512 token generation |

### User Experience Goals

- **Gorgeous UI** - Liquid Glass design sets new standard
- **Blazing Fast** - Native performance, no web overhead
- **Offline-First** - Works anywhere, syncs when able
- **Secure** - Hardware-level encryption, biometric auth
- **Intuitive** - Apple HIG compliant, natural interactions
- **Accessible** - VoiceOver, Dynamic Type, keyboard nav

### Business Goals

- **Flagship Product** - Showcase SwiftUI mastery
- **Easy Expansion** - Clean backend for React port (MagnetarPro)
- **Engineering Team Ready** - Well-documented, modular codebase
- **App Store Quality** - Ready for distribution day one
- **Platform Exclusive** - Full leverage of Apple ecosystem

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Yjs CRDT complexity** | High | Evaluate existing Swift CRDT libraries, consider server-side merge |
| **Metal 4 learning curve** | Medium | Start with SwiftUI components, add Metal later |
| **MLX model compatibility** | Medium | Test with quantized models early, fallback to Ollama |
| **P2P mesh reliability** | High | Extensive testing, fallback to server relay |
| **Large file performance** | Medium | Streaming encryption, chunked uploads |

### Migration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Scope creep** | High | Strict phase boundaries, no new features during migration |
| **Timeline overrun** | Medium | Buffer in each phase, prioritize core features |
| **Backend changes needed** | Medium | Comprehensive API testing, version API endpoints |
| **Data migration issues** | High | Extensive testing, rollback plan |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Platform lock-in** | Medium | Keep backend cross-platform ready |
| **App Store rejection** | High | Follow guidelines strictly, TestFlight beta |
| **Feature parity delays** | Medium | Launch with core features, iterate |

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Foundation** | 2-3 weeks | Auth + app shell |
| **Phase 2: Core Features** | 3-4 weeks | Chat, Database, Files |
| **Phase 3: Advanced** | 3-4 weeks | Team, Agent, Workflows |
| **Phase 4: ML & Polish** | 2-3 weeks | MLX, Metal 4, UI perfection |
| **Phase 5: Testing** | 2 weeks | Production-ready |
| **Total** | **12-16 weeks** | ✅ App Store submission |

---

## Next Steps

1. **Review & Approve Plan** - Ensure alignment on architecture decisions
2. **Create Swift Project** - Set up Xcode workspace
3. **Backend Refactoring** - Start modularizing services
4. **Phase 1 Kickoff** - Begin implementation

---

## Conclusion

This migration transforms MagnetarStudio from a web app into a **native macOS 26 & iPadOS 26 flagship** that fully leverages:

✨ **Apple FM** - On-device AI orchestration
✨ **MLX** - M5 Neural Accelerator inference
✨ **Metal 4** - GPU compute & gorgeous visuals
✨ **Liquid Glass** - Stunning new design language
✨ **Secure Enclave** - Hardware-level security
✨ **Network Framework** - Native P2P mesh

The **"do it right, do it once"** philosophy ensures:
- Clean, modular backend for easy React port (MagnetarPro)
- Showcase SwiftUI mastery (flagship quality)
- Engineering team-ready codebase
- Long-term business strategy alignment

**MagnetarStudio will be the jewel of the ball.** 💎
