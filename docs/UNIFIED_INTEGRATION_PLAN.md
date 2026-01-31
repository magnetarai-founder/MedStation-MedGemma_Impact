# MagnetarStudio Unified Integration Plan

> **Goal:** Bring MagnetarAI-iPad's seamless UX and context preservation system INTO MagnetarStudio while preserving all its powerful enterprise features.

---

## Working Instructions

### Approach
- **Sequential phases**: Complete each phase fully before moving to the next
- **Batch review**: Write multiple related files, then review the batch together
- **Concise updates**: Brief status (what was done, what's next)
- **Detailed task tracking**: Track each file/component with status

### Per-Phase Workflow
```
1. Create tasks for all files in the phase
2. Read source files from iPad/MagnetarCode for reference
3. Write batch of related files
4. Present batch for review
5. Address feedback
6. Mark tasks complete
7. Run verification tests (if applicable)
8. Move to next phase
```

### File Creation Order (within each phase)
1. Models/Data structures first
2. Core services second
3. Integration/wiring last

### Checkpoints
- After each phase: Verify builds without errors
- After Phase 2 (RAG): Test semantic search works
- After Phase 4 (Optimizer): Test context stays within limits
- After Phase 6 (Wire Up): Full integration test

---

## Executive Summary

This plan integrates:
- **MagnetarStudio's Power**: HuggingFace GGUF, Ollama Metal 4, P2P mesh, Vault E2E encryption, Workflow automation, Team RBAC
- **MagnetarAI-iPad's Seamless UX**: Hierarchical conversation storage, ANE user learning, context preservation with history bridges
- **MagnetarCode's Intelligence**: FAISS semantic search, orchestration patterns, smart caching

**Timeline:** 17 weeks across 8 phases
**Scope:** ~40 new files, ~15 modified files, ~5,000-7,000 LOC

---

## Architecture Philosophy

### Current State
- MagnetarStudio has raw power but basic context management
- iPad app has seamless context but limited model options
- MagnetarCode has intelligence layer but standalone

### Target State
- Unified platform with all three strengths
- 280K+ virtual context via hierarchical storage + semantic retrieval + ANE learning
- Works with Ollama, HuggingFace GGUF, Apple FM, and Claude API

---

## What Gets Preserved (Non-Negotiable)

| Feature | Location | Status |
|---------|----------|--------|
| HuggingFace GGUF | `MagnetarHub/` views | In progress (keep) |
| Ollama + Metal 4 | `OllamaService.swift`, backend | Complete (keep) |
| P2P Mesh (libp2p) | `p2p_mesh_service.py` | Complete (keep) |
| Vault E2E Encryption | `VaultStore.swift`, `vault_auth.py` | Complete (keep) |
| Workflow Automation | `WorkflowStore.swift`, backend | Complete (keep) |
| Team RBAC | `TeamStore.swift`, backend | Complete (keep) |
| Code Workspace | `CodeWorkspace.swift` | Complete (keep) |
| 40+ API Routes | `router_registry.py` | Complete (keep) |

---

## Phase 0: Foundation - Hierarchical Conversation Storage

**Duration:** Week 1-2
**Source:** MagnetarAI-iPad + Claude Code pattern
**Priority:** CRITICAL

### Directory Structure to Implement

```
.magnetar_studio/
├── conversations/
│   └── conv_{uuid}/
│       ├── metadata.json              # Session info, intent classification
│       ├── hierarchy/
│       │   ├── session_graph.json     # Entity relationships
│       │   ├── themes/
│       │   │   ├── theme_001.json     # Semantic nodes + embeddings
│       │   │   └── ...
│       │   └── compressed_context.json
│       ├── files/
│       │   ├── uploaded_doc.pdf
│       │   ├── uploaded_doc_processed.json  # Data engine output
│       │   └── embeddings/
│       │       └── uploaded_doc.vectors
│       └── reference_index.json       # REF ID quick lookup
├── user_model/
│   ├── behavior_patterns.json         # ANE-learned patterns
│   ├── topic_preferences.json
│   └── forgetting_thresholds.json
└── global_files/
    └── file_index.json                # Cross-conversation registry
```

### Files to Create

| File | Purpose | Port From |
|------|---------|-----------|
| `Shared/Services/ConversationStorage/ConversationStorageService.swift` | Manages hierarchy folders | iPad |
| `Shared/Services/ConversationStorage/ConversationModels.swift` | Data models | iPad |
| `Shared/Services/ConversationStorage/ThemeExtractor.swift` | Extracts themes | iPad |
| `Shared/Services/ConversationStorage/SessionGraphBuilder.swift` | Entity relationships | iPad |
| `Shared/Services/ConversationStorage/ReferenceIndex.swift` | REF token system | iPad |
| `Shared/Services/ConversationStorage/SemanticNode.swift` | Compressed context nodes | New |

### Key Data Models

```swift
struct ConversationHierarchy: Codable {
    let id: UUID
    var metadata: ConversationMetadata
    var themes: [ConversationTheme]
    var sessionGraph: SessionGraph
    var compressedContext: CompressedContext
    var fileReferences: [FileReference]
    var referenceIndex: [String: ReferencePointer]
}

struct ConversationTheme: Codable {
    let id: UUID
    var topic: String
    var entities: [String]
    var keyPoints: [String]
    var embedding: [Float]  // 384-dim
    var messageIds: [UUID]
    var relevanceScore: Float
    var lastAccessed: Date
}

struct SemanticNode: Codable {
    let id: UUID
    let concept: String
    let content: String
    let embedding: [Float]
    let entities: [String]
    let decisions: [String]?
    let todos: [String]?
    let fileRefs: [UUID]?
    let originalMessageCount: Int
    let relevanceScore: Float
}
```

---

## Phase 0.5: Apple Neural Engine Integration

**Duration:** Week 3
**Source:** MagnetarAI-iPad + MagnetarStudio persistence memory
**Priority:** CRITICAL

### What ANE Learns

1. **Usage Patterns**
   - Time of day patterns
   - Topic preferences
   - File type affinities
   - Query styles
   - Workspace switching patterns

2. **Context Predictions**
   - Likely topics based on history
   - Likely file needs
   - Compression aggressiveness per topic

3. **Cross-App Intelligence**
   - Data tab → AI Chat handoffs
   - Vault file usage patterns
   - Workflow → Chat correlation

### Files to Create

| File | Purpose | Port From |
|------|---------|-----------|
| `Shared/Services/ANE/UserBehaviorTracker.swift` | Collects patterns | iPad |
| `Shared/Services/ANE/ANEPredictor.swift` | CoreML predictions | iPad |
| `Shared/Services/ANE/ContextPreloader.swift` | Pre-loads context | iPad |
| `Shared/Services/ANE/SmartForgetting.swift` | Learned compression | iPad |
| `Resources/UserBehavior.mlmodel` | On-device ML model | New |

### Extended Behavior Events (MagnetarStudio-specific)

```swift
enum BehaviorEventType: String, Codable {
    // From iPad
    case messageSent, fileUploaded, fileAccessed, tabSwitched
    case sessionCreated, sessionCompacted, themeAccessed, searchPerformed

    // NEW for MagnetarStudio
    case workflowExecuted
    case kanbanTaskCreated
    case vaultFileAccessed
    case teamMessageSent
    case codeFileEdited
    case p2pPeerConnected
    case modelSwitched        // Ollama ↔ HuggingFace ↔ Claude
    case huggingFaceModelDownloaded
}
```

---

## Phase 1: Context Preservation System

**Duration:** Week 4-5
**Source:** MagnetarAI-iPad CompactService
**Priority:** HIGH

### Port CompactService with History Bridges

**Source:** `iPad/Features/Chat/CompactService.swift`
**Target:** `Shared/Services/Context/CompactService.swift`

**Key Adaptation:** Use Ollama for summarization (MagnetarStudio already has OllamaService)

```swift
class CompactService {
    private let ollamaService: OllamaService
    private let themeExtractor: ThemeExtractor

    func compact(session: ChatSession) async -> CompactionResult {
        // 1. Extract themes from old messages
        let themes = await themeExtractor.extract(from: session.messages)

        // 2. Create summary via Ollama
        let summary = await ollamaService.summarize(
            messages: session.messages,
            maxTokens: 500
        )

        // 3. Build history bridge
        let bridge = HistoryBridge(
            summary: summary,
            themes: themes,
            recentMessages: Array(session.messages.suffix(15))
        )

        // 4. Store compressed context
        await storageService.saveCompressedContext(bridge, for: session.id)

        // 5. Leave REF tokens in place
        return CompactionResult(
            bridge: bridge,
            refTokens: themes.map { "[REF:\($0.id)]" }
        )
    }
}
```

### Multi-Tier Memory Architecture

```swift
enum ContextTier {
    case immediate    // Last 10-15 messages, full fidelity
    case themes       // 3-5 key topics as structured JSON
    case graph        // Entity relationships for reference
    case compressed   // Older messages, heavily compressed
    case archived     // In storage, retrievable via semantic search
}
```

### REF Token System

```swift
// When compressing out of immediate context:
"[REF:topic_abc123]"  // Marker left in place

// When topic comes up again:
if query.mentionsEntity(matchingRef) {
    let fullContext = await storageService.expand(ref: "topic_abc123")
    // Inject into context on-demand
}
```

---

## Phase 2: Local RAG with Hash-Based Embeddings

**Duration:** Week 6-7
**Source:** MagnetarAI-iPad + Neutron Star
**Priority:** HIGH

### Files to Create

| File | Purpose | Port From |
|------|---------|-----------|
| `Shared/Services/RAG/HashEmbedder.swift` | MD5 → 384-dim vectors | iPad/Neutron |
| `Shared/Services/RAG/VectorStore.swift` | SQLite-backed storage | iPad |
| `Shared/Services/RAG/SemanticSearchService.swift` | Cosine similarity | iPad |
| `Shared/Services/RAG/RAGContextBuilder.swift` | Context assembly | iPad |
| `Shared/Services/RAG/RAGModels.swift` | Data models | iPad |

### Hash-Based Embedding (from Neutron Star)

```swift
class HashEmbedder {
    func embed(_ text: String) -> [Float] {
        let data = text.data(using: .utf8)!
        var hash = [UInt8](repeating: 0, count: 16)
        _ = data.withUnsafeBytes { CC_MD5($0.baseAddress, CC_LONG(data.count), &hash) }

        // Expand to 384 dimensions
        var vector = [Float](repeating: 0, count: 384)
        for i in 0..<384 {
            let byteIdx = i % 16
            vector[i] = (Float(hash[byteIdx]) - 128) / 128.0
        }
        return l2Normalize(vector)
    }
}
```

### What Gets Embedded

- Chat messages (conversation retrieval)
- File content summaries (from FilePreprocessor)
- Document snippets (from Docs workspace)
- Spreadsheet metadata (from Sheets)
- Vault file descriptions
- Workflow definitions
- Kanban task descriptions

---

## Phase 3: FAISS Backend Integration (from MagnetarCode)

**Duration:** Week 8
**Source:** MagnetarCode
**Priority:** HIGH

### Port FAISS Search Service

**Source:** `MagnetarCode/apps/backend/api/services/faiss_search.py`
**Target:** `MagnetarStudio/apps/backend/api/services/faiss_search.py`

### Strategy

- **On-device (HashEmbedder):** Privacy-sensitive quick lookups
- **Backend (FAISS):** Cross-workspace semantic search with sentence-transformers

### New Backend Endpoints

```python
# Add to api/context_router.py

@router.post("/v1/context/faiss/search")
async def faiss_semantic_search(
    request: FAISSSearchRequest,
    current_user: User = Depends(get_current_user)
) -> FAISSSearchResponse:
    """FAISS-accelerated vector similarity search"""
    faiss_service = get_faiss_search(get_db_path())
    results = await faiss_service.search(
        query=request.query,
        top_k=request.limit,
        user_id=str(current_user.id)
    )
    return FAISSSearchResponse(results=results)

@router.post("/v1/context/faiss/index")
async def index_content(
    request: IndexRequest,
    current_user: User = Depends(get_current_user)
):
    """Index content for semantic search"""
    faiss_service = get_faiss_search(get_db_path())
    await faiss_service.index(
        content=request.content,
        metadata=request.metadata,
        user_id=str(current_user.id)
    )
```

---

## Phase 4: Smart Context Optimizer

**Duration:** Week 9
**Source:** MagnetarAI-iPad + MagnetarCode
**Priority:** HIGH

### Token Budget Allocation

```swift
struct ContextBudget {
    let total: Int
    let systemPrompt: Int    // 10%
    let history: Int         // 25%
    let ragResults: Int      // 30%
    let fileContext: Int     // 25%
    let reserve: Int         // 10%

    // Presets for different models
    static let appleFM = ContextBudget(total: 4000, ...)
    static let ollamaSmall = ContextBudget(total: 8000, ...)
    static let ollamaLarge = ContextBudget(total: 32000, ...)
    static let huggingFace = ContextBudget(total: 128000, ...)
    static let claude = ContextBudget(total: 200000, ...)
}
```

### Relevance Scoring Algorithm

```swift
func scoreRelevance(node: SemanticNode, query: String) -> Float {
    let recencyScore = recencyWeight(node.lastAccessed)              // 0.3
    let similarityScore = cosineSimilarity(node.embedding, queryEmbed) // 0.4
    let entityScore = entityOverlap(node.entities, queryEntities)    // 0.2
    let userPatternScore = anePredictor.relevance(node)              // 0.1

    return (recencyScore * 0.3) +
           (similarityScore * 0.4) +
           (entityScore * 0.2) +
           (userPatternScore * 0.1)
}
```

---

## Phase 5: Cross-Conversation File System

**Duration:** Week 10
**Source:** MagnetarAI-iPad
**Priority:** HIGH

### Port CrossConversationFileIndex

**Source:** `iPad/Services/Files/CrossConversationFileIndex.swift`
**Target:** `Shared/Services/Files/CrossConversationFileIndex.swift`

### Integration with Vault

```swift
struct IndexedFile {
    let id: UUID
    let originalName: String
    let processedPath: URL
    let embeddingsPath: URL
    let conversationIds: [UUID]  // Where this file was used
    let isVaultProtected: Bool   // Respect VaultPermissionManager
    let accessCount: Int
    let lastAccessed: Date
}
```

### Enhanced File Picker UI

```
┌─────────────────────────────────────┐
│  📎 Add Context                     │
├─────────────────────────────────────┤
│  📤 Upload New File                 │
│  ─────────────────────────────────  │
│  📁 From Files Tab          (12)    │
│  🔐 From Vault              (8)     │  ← NEW: Vault integration
│  📊 From Data Tab           (3)     │
│  🕐 Previously Uploaded     (5)     │
│  🔗 Cross-Conversation      (28)    │
│  ─────────────────────────────────  │
│  ⭐ ANE Suggested                   │  ← NEW: Predicted files
│     📄 Q4_Report.pdf (relevant)     │
│     📊 Budget.xlsx (likely needed)  │
└─────────────────────────────────────┘
```

---

## Phase 6: Wire Up Incomplete Features

**Duration:** Week 11-12
**Priority:** HIGH

### 6.1 Enable P2P Chat Router

**File:** `apps/backend/api/router_registry.py` (lines 103-110)

```python
# Uncomment and wire up:
try:
    from api.p2p_chat import router as p2p_chat_router
    app.include_router(p2p_chat_router)
    services_loaded.append("P2P Chat")
except Exception as e:
    services_failed.append("P2P Chat")
    logger.error("Failed to load P2P chat router", exc_info=True)
```

### 6.2 Complete ANE Core ML Routing

**File:** `apps/backend/api/ml/ane/router.py`

- Add training data collection from routing decisions
- Implement Core ML model training pipeline
- Add model hot-swap for updated models

### 6.3 Complete Kanban Backend Sync

**File:** `apps/native/macOS/Workspaces/KanbanWorkspace.swift` (lines 265, 293)

```swift
private func updateTaskStatus(_ task: KanbanTask, to newStatus: TaskStatus) {
    // Local update
    withAnimation { task.status = newStatus }

    // Sync with backend
    Task {
        await crudOperations.updateTask(
            task.taskId,
            updates: TaskUpdateRequest(status: newStatus.rawValue)
        )
    }
}
```

### 6.4 Enable Document/Spreadsheet Creation

**File:** `apps/native/Shared/Components/Header/HeaderComponents.swift` (lines 489-503)

```swift
Button {
    Task {
        let doc = await DocsService.shared.createDocument(
            title: "Untitled Document",
            type: .richText
        )
        openWindow(id: "workspace-docs", value: doc.id)
    }
} label: {
    Label("New Document", systemImage: "doc.richtext")
}
// Remove .disabled(true)
```

---

## Phase 7: Refactor Monolithic Files

**Duration:** Week 13-14
**Priority:** MEDIUM

### 7.1 Break Up AppContext.swift (1,037 lines)

**Current:** `Shared/Models/AppContext.swift`

**Target Structure:**
```
Shared/Models/AppContext/
├── AppContext.swift              (Core, ~150 lines)
├── MainActorSnapshot.swift
├── WorkspaceContexts/
│   ├── VaultContext.swift
│   ├── DataContext.swift
│   ├── KanbanContext.swift
│   ├── WorkflowContext.swift
│   ├── TeamContext.swift
│   └── CodeContext.swift
├── ANEContextState.swift
├── ModelInteractionHistory.swift
├── UserPreferences.swift
└── SystemResourceState.swift
```

### 7.2 Break Up ChatStore.swift (942 lines)

**Current:** `Shared/Stores/ChatStore.swift`

**Target Structure:**
```
Shared/Stores/Chat/
├── ChatStore.swift               (Core, ~300 lines)
├── ChatStore+Sessions.swift
├── ChatStore+Messaging.swift
├── ChatStore+ModelRouting.swift
├── ChatStore+Persistence.swift
└── ChatModels.swift
```

### 7.3 Break Up ContextBundle.swift (892 lines)

**Current:** `Shared/Models/ContextBundle.swift`

**Target Structure:**
```
Shared/Models/ContextBundle/
├── ContextBundle.swift           (Core, ~100 lines)
├── BundledContexts/
│   ├── BundledVaultContext.swift
│   ├── BundledDataContext.swift
│   ├── BundledKanbanContext.swift
│   ├── BundledWorkflowContext.swift
│   ├── BundledTeamContext.swift
│   └── BundledCodeContext.swift
├── RAGDocuments.swift
├── AvailableModels.swift
├── ContextBundler.swift
└── QueryRelevance.swift
```

---

## Phase 8: Testing and Polish

**Duration:** Week 15-17
**Priority:** HIGH

### Integration Tests

```
apps/native/Tests/Integration/
├── ContextPreservationTests.swift
├── RAGIntegrationTests.swift
├── CrossConversationFileTests.swift
├── ANEBehaviorTests.swift
├── CompactionFlowTests.swift
├── P2PChatTests.swift
└── VaultContextTests.swift
```

### Performance Benchmarks

| Operation | Target |
|-----------|--------|
| Context bundling | <100ms |
| RAG search (local) | <50ms |
| RAG search (FAISS backend) | <200ms |
| Compaction | <500ms |
| ANE prediction | <20ms |
| File picker relevance scoring | <100ms |

### Verification Checklist

- [ ] Context preserved across compaction
- [ ] RAG retrieves relevant context from 50+ messages ago
- [ ] ANE predictions improve after 10+ sessions
- [ ] File uploads persist and are searchable
- [ ] REF tokens expand on-demand correctly
- [ ] P2P chat syncs conversations
- [ ] Vault files respect permissions in AI context
- [ ] HuggingFace models work with new context system

---

## Dependency Graph

```
Phase 0 (Hierarchical Storage) ─────┐
                                    │
Phase 0.5 (ANE Learning) ───────────┼───┐
                                    │   │
Phase 1 (Context Preservation) ─────┤   │
                                    │   │
Phase 2 (Local RAG) ────────────────┼───┼───> Phase 5 (File System)
                                    │   │           │
Phase 3 (FAISS Backend) ────────────┘   │           │
                                        │           │
Phase 4 (Context Optimizer) ────────────┘           │
                                                    │
Phase 6 (Wire Up Features) <────────────────────────┘
        │
        └──> Phase 7 (Refactor Monoliths)
                    │
                    └──> Phase 8 (Testing)
```

---

## How 280K+ Context Actually Works

### The Flow (When User Sends Message)

1. **ANE predicts** likely context needs (based on learned patterns)
2. **Semantic search** queries conversation hierarchy:
   - `themes/` for relevant topics
   - `files/` for relevant documents
   - `session_graph` for entity relationships
3. **Pull top-K** most relevant nodes (~1-2K tokens for small models, more for large)
4. **Combine** with last 10-15 messages (immediate context)
5. **Expand** any REF tokens that match current query
6. **Send** to model (within its actual context limit)
7. **Get response**
8. **Store** new exchange:
   - Add to immediate tier
   - Update session_graph with new entities
   - Compute embedding for new message
   - ANE updates user behavior model
9. **If threshold exceeded:**
   - Extract themes from older messages
   - Create semantic nodes
   - Compress to `themes/` folder
   - Leave REF tokens in place

### Why It Feels Like 280K

- Model only uses its actual limit (4K-200K depending on model)
- But user can reference anything from full history
- Semantic search finds relevant context instantly
- File uploads persist forever with full processing
- ANE learns what matters and pre-loads it
- Smart forgetting keeps only what's relevant

### Token Budget Reality

```swift
// Per-message actual usage (Apple FM example):
struct TokenAllocation {
    let systemPrompt = 400        // 10%
    let immediateContext = 1000   // 25% (last 10-15 msgs)
    let ragRetrieved = 1200       // 30% (semantic search results)
    let fileContext = 1000        // 25% (relevant file snippets)
    let reserve = 400             // 10% (for response)
    // Total: ~4000 tokens sent to Apple FM
}

// User perceived context:
// All 280K+ tokens searchable and retrievable on-demand
```

---

## Files Summary

### New Files to Create (~40)

**Phase 0: Conversation Storage (9 files)** ← EXPANDED for gaps
- `ConversationStorageService.swift`
- `ConversationModels.swift`
- `ThemeExtractor.swift`
- `SessionGraphBuilder.swift` ← ENHANCED (Gap 1: Full entity relationships)
- `ReferenceIndex.swift`
- `SemanticNode.swift` ← ENHANCED (Gap 2: decisions/todos/fileRefs/codeRefs)
- `SessionBranch.swift` ← NEW (Gap 3: Topic branching)
- `SessionBranchManager.swift` ← NEW (Gap 3)
- `VirtualContextDisplay.swift` ← NEW (Gap 5: 280K display)

**Phase 0.5: ANE (10 files)** ← EXPANDED for gaps
- `UserBehaviorTracker.swift`
- `ANEPredictor.swift`
- `ContextPreloader.swift`
- `SmartForgetting.swift`
- `UserBehavior.mlmodel`
- `ANETrainingManager.swift` ← NEW (Gap 4: Real CreateML training)
- `BehaviorTrainingExample.swift` ← NEW (Gap 4)
- `CrossWorkspaceIntelligence.swift` ← NEW (Gap 6: Cross-app learning)
- `TransitionContext.swift` ← NEW (Gap 6)
- `LearnablePattern.swift` ← NEW (Gap 6)

**Phase 1: Context Preservation (3 files)**
- `CompactService.swift`
- `HistoryBridge.swift`
- `ContextTier.swift`

**Phase 2: RAG (5 files)**
- `HashEmbedder.swift`
- `VectorStore.swift`
- `SemanticSearchService.swift`
- `RAGContextBuilder.swift`
- `RAGModels.swift`

**Phase 3: FAISS Backend (2 files)**
- `faiss_search.py`
- `faiss_models.py`

**Phase 4: Context Optimizer (3 files)**
- `ContextOptimizer.swift`
- `ContextItem.swift`
- `TokenCounter.swift`

**Phase 5: File System (3 files)**
- `CrossConversationFileIndex.swift`
- `FileRelevanceScorer.swift`
- `SmartFilePicker.swift`

**Phase 7: Refactored Files (~15 new from splits)**

### Files to Modify (~15)

- `ChatStore.swift` - Integrate full pipeline
- `ContextBundle.swift` - Add RAG documents
- `AppContext.swift` - ANE state integration
- `router_registry.py` - Enable P2P chat
- `ane/router.py` - Complete implementation
- `KanbanWorkspace.swift` - Backend sync
- `HeaderComponents.swift` - Enable document creation, file picker
- `AcceleratedAIService.swift` - ANE hooks
- `FilePreprocessor.swift` - Store embeddings
- `VaultStore.swift` - CrossConversation integration
- `OllamaService.swift` - Compaction support
- `context_router.py` - FAISS endpoints

---

## CRITICAL GAPS TO ADDRESS (from iPad Diagnostics)

These items were identified as potential gaps in the iPad implementation. MagnetarStudio MUST implement these fully.

### Gap 1: SessionGraphBuilder - Full Entity Relationship Tracking

**Status in iPad:** Entity extraction exists in ThemeExtractor, but dedicated relationship graph may not be fully wired.

**MagnetarStudio Requirement:** Implement complete SessionGraphBuilder that tracks:

```swift
struct SessionGraph: Codable {
    var nodes: [EntityNode]
    var edges: [EntityRelationship]

    struct EntityNode: Codable {
        let id: UUID
        let name: String
        let type: EntityType  // person, place, concept, file, task, etc.
        let firstMentioned: Date
        let lastMentioned: Date
        let mentionCount: Int
        let embedding: [Float]
    }

    struct EntityRelationship: Codable {
        let sourceId: UUID
        let targetId: UUID
        let relationshipType: String  // "mentioned_with", "caused_by", "depends_on"
        let strength: Float           // Co-occurrence frequency
        let context: String           // Brief description of relationship
    }

    // Query methods
    func relatedEntities(to entityId: UUID, limit: Int) -> [EntityNode]
    func pathBetween(source: UUID, target: UUID) -> [EntityRelationship]?
    func strongestRelationships(limit: Int) -> [EntityRelationship]
}
```

**File:** `Shared/Services/ConversationStorage/SessionGraphBuilder.swift`

### Gap 2: SemanticNode - Full Structure with Decisions/TODOs/FileRefs

**Status in iPad:** CompressedContext exists but may not have full structure.

**MagnetarStudio Requirement:** Ensure SemanticNode has ALL fields:

```swift
struct SemanticNode: Codable {
    let id: UUID
    let concept: String              // What this represents
    let content: String              // Compressed content
    let embedding: [Float]           // 384-dim for retrieval
    let entities: [String]           // Referenced entities

    // CRITICAL - These must be implemented:
    let decisions: [Decision]?       // Any decisions made in this context
    let todos: [TodoItem]?           // Outstanding items extracted
    let fileRefs: [UUID]?            // Related files
    let codeRefs: [CodeReference]?   // Code snippets discussed (NEW for MagnetarStudio)
    let workflowRefs: [UUID]?        // Related workflows (NEW for MagnetarStudio)

    let originalMessageCount: Int
    let relevanceScore: Float
    let createdAt: Date
    let lastAccessed: Date

    struct Decision: Codable {
        let summary: String
        let madeAt: Date
        let confidence: Float
    }

    struct TodoItem: Codable {
        let description: String
        let priority: Priority
        let extractedAt: Date
        let completed: Bool
    }

    struct CodeReference: Codable {
        let filePath: String
        let language: String
        let snippet: String
        let lineRange: ClosedRange<Int>?
    }
}
```

**File:** `Shared/Services/ConversationStorage/SemanticNode.swift`

### Gap 3: Session Branching (Topic-Based Context Isolation)

**Status in iPad:** ❌ Not implemented

**MagnetarStudio Requirement:** Implement session branching for topic isolation:

```swift
struct SessionBranch: Codable {
    let id: UUID
    let parentSessionId: UUID
    let branchName: String
    let branchTopic: String
    let createdAt: Date
    let contextSnapshot: ContextSnapshot  // Full context at branch point
    var messages: [ChatMessage]
    var isActive: Bool
}

class SessionBranchManager {
    /// Detect significant topic shift
    func detectTopicShift(
        currentMessages: [ChatMessage],
        newMessage: ChatMessage
    ) -> TopicShiftResult

    /// Offer to branch when shift detected
    func suggestBranch(for shift: TopicShiftResult) -> BranchSuggestion?

    /// Create a new branch, saving current context
    func createBranch(
        from session: ChatSession,
        name: String,
        topic: String
    ) async -> SessionBranch

    /// Switch between branches
    func switchToBranch(_ branchId: UUID) async

    /// Merge branch back into main
    func mergeBranch(_ branchId: UUID, into sessionId: UUID) async

    /// List all branches for a session
    func branches(for sessionId: UUID) -> [SessionBranch]
}

enum TopicShiftResult {
    case noShift
    case minorShift(confidence: Float)
    case majorShift(newTopic: String, confidence: Float)
}
```

**Files to Create:**
- `Shared/Services/ConversationStorage/SessionBranch.swift`
- `Shared/Services/ConversationStorage/SessionBranchManager.swift`

**UI Integration:**
- Add branch indicator in ChatWorkspace sidebar
- Show "Branch this conversation?" prompt on major topic shift
- Tab-like branch switcher within a session

### Gap 4: CreateML On-Device Training (Real MLUpdateTask, Not Heuristics)

**Status in iPad:** ANEPredictor may use heuristics, not actual MLUpdateTask training.

**MagnetarStudio Requirement:** Implement REAL on-device training:

```swift
import CreateML
import CoreML

class ANETrainingManager {
    private var trainingData: [BehaviorTrainingExample] = []
    private let minExamplesForTraining = 50

    struct BehaviorTrainingExample: Codable {
        let features: UserBehaviorFeatures
        let label: ContextPrediction
        let timestamp: Date
    }

    /// Collect training example after each interaction
    func recordExample(
        features: UserBehaviorFeatures,
        actualOutcome: ContextPrediction
    ) {
        trainingData.append(BehaviorTrainingExample(
            features: features,
            label: actualOutcome,
            timestamp: Date()
        ))

        if trainingData.count >= minExamplesForTraining {
            Task { await trainModelIfNeeded() }
        }
    }

    /// Train/update model on-device using CreateML
    func trainModelIfNeeded() async {
        guard trainingData.count >= minExamplesForTraining else { return }

        do {
            // Convert to MLDataTable
            let dataTable = try createDataTable(from: trainingData)

            // Train classifier
            let classifier = try MLBoostedTreeClassifier(
                trainingData: dataTable,
                targetColumn: "prediction"
            )

            // Save updated model
            let modelURL = getModelURL()
            try classifier.write(to: modelURL)

            // Hot-swap the model in ANEPredictor
            await ANEPredictor.shared.reloadModel(from: modelURL)

            // Clear old training data, keep recent
            trainingData = Array(trainingData.suffix(20))

        } catch {
            logger.error("On-device training failed: \(error)")
        }
    }

    /// Use MLUpdateTask for incremental updates (iOS 14+)
    func incrementalUpdate(with newExamples: [BehaviorTrainingExample]) async {
        guard let modelURL = Bundle.main.url(forResource: "UserBehavior", withExtension: "mlmodelc") else { return }

        let updateTask = try? MLUpdateTask(
            forModelAt: modelURL,
            trainingData: createBatchProvider(from: newExamples),
            configuration: nil,
            completionHandler: { context in
                // Save updated model
                context.model.write(to: self.getModelURL())
            }
        )
        updateTask?.resume()
    }
}
```

**Files to Create:**
- `Shared/Services/ANE/ANETrainingManager.swift`
- `Shared/Services/ANE/BehaviorTrainingExample.swift`

**Integration:** ANEPredictor should use ANETrainingManager for continuous improvement.

### Gap 5: 280K Virtual Limit Display

**Status in iPad:** Shows 100K for Apple FM - should show 280K

**MagnetarStudio Requirement:** Virtual limit should reflect the FULL retrievable context:

```swift
struct VirtualContextDisplay {
    /// What the model actually uses
    let actualModelLimit: Int

    /// What the user can reference (all stored context)
    let virtualLimit: Int

    /// Current usage in the virtual space
    let currentUsage: Int

    static func forModel(_ model: AIModel, storageService: ConversationStorageService) -> VirtualContextDisplay {
        let actualLimit = model.contextWindow

        // Virtual limit = all stored themes + files + graph
        let storedTokens = storageService.estimateTotalStoredTokens()
        let virtualLimit = max(280_000, storedTokens)  // Minimum 280K

        return VirtualContextDisplay(
            actualModelLimit: actualLimit,
            virtualLimit: virtualLimit,
            currentUsage: storageService.currentSessionTokens()
        )
    }
}

// UI displays:
// "Context: 45,231 / 280,000 tokens" (virtual)
// NOT: "Context: 2,341 / 4,000 tokens" (actual)
```

**File:** Modify `ChatStore.swift` token display logic

### Gap 6: Cross-App ANE Learning (Full Workspace Intelligence)

**Status in iPad:** Data tab → AI Chat pattern learning may not be fully connected.

**MagnetarStudio Requirement:** Wire up ALL workspace transitions:

```swift
class CrossWorkspaceIntelligence {
    private let behaviorTracker: UserBehaviorTracker
    private let contextPreloader: ContextPreloader

    /// Track workspace transitions and learn patterns
    func trackWorkspaceTransition(
        from source: WorkspaceType,
        to destination: WorkspaceType,
        context: TransitionContext
    ) {
        // Record the transition
        behaviorTracker.record(.workspaceTransition(
            from: source,
            to: destination,
            withFile: context.activeFile,
            withQuery: context.lastQuery
        ))

        // Learn patterns
        updateTransitionModel(source, destination, context)

        // Pre-load likely needed context
        if let prediction = predictNeededContext(for: destination, given: context) {
            Task { await contextPreloader.preload(prediction) }
        }
    }

    /// Predict what context will be needed based on learned patterns
    func predictNeededContext(
        for workspace: WorkspaceType,
        given context: TransitionContext
    ) -> ContextPrediction? {
        switch workspace {
        case .chat:
            // User going to Chat from Data → likely to ask about the dataset
            if context.previousWorkspace == .data,
               let dataset = context.activeDataset {
                return .preloadDatasetContext(dataset)
            }
            // From Code → likely to ask about the code
            if context.previousWorkspace == .code,
               let file = context.activeFile {
                return .preloadCodeContext(file)
            }

        case .data:
            // Coming from Chat → check if recent messages mentioned data
            if let recentQuery = context.lastQuery,
               recentQuery.containsDataIntent {
                return .preloadRelevantDatasets(for: recentQuery)
            }

        case .vault:
            // Pre-load recently discussed files
            return .preloadRecentlyMentionedFiles()

        case .workflow:
            // Pre-load workflows mentioned in chat
            return .preloadDiscussedWorkflows()

        default:
            return nil
        }
    }

    /// MagnetarStudio-specific patterns to learn
    enum LearnablePattern {
        case dataTabThenChat(datasetId: UUID)           // "When I open dataset X, I usually ask about Y"
        case vaultFileThenChat(fileId: UUID)            // "When I access file X, I discuss Y"
        case workflowThenChat(workflowId: UUID)         // "After running workflow X, I ask about results"
        case kanbanThenChat(taskId: UUID)               // "When viewing task X, I discuss blockers"
        case codeFileThenChat(filePath: String)         // "When editing X.swift, I ask about patterns"
        case teamChatThenMainChat(teamId: UUID)         // "After team discussion, I summarize in main chat"
        case p2pSyncThenChat                            // "After P2P sync, I review changes"
        case huggingFaceDownloadThenChat(modelId: String) // "After downloading model X, I test it"
    }
}
```

**Files to Create:**
- `Shared/Services/ANE/CrossWorkspaceIntelligence.swift`
- `Shared/Services/ANE/TransitionContext.swift`
- `Shared/Services/ANE/LearnablePattern.swift`

**Integration Points:**
- Hook into every workspace's `onAppear`
- Hook into NavigationStore workspace changes
- Wire to existing UserBehaviorTracker

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Additive storage; preserve original data |
| Performance regression | Benchmark before/after each phase |
| Breaking changes | Feature flags for gradual rollout |
| Memory pressure | Monitor with Instruments during RAG/FAISS |
| ANE model accuracy | Start with simple heuristics, train over time |
| Session branching complexity | Start with manual branching, add auto-suggest later |
| CreateML training latency | Train in background, use cached model until ready |

---

## Success Metrics

### Core Metrics
- [ ] Context feels "infinite" to users regardless of model
- [ ] Compaction preserves 95%+ of semantic content
- [ ] ANE predictions reach 70%+ accuracy after 20 sessions
- [ ] File search returns relevant results in <100ms
- [ ] All previously incomplete features now functional
- [ ] Monolithic files reduced to <400 lines each
- [ ] Test coverage >80% for new code

### Gap Coverage Metrics (from iPad Diagnostics)
- [ ] **Gap 1:** SessionGraph tracks entity RELATIONSHIPS, not just extractions
- [ ] **Gap 2:** SemanticNode extracts decisions, TODOs, and file refs from context
- [ ] **Gap 3:** Session branching allows topic isolation with branch switching
- [ ] **Gap 4:** ANE uses real CreateML MLUpdateTask, not just heuristics
- [ ] **Gap 5:** UI displays 280K+ virtual limit (not actual model limit)
- [ ] **Gap 6:** Cross-workspace transitions (Data→Chat, Code→Chat, etc.) trigger intelligent preloading

### Verification Checklist

**Context Preservation**
- [ ] Context preserved across compaction
- [ ] RAG retrieves relevant context from 50+ messages ago
- [ ] REF tokens expand on-demand correctly
- [ ] Session branching creates isolated contexts
- [ ] Branch merging works correctly

**ANE Learning**
- [ ] ANE predictions improve after 10+ sessions
- [ ] CreateML model trains on-device after 50+ examples
- [ ] Cross-workspace transitions are tracked and learned
- [ ] Data tab → Chat preloads dataset context
- [ ] Code workspace → Chat preloads code context

**File System**
- [ ] File uploads persist and are searchable
- [ ] Vault files respect permissions in AI context
- [ ] Cross-conversation files accessible
- [ ] File relevance scoring works

**Model Integration**
- [ ] HuggingFace models work with new context system
- [ ] Ollama compaction uses local summarization
- [ ] Apple FM (if available) respects 4K actual limit
- [ ] Claude API uses full 200K when available

**Incomplete Features Wired**
- [ ] P2P chat router enabled and functional
- [ ] Kanban backend sync works
- [ ] Document creation enabled
- [ ] Spreadsheet creation enabled

---

## Updated Scope

**Original Estimate:** ~40 new files, ~15 modified files
**Updated Estimate (with gaps):** ~48 new files, ~18 modified files, ~6,500-8,500 LOC

| Category | Original | With Gaps | Delta |
|----------|----------|-----------|-------|
| Phase 0 files | 6 | 9 | +3 |
| Phase 0.5 files | 5 | 10 | +5 |
| Total new files | ~40 | ~48 | +8 |
| LOC estimate | 5-7K | 6.5-8.5K | +1.5K |

---

*Plan created: January 31, 2026*
*Updated: January 31, 2026 (Gap coverage from iPad diagnostics)*
*Estimated completion: May 2026*
