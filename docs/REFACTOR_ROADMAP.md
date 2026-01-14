# MagnetarStudio Mac - Refactor Roadmap

> **Target:** Post-iPad launch + Kaggle submission (Feb-March 2026)
> **Last Updated:** January 13, 2026

---

## Table of Contents

1. [Vision & Philosophy](#vision--philosophy)
2. [Current State Assessment](#current-state-assessment)
3. [Pre-Requisite Fixes](#pre-requisite-critical-bug-fixes)
4. [Phase 1: Bridge Completion](#phase-1-bridge-completion-weeks-3-4)
5. [Phase 2: Major UI/UX Refactor](#phase-2-major-uiux-refactor-weeks-7-12)
6. [Hugging Face Integration](#hugging-face-integration)
7. [Technical Debt Cleanup](#cleanup-technical-debt)
8. [Timeline Summary](#timeline-summary)
9. [Success Criteria](#success-criteria)

---

## Vision & Philosophy

### iPad Design Philosophy = "Local-First Simplicity"

The iPad app demonstrates the target architecture:

- **45 focused Swift files** vs Mac's **250+ Python files**
- **Zero backend dependency** - all data stays on device
- **Single entry point**: `ContentView.swift` is literally ONE line
- **Build-time purity**: XcodeGen excludes 60+ files to prevent backend creep
- **Graceful degradation**: Features disable cleanly, never crash

### Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Less is more** | Hide complexity by default |
| **Spawnable windows** | Don't cram everything in one view |
| **User choice** | Let users customize their workspace |
| **Clean aesthetics** | iPad polish brought to Mac |
| **Progressive disclosure** | Show features as needed |
| **Offline-first** | Always works, always fast |

### What This Eliminates

- Overwhelming main interface
- Feature discoverability problems
- "Too much at once" cognitive load
- Cluttered navigation and header bars

---

## Current State Assessment

### Code Quality Scorecard

| Area | Score | Grade |
|------|-------|-------|
| Configuration Management | 9/10 | A |
| Testing Infrastructure | 8/10 | B+ |
| Security Practices | 7/10 | B- |
| Module Cohesion | 6/10 | C+ |
| Abstraction Quality | 6/10 | C+ |
| Layering | 5/10 | C |
| Dependency Direction | 4/10 | D+ |
| State Management | 3/10 | D- |
| Database Access | 4/10 | D+ |

**Overall Grade: C+ (65/100)**

### The Gap: Mac Backend vs iPad Philosophy

| Aspect | iPad (Target) | Mac (Current) |
|--------|--------------|---------------|
| Entry Point | 1 line: `ChatWorkspace()` | Complex auth + multi-service init |
| File Count | 45 focused files | 250+ files with god objects |
| State Management | `@Observable` stores | Global dicts (thread-unsafe) |
| Database Access | Local files + UserDefaults | 124 files with direct `sqlite3.connect()` |
| Error Handling | Graceful degradation | 50+ broad `except Exception` |
| Dependencies | 2 external packages | 40+ Python packages |
| Feature Disclosure | Progressive (hidden by default) | Everything visible at once |

---

## Pre-Requisite: Critical Bug Fixes

**These MUST be fixed before the UI/UX refactor to prevent production issues:**

### P0 - Fix Immediately

| Issue | Files | Fix |
|-------|-------|-----|
| Thread-unsafe global state | `core/state.py` | Add `threading.RLock` wrappers |
| Sessions router missing auth | `routes/sessions.py` | Add `Depends(get_current_user)` |
| Silent audit failures | `audit_logger.py` | Add fallback queue |
| Broad exception handlers | 50+ files | Replace with specific exceptions |
| Setup wizard admin bypass | `setup_wizard_routes.py` | Add users-exist check |
| WebSocket token in query params | `auth_middleware.py` | Remove query param fallback |

### P1 - High Priority

| Issue | Impact |
|-------|--------|
| God classes | `data_engine.py` (2000+ lines), `workflow_orchestrator.py` (750 lines) |
| Direct sqlite3.connect() | 124 files bypassing connection pool |
| Deprecated facades | 20+ files creating import confusion |
| Missing type hints | Heavy `Any` usage, reduced type safety |
| Inconsistent error handling | 4+ different patterns across codebase |

---

## Phase 1: Bridge Completion (Weeks 3-4)

*Parallel to Kaggle prep*

### 1.1 iPad-Mac Bridge Finalization

**New Directory Structure:**
```
apps/backend/api/
├── routes/sync/          # New: Unified sync endpoints
│   ├── workspace.py      # Bidirectional workspace sync
│   ├── chat.py           # Chat history sync
│   └── discovery.py      # P2P + LAN + cloud relay
├── services/sync/        # New: Sync business logic
│   ├── workspace_sync.py
│   ├── chat_sync.py
│   └── conflict_resolver.py
└── mesh/                 # Existing P2P code (refactor)
```

**Deliverables:**
- [ ] Workspace bidirectional sync API
- [ ] Chat session sync with conflict resolution
- [ ] Discovery protocol unification (P2P, LAN, cloud relay)
- [ ] WiFi Aware integration tests
- [ ] Offline → online transition handling

### 1.2 Cross-Platform Validation

- [ ] Test handoff scenarios
- [ ] Verify offline → online transitions
- [ ] Ensure data integrity across sync

---

## Phase 2: Major UI/UX Refactor (Weeks 7-12)

### Phase 2A: Backend Preparation (Week 7-8)

**Goal:** Decouple backend services so each spawnable window can operate independently.

#### 2A.1: Service Decomposition

Break up god objects following iPad's pattern:

**Before (Current):**
```
data_engine.py (2000+ lines)
  ├── File parsing
  ├── Schema inference
  ├── Data cleaning
  ├── SQL generation
  ├── Query execution
  └── Metadata management
```

**After (iPad-style):**
```
services/data_engine/
├── __init__.py              # Clean facade
├── parsers/
│   ├── excel.py             # Single responsibility
│   ├── csv.py
│   ├── json.py
│   └── parquet.py
├── schema_inference.py
├── sql_generator.py
├── query_executor.py
└── metadata.py
```

**Same for workflow_orchestrator.py (750 lines):**
```
services/workflow/
├── __init__.py
├── state_machine.py
├── stage_router.py
├── sla_tracker.py
├── queue_manager.py
└── storage.py
```

#### 2A.2: State Management Refactor

**iPad Pattern:**
```swift
@MainActor @Observable
class LocalChatStore {
    var sessions: [LocalChatSession] = []
    var currentSession: LocalChatSession?
    var isLoading: Bool = false
}
```

**Mac Equivalent (New):**
```python
# apps/backend/api/core/stores/chat_store.py
from threading import RLock
from typing import Optional
from pydantic import BaseModel

class ChatState(BaseModel):
    sessions: list[ChatSession] = []
    current_session_id: Optional[str] = None
    is_loading: bool = False

class ChatStore:
    """Thread-safe chat state management (iPad philosophy)"""
    _lock = RLock()
    _state: ChatState

    def get_current_session(self) -> Optional[ChatSession]:
        with self._lock:
            return next((s for s in self._state.sessions
                        if s.id == self._state.current_session_id), None)
```

**Replace all global state in `core/state.py`:**
```python
# OLD (Thread-unsafe)
sessions: dict[str, dict] = {}
query_results: dict[str, pd.DataFrame] = {}

# NEW (Thread-safe stores)
from api.core.stores import ChatStore, QueryStore, SessionStore

chat_store = ChatStore()
query_store = QueryStore()  # With LRU eviction
session_store = SessionStore()
```

#### 2A.3: Database Access Centralization

```python
# apps/backend/api/db/registry.py
class DatabaseRegistry:
    """Single source of truth for all database connections"""

    _pools: dict[str, SQLiteConnectionPool] = {}

    @classmethod
    def get_connection(cls, db_name: str) -> ContextManager[sqlite3.Connection]:
        """All 124 files should use this instead of sqlite3.connect()"""
        if db_name not in cls._pools:
            cls._pools[db_name] = SQLiteConnectionPool(
                get_config_paths().get_db_path(db_name),
                min_size=2, max_size=10
            )
        return cls._pools[db_name].get_connection()
```

**Migration path:**
1. Create `DatabaseRegistry`
2. Add linter rule banning `sqlite3.connect()`
3. Migrate 124 files incrementally

---

### Phase 2B: Main Interface Redesign (Week 9-10)

#### 2B.1: Core Always-On Interface

**Header Simplification:**
```
Current: [Logo] [Search] [Notifications] [User] [Settings] [Help] [...]
Target:  [Logo] [Tab Switcher] [Quick Action Button]
```

**Quick Action Button (Control Center style):**
```python
# apps/backend/api/routes/quick_actions.py
@router.get("/quick-actions")
async def get_quick_actions(
    current_user: User = Depends(get_current_user)
) -> QuickActionsResponse:
    """Return user's configured quick actions"""
    return QuickActionsResponse(
        workflows=user_workflows,
        automations=user_automations,
        recent_documents=recent_docs[:5],
        settings_shortcuts=["appearance", "ai_models", "sync"]
    )
```

#### 2B.2: Workspace/Channels (Slack-style)

```python
# apps/backend/api/models/workspace.py
class Workspace(BaseModel):
    id: str
    name: str
    type: Literal["individual", "team"]
    channels: list[Channel] = []

class Channel(BaseModel):
    id: str
    name: str
    workspace_id: str
    is_private: bool = False
    members: list[str] = []  # user_ids
```

#### 2B.3: Data Section Redesign

- Adopt iPad's clean data interface design
- Simplify navigation and hierarchy
- Improve visual clarity

#### 2B.4: Files Tab (Vault → Files)

**API Structure:**
```
apps/backend/api/routes/files/
├── __init__.py
├── browse.py          # Hierarchical folder structure
├── upload.py          # File upload with routing
├── download.py        # File retrieval
├── search.py          # Search + filter
└── security.py        # Lock/unlock status
```

**Design:** "Finder meets Proton Drive" with clear locked vs unlocked visual distinction.

---

### Phase 2C: Spawnable Windows Architecture (Week 11)

#### Window Types

| Window | Default | Pop-out Behavior |
|--------|---------|------------------|
| Documents | Main window | Pages aesthetic + AI chat specific to doc |
| Spreadsheets | Main window | Numbers aesthetic + AI chat specific to sheet |
| PDF Editor | Main window | Preview + Adobe power |
| Code | Spawned | Always connected to workspace context |
| Project Mgmt | OFF (toggleable) | Kanban/Confluence style |
| Automations | OFF (toggleable) | Workflow builder |

#### Backend Support for Spawnable Windows

```python
# apps/backend/api/services/window_context.py
class WindowContext:
    """Maintain context for spawned windows"""

    def __init__(self, window_id: str, document_id: str):
        self.window_id = window_id
        self.document_id = document_id
        self.chat_session_id = self._create_doc_chat_session()

    async def get_ai_context(self) -> dict:
        """Return document-specific AI context"""
        document = await self.get_document()
        return {
            "document_content": document.content[:4000],
            "document_type": document.type,
            "document_metadata": document.metadata,
            "chat_history": await self.get_chat_history()
        }
```

#### Chat Persistence for Popped Windows

```python
# When window closes, chat is saved to workspace
class DocumentChatSession(BaseModel):
    id: str
    document_id: str
    workspace_id: str
    messages: list[ChatMessage]
    created_at: datetime
    last_accessed: datetime

# Can be reopened later
@router.get("/documents/{doc_id}/chat-history")
async def get_document_chat_history(doc_id: str):
    """Retrieve chat history for a specific document"""
```

#### Code Integration

- Code built into Studio (not separate app)
- Button/menu: "Open Code Window"
- Spawns separate window
- Always connected to Studio workspace context
- Can run independently alongside main window
- Code also available as standalone app (same codebase, different distribution)

---

### Phase 2D: Feature Toggles & Settings (Week 12)

**iPad Pattern:** Features OFF by default, enable in settings

```python
# apps/backend/api/models/feature_flags.py
class FeatureFlags(BaseModel):
    """User-configurable feature toggles"""

    # Core features (always ON)
    workspace: bool = True
    chat: bool = True
    files: bool = True

    # Optional features (OFF by default)
    project_management: bool = False  # Kanban/Confluence
    automations: bool = False         # Workflow builder
    data_analysis: bool = False       # NeutronCore
    voice_transcription: bool = True  # Key differentiator

    # Advanced (hidden in developer settings)
    developer_mode: bool = False
    debug_logging: bool = False
```

**Settings API:**
```python
@router.get("/settings/features")
async def get_feature_flags(user: User = Depends(get_current_user)):
    return user.feature_flags

@router.patch("/settings/features")
async def update_feature_flags(
    updates: dict,
    user: User = Depends(get_current_user)
):
    # Validate updates, update preferences, return new state
```

---

## Hugging Face Integration

### Context: Kaggle MedGemma Impact Challenge

- **Prize Pool:** $100,000
- **Deadline:** February 24, 2026
- **Requirement:** Build human-centered AI applications using MedGemma
- **Model:** MedGemma 1.5 4B (released Jan 13, 2026, available on Hugging Face)

### Model Management Window

#### Dual Model Source Support

**Ollama Integration (existing):**
- Browse Ollama catalog in-app
- Copy model name → paste → download
- Backend: `ollama pull [model-name]`
- List view: `ollama list`
- Actions: update | delete

**Hugging Face Integration (new):**
- Browse Hugging Face Hub in-app
- Support for multiple formats: GGUF, PyTorch, ONNX, Safetensors
- Download with quantization options (4-bit, 8-bit, full precision)
- Progress bar with speed/ETA

### Directory Structure

```
apps/backend/api/
├── services/models/           # New model management
│   ├── __init__.py
│   ├── provider_interface.py  # Abstract provider
│   ├── ollama_provider.py     # Existing Ollama
│   ├── huggingface_provider.py # NEW: HF integration
│   ├── model_manager.py       # Unified model mgmt
│   └── download_manager.py    # Queue + progress
├── routes/models/            # Model management API
│   ├── browse.py             # HF Hub browser
│   ├── download.py           # Download with progress
│   └── manage.py             # List, update, delete
```

### Model Provider Interface

```python
class ModelProvider(Protocol):
    async def list_models(self) -> list[ModelInfo]: ...
    async def download_model(self, model_id: str, options: DownloadOptions) -> AsyncIterator[DownloadProgress]: ...
    async def delete_model(self, model_id: str) -> bool: ...
    async def load_model(self, model_id: str) -> LoadedModel: ...
    async def generate(self, prompt: str, params: InferenceParams) -> AsyncIterator[str]: ...
```

### Unified Model Selector

```python
class UnifiedModelSelector:
    """Single interface for all AI features - app doesn't care about source"""

    providers: dict[str, ModelProvider] = {
        "ollama": OllamaProvider(),
        "huggingface": HuggingFaceProvider(),
        "local": LocalModelProvider()
    }

    async def get_available_models(self) -> list[ModelInfo]:
        """Aggregate models from all providers"""
        all_models = []
        for provider in self.providers.values():
            all_models.extend(await provider.list_models())
        return all_models
```

### Implementation Priority

**Phase 1 (Essential for Kaggle - Weeks 3-4):**
- [ ] Basic HF model download (GGUF format only)
- [ ] MedGemma 1.5 4B integration specifically
- [ ] Unified model selector UI
- [ ] llama.cpp inference for HF GGUF models

**Phase 2 (Post-Kaggle):**
- [ ] Full HF Hub browser integration
- [ ] PyTorch model support
- [ ] Model conversion tools
- [ ] Advanced model management

**Phase 3 (Future):**
- [ ] Fine-tuning interface
- [ ] Model upload to HF
- [ ] Collaborative model sharing
- [ ] Enterprise model registry

### Healthcare/Kaggle Specific Models

- **MedGemma:** `google/medgemma-2b` - Pre-configured for medical tasks
- **BioMistral, Med-PaLM variants:** Access to open medical models
- **Specialized:** Radiology (image analysis), Clinical notes (NER/summarization), Drug interaction (safety checking)

---

## Cleanup: Technical Debt

### Deprecated Code Removal

**20+ deprecated facades to remove:**
- [ ] `chat_service.py` → Use `services/chat/`
- [ ] `vault_service.py` → Use `services/vault/`
- [ ] `team_service.py` → Use `routes/team/`
- [ ] `p2p_chat_service.py` → Use `mesh/`

**Strategy:**
1. Add `@deprecated(removal_version="2.0")` decorator
2. Add runtime warnings
3. Update all imports in one PR
4. Remove deprecated files

### Import Pattern Standardization

**Remove 200+ try/except import wrappers:**
```python
# CURRENT (Bad)
try:
    from .config import get_settings
except ImportError:
    from config import get_settings

# TARGET (Good)
from api.config import get_settings  # Always use absolute imports
```

**Enforcement:**
```toml
# pyproject.toml
[tool.ruff]
select = ["I"]  # isort rules
[tool.ruff.isort]
force-single-line = false
known-first-party = ["api", "packages"]
```

---

## Timeline Summary

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1-2 | Ship iPad | iPad app ready |
| 3-4 | Bridge + Kaggle | Workspace sync, MedGemma integration |
| 5-6 | Kaggle Polish | Submission ready, HF download working |
| 7-8 | 2A: Backend Prep | God object decomposition, state management |
| 9-10 | 2B: Interface | Header, Workspace/Channels, Files redesign |
| 11 | 2C: Windows | Spawnable window architecture |
| 12 | 2D: Toggles | Feature flags, settings, polish |
| 13+ | Feature Completion | Healthcare features, enterprise readiness |

---

## Success Criteria

### Design Philosophy Alignment
- [ ] Mac matches iPad's "less is more" clarity
- [ ] Features hidden by default, progressive disclosure
- [ ] Spawnable windows reduce cognitive load
- [ ] Single entry point simplicity

### Technical Quality
- [ ] Zero thread-unsafe global state
- [ ] Zero direct `sqlite3.connect()` (use registry)
- [ ] Zero god objects >500 lines
- [ ] Zero broad `except Exception` handlers

### User Experience
- [ ] Free tier drives adoption
- [ ] Team tier shows clear upgrade value
- [ ] Code integration proves local AI agent thesis
- [ ] Ready for investor demos

### Kaggle
- [ ] MedGemma 1.5 4B working by Feb 24
- [ ] Healthcare workflow queue functional
- [ ] Demo-ready for competition

---

## Pricing & Tiers

### Individual Tier: FREE
- Full access to core productivity suite
- Documents, spreadsheets, PDFs, notes
- Voice transcription
- Local AI integration
- Code mode included
- Single-user workspace

### Team Tier: PAID (Subscription)
- Everything in Individual
- Team collaboration features
- Multi-user workspaces
- Chat/messaging
- Shared workspace sync
- Team workflows and automations
- Priority support

### Pricing Structure (TBD)
- Monthly: $10-15/user/month
- Annual: $100-150/user/year (2 months free)
- Small team (5-10 users): discount tier
- Enterprise (custom): volume pricing

### MagnetarMission
- Unlocks Team tier for Christian organizations
- Free verification process
- Same features as paid Team tier

---

## Post-Refactor: Feature Completion

### Healthcare/Kaggle Features (if winning/continuing)
- [ ] Patient workflow queue (Kanban adaptation)
- [ ] Clinical note templates
- [ ] MedGemma integration for diagnostics
- [ ] HIPAA-compliant data handling

### Advanced Collaboration
- [ ] Enhanced offline mesh networking
- [ ] Improved conflict resolution
- [ ] Team permissions and roles
- [ ] Audit logs for team tier

### Enterprise Readiness (if needed)
- [ ] SSO integration
- [ ] Admin dashboard
- [ ] Usage analytics
- [ ] Deployment tooling
