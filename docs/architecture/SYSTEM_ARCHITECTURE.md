# ElohimOS System Architecture

**Version**: 1.0
**Last Updated**: 2025-11-11
**Platform**: macOS-only (Darwin)

---

## Executive Summary

ElohimOS is an **offline-first AI operating system** for mission-critical field operations. It provides a complete computing environment with AI capabilities, data processing, secure storage, and team collaboration - all functioning without internet connectivity.

### Core Design Principles

1. **Offline-First**: Everything works without internet
2. **"Dumb Core That Always Works"**: Simple, reliable foundation with smart features layered on top
3. **Zero-Trust Security**: End-to-end encryption, audit logging, panic mode
4. **Battery Efficiency**: ANE (Apple Neural Engine) routing for ultra-low power AI
5. **Field-Ready**: Designed for harsh conditions and limited resources

---

## Technology Stack

### Backend
- **Language**: Python 3.11/3.12
- **Framework**: FastAPI (async/await)
- **Database**: SQLite with WAL mode (8+ databases)
- **Data Processing**: DuckDB (in-memory OLAP), pandas, polars
- **AI/ML**: Ollama (local LLM), sentence-transformers, Whisper

### Frontend
- **Language**: TypeScript
- **Framework**: React 18.2
- **State Management**: Zustand 4.4 (13 stores)
- **Data Fetching**: TanStack Query 5.8
- **Build Tool**: Vite 5.4

### Apple Silicon Integration
- **GPU**: Metal 4 framework (compute shaders)
- **ML**: Metal Performance Shaders (MPS)
- **ANE**: Apple Neural Engine (ultra-low power)
- **PyObjC**: Python bindings for Metal framework

### Networking
- **P2P**: libp2p 0.1.5+ (mesh networking)
- **LAN Discovery**: zeroconf 0.132+ (Bonjour/mDNS)
- **WebSocket**: websockets 12.0+ (real-time communication)

### Encryption
- **Symmetric**: AES-256-GCM (Fernet)
- **Asymmetric**: X25519 (elliptic curve)
- **Hashing**: SHA-256, PBKDF2 (600k iterations)
- **Library**: PyNaCl 1.5.0 (libsodium)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
│  (TypeScript, Zustand, TanStack Query, Monaco Editor)          │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             │ HTTP/REST                          │ WebSocket
             │                                    │
┌────────────▼────────────────────────────────────▼───────────────┐
│                       FastAPI Backend                           │
│             (Python 3.12, asyncio, JWT auth)                    │
├─────────────────────────────────────────────────────────────────┤
│  Auth Middleware → Permission Engine → Audit Logger            │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐     │
│  │  Data    │   Chat   │  Vault   │  Team    │ Workflow │     │
│  │ Engine   │ Service  │ Service  │ Service  │  Service │     │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐     │
│  │Terminal  │   P2P    │  RBAC    │ Learning │  Metal4  │     │
│  │   API    │  Mesh    │  Engine  │  System  │  Engine  │     │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                   Data Access Layer                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  SQLite Databases (WAL mode)                           │    │
│  │  • elohimos_app.db  • vault.db      • workflows.db     │    │
│  │  • chat_memory.db   • teams.db      • learning.db      │    │
│  │  • datasets.db      • audit.db                         │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
             │                                    │
             │                                    │
┌────────────▼────────────────┐    ┌─────────────▼──────────────┐
│   Shared Packages           │    │  External Services         │
│  • neutron_core (DuckDB)    │    │  • Ollama (localhost:11434)│
│  • neutron_utils            │    │  • Metal 4 GPU             │
│  • pulsar_core (JSON)       │    │  • Apple Neural Engine     │
└─────────────────────────────┘    └────────────────────────────┘
```

---

## Component Architecture

### 1. Neutron Star Data Engine (Foundation)

**Purpose**: "Dumb core that always works" - Excel + SQL + DuckDB = Results

**Components**:
- `packages/neutron_core/engine.py` - NeutronEngine (DuckDB wrapper)
- `packages/neutron_utils/` - CSV/Excel/JSON utilities
- `apps/backend/api/data_engine.py` - Persistence layer (SQLite)

**Data Flow**:
```
User uploads Excel/CSV/JSON
    ↓
File reading (multi-format, multi-strategy)
    ├─→ Try DuckDB direct read
    ├─→ Fallback to pandas
    └─→ Fallback to stream-to-CSV
    ↓
Auto-type inference (optional)
    ↓
Load into DuckDB (in-memory)
    ↓
Store metadata in SQLite (datasets.db)
    ↓
Brute-force schema discovery
    ↓
Generate query suggestions
```

**Key Features**:
- Multi-dialect SQL translation (Redshift, PostgreSQL, MySQL, BigQuery)
- Auto-type inference (numeric detection, date parsing)
- Column name cleaning (SQL-safe)
- Streaming for large files (>100MB)
- Memory management (4GB limit, LRU eviction)

---

### 2. Pulsar JSON Pipeline

**Purpose**: Industrial-strength JSON normalization and Excel conversion

**Components**:
- `packages/pulsar_core/engine.py` - JsonToExcelEngine
- `packages/pulsar_core/json_parser.py` - V1 parser (safe, non-expanding)
- `packages/pulsar_core/json_parser_v2.py` - V2 parser (array expansion)
- `packages/pulsar_core/json_streamer.py` - Streaming parser (large files)

**Data Flow**:
```
JSON file upload
    ↓
Detect structure (objects, arrays, nesting)
    ↓
Estimate row expansion (prevent explosion)
    ↓
[If safe] Flatten with array expansion
[If unsafe] Auto-safe mode (arrays → separate sheets)
    ↓
Export to multi-sheet Excel
```

**Auto-Safe Mechanism**:
- Threshold: 100k rows (configurable)
- Cartesian explosion prevention
- Memory-aware fallbacks

---

### 3. AI Chat + RAG System

**Purpose**: Local AI chat with retrieval augmented generation

**Components**:
- `apps/backend/api/chat_service.py` - Chat orchestration (2,231 lines)
- `apps/backend/api/jarvis_rag_pipeline.py` - RAG implementation
- `apps/backend/api/metal4_mps_embedder.py` - GPU embeddings
- `apps/backend/api/adaptive_router.py` - Model selection
- `chat_memory.db` - Session persistence

**Data Flow**:
```
User message + file attachments
    ↓
Extract text from files (PDF, DOCX, images)
    ↓
Generate embeddings (Metal 4 MPS or ANE)
    ↓
Vector search in local knowledge base
    ↓
Retrieve top-K relevant chunks
    ↓
Build prompt (message + context + history)
    ↓
Route to Ollama model (via ANE router)
    ↓
Stream response token-by-token (SSE)
    ↓
Store in chat memory (rolling summaries)
```

**RAG Pipeline**:
- Document chunking: 512 tokens with 50-token overlap
- Embedding model: sentence-transformers (all-MiniLM-L6-v2)
- Vector store: FAISS or ChromaDB
- Semantic search: Cosine similarity

**Ollama Integration**:
- Local inference (no cloud calls)
- Streaming responses (Server-Sent Events)
- Model management (list, pull, delete)
- Custom system prompts

---

### 4. Vault System (Encrypted Storage)

**Purpose**: Zero-knowledge encrypted storage with plausible deniability

**Components**:
- `apps/backend/api/vault_service.py` - Vault management (5,356 lines)
- `apps/backend/api/team_crypto.py` - Team vault encryption
- `vault.db` - Encrypted blob storage
- `.neutron_data/vault_files/` - Encrypted file storage

**Data Flow**:
```
[Client-Side Encryption]
User creates document
    ↓
Browser generates encryption key (Web Crypto API)
    ↓
Browser encrypts document + metadata
    ↓
[Server-Side Storage]
Upload encrypted blob to server
    ↓
Server stores blob (cannot read)
    ↓
[Client-Side Decryption]
Client retrieves encrypted blob
    ↓
Browser decrypts with stored key
    ↓
User views document
```

**Security Model**:
- **Zero-knowledge**: Server cannot read vault contents
- **Client-side encryption**: AES-256-GCM in browser
- **Plausible deniability**: Two vaults (real + decoy) with different passwords
- **Team vault**: Shared key distribution with member public keys

---

### 5. Team Collaboration System

**Purpose**: Complete team management with offline P2P sync

**Components**:
- `apps/backend/api/team_service.py` - Team management (5,145 lines)
- `apps/backend/api/p2p_mesh_service.py` - P2P networking
- `apps/backend/api/p2p_chat_service.py` - Mesh messaging
- `teams.db` - Team data

**Data Flow**:
```
Team creation
    ↓
Generate invite code (OMNI-XXXX-XXXX)
    ↓
Member joins with code
    ↓
Role assignment (Super Admin / Admin / Member / Guest)
    ↓
Team workspace access (vault, workflows, chat)
    ↓
P2P sync via libp2p mesh
```

**Roles**:
- **Super Admin**: Full control, cannot be removed
- **Admin**: Manage members, cannot remove Super Admin
- **Member**: Standard access
- **Guest**: Read-only

**Offline Failsafe**:
- If Super Admin offline >30 days
- Admin can request temporary promotion
- Requires approval from another Admin

---

### 6. Workflow Automation System

**Purpose**: n8n-inspired workflow orchestration with queues and SLAs

**Components**:
- `apps/backend/api/workflow_service.py` - Workflow engine (795 lines)
- `apps/backend/api/workflow_orchestrator.py` - State machine
- `workflows.db` - Workflow definitions and work items

**Data Flow**:
```
Workflow definition (stages + triggers)
    ↓
Create work item (manual or automated)
    ↓
Work item enters queue
    ↓
User claims work item
    ↓
User completes stage
    ↓
Auto-transition to next stage or complete
```

**Work Item Lifecycle**:
```
QUEUED → CLAIMED → IN_PROGRESS → COMPLETED
```

**Queue System**:
- Role-based assignment
- Priority sorting
- SLA tracking (warnings at 80%, overdue at 100%)
- P2P sync for team workflows

---

### 7. P2P Mesh Network

**Purpose**: Device-to-device collaboration without internet

**Components**:
- `apps/backend/api/p2p_mesh_service.py` - Connection management
- `apps/backend/api/offline_mesh_router.py` - Message routing
- `apps/backend/api/lan_discovery.py` - Bonjour/mDNS discovery

**Data Flow**:
```
[LAN Discovery]
Device A broadcasts on mDNS
    ↓
Device B discovers Device A
    ↓
[Manual Pairing]
Device A generates connection code
    ↓
User shares code to Device B (voice, SMS, etc.)
    ↓
Device B enters code
    ↓
[libp2p Connection]
Device B connects to Device A
    ↓
Encrypted P2P channel established
    ↓
[Mesh Routing]
Message sent from A → B → C (multi-hop)
```

**Connection Code System**:
- Format: `OMNI-XXXX-XXXX` (8 characters)
- Single-use codes
- Expires in 7 days (configurable)
- Stored in `p2p_connection_codes.db`

**Mesh Routing**:
- Flood routing with TTL
- Seen message cache (deduplication)
- Dead peer detection (30s timeout)

---

### 8. RBAC System (Permission Engine)

**Purpose**: Salesforce-style role-based access control

**Components**:
- `apps/backend/api/permission_engine.py` - Permission resolution
- `apps/backend/api/permissions_admin.py` - Admin UI
- `elohimos_app.db` - Permission data

**Permission Resolution Order**:
```
1. Founder Rights? → Allow all (bypass)
    ↓
2. Super Admin? → Allow unless explicitly restricted
    ↓
3. Load role baseline permissions
    ↓
4. Apply permission profiles (union)
    ↓
5. Apply permission sets (override)
    ↓
6. Return effective permissions
```

**Permission Types**:
- **Boolean**: true/false (e.g., `workflows.create`)
- **Level**: none/read/write/admin (e.g., `vault.access`)
- **Scope**: object-based (e.g., `{own_only: true}`)

**Caching**:
- In-memory cache (5-minute TTL)
- Cache key: `{user_id}:{team_id}`
- Invalidate on permission change

---

### 9. Code Editor + Terminal

**Purpose**: Full-featured development environment

**Components**:
- `apps/backend/api/code_editor_service.py` - File operations (765 lines)
- `apps/backend/api/terminal_api.py` - Terminal sessions (734 lines)
- `apps/backend/api/agent/engines/continue_engine.py` - Continue CLI
- `apps/backend/api/agent/engines/aider_engine.py` - Aider integration

**Terminal Persistence**:
```
Terminal session created (PTY)
    ↓
All I/O logged to database
    ↓
[User reloads page]
    ↓
Restore session from database
    ↓
Replay command history
    ↓
Re-attach to running processes (if still alive)
```

**Continue CLI Integration**:
- Inline code completion
- Multi-file context
- Codebase search
- Refactoring suggestions

**Aider Integration**:
- AI pair programming
- Multi-file edits
- Git commit generation

---

### 10. Metal 4 GPU Acceleration

**Purpose**: Apple Silicon GPU acceleration for ML operations

**Components**:
- `apps/backend/api/metal4_engine.py` - GPU device management
- `apps/backend/api/metal4_tensor_ops.py` - Tensor operations
- `apps/backend/api/metal4_mps_embedder.py` - Embedding generation

**Performance Comparison**:
```
Embedding Generation (1000 sentences):
- CPU (NumPy):    500 sentences/sec
- MLX (M2 Max):   2,000 sentences/sec
- Metal 4:        5,000 sentences/sec (10x faster)

Vector Search (1M vectors, 768 dim):
- CPU:            ~500ms
- MLX:            ~50ms
- Metal 4:        ~10ms (50x faster)
```

**When to Use**:
- **Metal 4**: Performance-critical operations, custom kernels
- **MLX**: Standard ML operations, prototyping
- **CPU**: Fallback when GPU unavailable

---

### 11. ANE Routing (Battery Optimization)

**Purpose**: Route small tasks to Apple Neural Engine for ultra-low power

**Components**:
- `apps/backend/api/ane_router.py` - Routing decisions
- `apps/backend/api/learning_system.py` - Adaptive learning

**Routing Decision**:
```
Task arrives
    ↓
Estimate cost (tokens × complexity)
    ↓
Cost < threshold (512 tokens)?
    ├─→ [Yes] Route to ANE (ultra-low power)
    └─→ [No] Route to Metal 4 GPU
    ↓
Update performance metrics
    ↓
Learning system adjusts thresholds
```

**Battery Impact**:
- ANE: ~50% battery savings vs CPU
- Critical for multi-day field deployments

---

## Database Architecture

### Database List

All databases stored in `.neutron_data/`:

1. **elohimos_app.db** (260 KB) - Main application
   - users, teams, team_members, permissions
   - invite_codes, delayed_promotions
   - audit_log (cross-references other DBs)

2. **vault.db** - Encrypted vault storage
   - vault_documents (real + decoy)
   - vault_files, vault_file_versions
   - team_vault_items

3. **datasets.db** - Data engine
   - dataset_metadata
   - ds_{hash} (dynamic tables per upload)

4. **chat_memory.db** (28 KB) - AI chat
   - chat_sessions, chat_messages
   - chat_summaries (rolling summaries)

5. **teams.db** (116 KB) - Team collaboration
   - teams, team_members, team_invites
   - team_vault_items, team_chat_messages

6. **workflows.db** (112 KB) - Workflow automation
   - workflows, work_items
   - workflow_history

7. **learning.db** (20 KB) - Adaptive learning
   - learned_patterns (query templates, preferences)
   - performance_metrics (backend latency, throughput)

8. **audit.db** (40 KB) - Audit logging
   - audit_log (all operations, 90-day retention)

### Database Configuration

**All databases use**:
- SQLite 3.x
- WAL mode (Write-Ahead Logging) for concurrent access
- `PRAGMA synchronous=NORMAL` (balance safety vs performance)
- `PRAGMA temp_store=MEMORY` (fast temp tables)
- `PRAGMA mmap_size=30000000000` (30GB memory-mapped I/O)

### Relationships

```
elohimos_app.db (users, teams, permissions)
    ↓ user_id
vault.db (user-specific vaults)
chat_memory.db (user chat sessions)
    ↓ team_id
teams.db (team data)
workflows.db (team workflows)
    ↓ audit_log
audit.db (all operations)
```

---

## API Architecture

### Endpoint Structure

**Base URL**: `http://localhost:8000`

**Authentication**: JWT Bearer token in `Authorization` header

**Versioning**: `/api/v1/...`

### Main Routers

**Core Services**:
- `/api/v1/auth/*` - Authentication
- `/api/v1/data/*` - Data engine (upload, query, export)
- `/api/v1/chat/*` - AI chat
- `/api/v1/vault/*` - Encrypted vault
- `/api/v1/teams/*` - Team management
- `/api/v1/workflow/*` - Workflow automation
- `/api/v1/terminal/*` - Terminal sessions
- `/api/v1/p2p/*` - P2P mesh

**System**:
- `/health` - Health check
- `/diagnostics` - System diagnostics
- `/metrics` - Prometheus metrics

### Middleware Stack

```
Request arrives
    ↓
CORS middleware
    ↓
Auth middleware (JWT verification)
    ↓
Rate limiting (slowapi)
    ↓
Permission engine (@require_perm decorator)
    ↓
Route handler
    ↓
Audit logger (automatic)
    ↓
Response
```

### WebSocket Endpoints

- `/api/v1/terminal/ws/{session_id}` - Terminal I/O
- `/api/v1/chat/stream` - Chat streaming (SSE alternative)
- `/api/v1/p2p/ws` - P2P mesh events

---

## Security Architecture

### Encryption Layers

**1. Client-Side Encryption** (Vault):
- Web Crypto API (browser)
- AES-256-GCM (Fernet)
- Keys never leave client

**2. Database Encryption** (Optional):
- SQLCipher for database-level encryption
- Currently: Filesystem-level (FileVault on macOS)

**3. Network Encryption** (P2P):
- libp2p secio (encrypted channels)
- TLS for WebSocket (optional)

**4. Key Management**:
- Secure Enclave (macOS Keychain)
- PBKDF2 key derivation (600k iterations)

### Authentication Flow

```
User enters credentials
    ↓
POST /api/v1/auth/login
    ↓
Server verifies password (PBKDF2)
    ↓
Generate JWT (HS256, 24-hour expiration)
    ↓
Return JWT to client
    ↓
Client stores in localStorage
    ↓
[Every Request]
    ↓
Client sends JWT in Authorization header
    ↓
Server verifies JWT signature
    ↓
Extract user_id from claims
    ↓
Load user context (role, team, permissions)
    ↓
Check permissions
    ↓
Execute request
```

### Rate Limiting

**Global**: 100 req/min
**Login**: 5 failures/15min → account lockout
**Invite codes**: 5 failures/hour → IP block
**Write operations**: 30 req/min
**Delete operations**: 20 req/min

### Audit Logging

**All operations logged**:
- User ID, action, resource, timestamp
- IP address, user agent
- Success/failure
- Additional context (sanitized)

**Retention**: 90 days, then auto-delete

---

## Performance Optimizations

### Backend

1. **Connection Pooling**: Single SQLite connection per database
2. **Query Caching**: 500MB total, 100MB per result, LRU eviction
3. **Request Deduplication**: 60-second window
4. **Batch Operations**: Group multiple updates
5. **Lazy Loading**: Only load metadata initially
6. **Pre-compiled Regex**: Module-level patterns

### Frontend

1. **Code Splitting**: Manual chunks (React, TanStack, Monaco)
2. **Lazy Loading**: Suspense boundaries for heavy components
3. **Service Worker**: Offline support (production only)
4. **Debounced Saves**: Wait 500ms before saving
5. **Virtual Scrolling**: For large lists

### Database

1. **WAL Mode**: Concurrent reads, non-blocking writes
2. **Indexes**: Strategic indexes on foreign keys, timestamps
3. **VACUUM**: Weekly automatic cleanup
4. **Memory-Mapped I/O**: 30GB mmap_size

### Metal 4 / ANE

1. **Batch Processing**: Group embeddings
2. **Memory Pooling**: Reuse GPU buffers
3. **Lazy Model Loading**: Load on first use
4. **ANE Routing**: Small tasks to ANE (50% battery savings)

---

## Deployment Architecture

### Development

```
Developer Machine (macOS)
    ↓
./elohim script
    ├─→ Backend (Uvicorn, port 8000)
    └─→ Frontend (Vite dev server, port 4200)
    ↓
Ollama (localhost:11434)
Metal 4 / ANE (local GPU)
```

### Production (Field Deployment)

```
User Device (MacBook, offline)
    ↓
ElohimOS App Bundle
    ├─→ Backend (embedded)
    ├─→ Frontend (embedded)
    └─→ Ollama (bundled models)
    ↓
Local Databases (.neutron_data/)
P2P Mesh (LAN or ad-hoc WiFi)
```

### Future: Cloud with Local Resilience

```
Cloud Server (AWS/GCP)
    ├─→ Multi-tenant backend
    ├─→ Team workspace sync
    └─→ Model hosting (optional)
    ↓
User Device (still works offline)
    ├─→ Local cache
    ├─→ Offline queue
    └─→ Auto-sync when online
```

---

## Failure Modes & Recovery

### Critical Failures

**1. Database Corruption**
- **Detection**: SQLite integrity check on startup
- **Recovery**: Restore from backup, replay audit log
- **Mitigation**: WAL mode, auto-backup, VACUUM

**2. Ollama Model Unavailable**
- **Detection**: Health check on startup
- **Recovery**: CPU fallback (slow but works)
- **Mitigation**: Bundle models in installer

**3. Vault Encryption Key Lost**
- **Detection**: User cannot decrypt vault
- **Recovery**: UNRECOVERABLE (by design)
- **Mitigation**: User education, paper wallet backup

**4. P2P Sync Conflict**
- **Detection**: Timestamp comparison
- **Recovery**: Last-write-wins, show warning
- **Mitigation**: Audit trail, manual merge tool

**5. Battery Drain**
- **Detection**: System power monitoring
- **Recovery**: ANE routing, model unloading
- **Mitigation**: Throttle P2P, reduce batch sizes

### Non-Critical Failures

**6. File Upload Too Large**
- **Detection**: Size check before upload
- **Recovery**: Reject with error message
- **Mitigation**: Stream to disk, chunk uploads

**7. SQL Query Timeout**
- **Detection**: DuckDB timeout (300s default)
- **Recovery**: Return partial results
- **Mitigation**: Query optimization hints

**8. Metal 4 GPU Unavailable**
- **Detection**: Device query on startup
- **Recovery**: Fall back to MLX or CPU
- **Mitigation**: Graceful degradation

---

## Future Architecture (Cloud + Local)

### Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Backend                          │
│  • Multi-tenant workspace                                   │
│  • Team sync server                                         │
│  • Model hosting (optional)                                 │
│  • Analytics                                                │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTPS (when online)
             │
┌────────────▼────────────────────────────────────────────────┐
│                  Local ElohimOS Client                      │
│  • Full offline functionality                               │
│  • Local cache                                              │
│  • Offline queue                                            │
│  • Auto-sync when online                                    │
└─────────────────────────────────────────────────────────────┘
```

### Migration Path

**Phase 1**: Add cloud sync (optional)
**Phase 2**: Multi-tenant SaaS
**Phase 3**: Enterprise features (SSO, LDAP)
**Phase 4**: Mobile companion app

---

## Conclusion

ElohimOS is a **complete offline-first operating system** designed for mission-critical field operations. Its architecture prioritizes:

1. **Reliability**: "Dumb core that always works" with multiple fallback chains
2. **Security**: Zero-knowledge encryption, E2E, plausible deniability
3. **Performance**: Metal 4 GPU, ANE routing, efficient caching
4. **Offline**: Everything works without internet
5. **Maintainability**: Clear separation of concerns, documented patterns

The system is **production-ready** for field deployment while maintaining a clear path to cloud expansion.
