# ElohimOS Developer Onboarding Guide

Welcome to ElohimOS! This guide will get you up and running as a contributor.

## What is ElohimOS?

ElohimOS is an **offline-first AI operating system** for field operations (missionaries, Doctors Without Borders, disaster relief). It provides a complete computing environment with AI, data processing, secure storage, and team collaboration - all working without internet.

Think: "macOS for field workers who need AI and data tools that work offline."

## High-Level Architecture

ElohimOS is a **monorepo** with 15+ integrated subsystems:

```
ElohimOS/
├── apps/
│   ├── backend/          # Python/FastAPI backend (149 modules)
│   └── frontend/         # React/TypeScript frontend (119 components)
├── packages/
│   ├── neutron_core/     # Core SQL/data engine (DuckDB)
│   ├── neutron_utils/    # Data utilities (CSV, Excel, JSON)
│   └── pulsar_core/      # JSON normalization engine
└── tools/
    ├── config/           # Configuration templates
    └── scripts/          # Setup and deployment scripts
```

### The 15+ Major Subsystems

1. **Neutron Star Data Engine** - Excel/CSV/SQL processing (the "dumb core that always works")
2. **Pulsar JSON Pipeline** - Industrial-strength JSON normalization
3. **AI Chat + RAG** - Local LLM with Ollama, vector search, embeddings
4. **Vault System** - End-to-end encrypted storage with plausible deniability
5. **Team Collaboration** - Invite codes, roles, permissions, team vault
6. **P2P Mesh Network** - Device-to-device sync without internet (libp2p)
7. **Workflow Automation** - n8n-style queue system with SLA tracking
8. **Code Editor + Terminal** - Monaco editor, persistent terminal, Continue/Aider
9. **RBAC System** - Salesforce-style permissions (roles, profiles, sets)
10. **Metal 4 GPU** - Apple Silicon acceleration for ML operations
11. **ANE Routing** - Ultra-low power inference on Apple Neural Engine
12. **Adaptive Learning** - Learns from user behavior to optimize performance
13. **Whisper Insights** - Offline audio transcription and analysis
14. **BigQuery-adapted SQLite** - Backend process orchestration
15. **Context Preservation** - Session persistence and state management

## Where Things Live

### Backend (Python)

**Entry Point**: `apps/backend/api/main.py` (2,798 lines)

**Major Services**:
- `data_engine.py` - Data upload and SQL query execution
- `chat_service.py` - AI chat with Ollama (2,231 lines)
- `vault_service.py` - Encrypted storage (5,356 lines)
- `team_service.py` - Team management (5,145 lines)
- `workflow_service.py` - Workflow automation (795 lines)
- `terminal_api.py` - Terminal sessions (734 lines)
- `p2p_mesh_service.py` - P2P networking (402 lines)
- `permission_engine.py` - RBAC system

**Shared Packages**:
- `packages/neutron_core/engine.py` - Core DuckDB SQL engine (876 lines)
- `packages/pulsar_core/engine.py` - JSON to Excel converter (981 lines)
- `packages/neutron_utils/` - Utilities (CSV, Excel, SQL helpers)

### Frontend (React/TypeScript)

**Entry Point**: `apps/frontend/src/App.tsx`

**Main Features**:
- Data tab - File upload, SQL editor, query results
- Chat tab - AI chat with Ollama models
- Code tab - Monaco editor, terminal, file browser
- Team tab - Team workspace, chat, vault

**State Management**: Zustand (13 stores in `src/stores/`)

**API Integration**: `src/lib/api.ts` (Axios client)

### Databases

All databases are in `.neutron_data/`:

- `elohimos_app.db` - Main application (users, teams, permissions)
- `vault.db` - Encrypted vault storage (real + decoy vaults)
- `datasets.db` - Data engine (uploaded files)
- `chat_memory.db` - Chat history and sessions
- `teams.db` - Team collaboration
- `workflows.db` - Workflow automation
- `learning.db` - Adaptive learning system
- `audit.db` - Audit logs (90-day retention)

## Getting Started

### Prerequisites

- **macOS 12+** (Monterey or newer) - ElohimOS is macOS-only
- **Python 3.11 or 3.12** (3.14 works but MLX not supported)
- **Node.js 18+**
- **Ollama** - For local AI inference

### Installation

1. **Clone the repository**:
```bash
git clone <repo-url>
cd ElohimOS
```

2. **Setup Python environment**:
```bash
./tools/scripts/setup_python_env.sh
source venv/bin/activate
```

3. **Install Python dependencies**:
```bash
pip install -r apps/backend/requirements.txt
```

4. **Install frontend dependencies**:
```bash
cd apps/frontend
npm install
cd ../..
```

5. **Install Ollama** (if not already installed):
```bash
brew install ollama
ollama serve
```

6. **Pull required models**:
```bash
ollama pull qwen2.5-coder:14b
ollama pull phi3.5:3.8b
```

### Running Locally

**Option 1: Quick Start** (recommended):
```bash
./elohim
```

This script:
- Activates Python venv
- Starts Ollama (if not running)
- Validates Metal 4 GPU
- Starts backend (port 8000)
- Starts frontend (port 4200)
- Opens browser

**Option 2: Manual Start**:

Terminal 1 (Backend):
```bash
source venv/bin/activate
cd apps/backend/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (Frontend):
```bash
cd apps/frontend
npm run dev
```

**Access**:
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (Swagger UI)

### Verify Setup

1. **Check backend health**:
```bash
curl http://localhost:8000/health
```

2. **Check Ollama**:
```bash
curl http://localhost:11434/api/tags
```

3. **Check Metal 4 availability**:
```bash
python3 -c "import Metal; print('Metal 4 available')"
```

4. **Open frontend**: Navigate to http://localhost:4200

## Project Structure Deep Dive

### Backend Architecture

```
apps/backend/api/
├── main.py                    # FastAPI app, routes, middleware
├── config.py                  # Environment variables, settings
├── auth_middleware.py         # JWT authentication
├── permission_engine.py       # RBAC system
├── audit_logger.py            # Audit logging
│
├── data_engine.py             # Data upload/query
├── chat_service.py            # AI chat with Ollama
├── vault_service.py           # Encrypted vault
├── team_service.py            # Team management
├── workflow_service.py        # Workflow automation
├── terminal_api.py            # Terminal sessions
├── p2p_mesh_service.py        # P2P networking
│
├── metal4_engine.py           # Metal 4 GPU acceleration
├── ane_router.py              # Apple Neural Engine routing
├── learning_system.py         # Adaptive learning
├── jarvis_memory.py           # Context preservation
│
└── migrations/                # Database migrations
```

### Frontend Architecture

```
apps/frontend/src/
├── App.tsx                    # Main app component
├── components/
│   ├── FileUpload.tsx         # Data upload
│   ├── ChatWindow.tsx         # AI chat UI
│   ├── CodeWorkspace.tsx      # Code editor
│   ├── TeamWorkspace.tsx      # Team collaboration
│   └── ...
├── stores/                    # Zustand state management
│   ├── sessionStore.ts        # Session state
│   ├── chatStore.ts           # Chat state
│   ├── editorStore.ts         # Code editor state
│   └── ...
├── lib/
│   ├── api.ts                 # Axios API client
│   ├── websocketClient.ts     # WebSocket client
│   └── ...
└── vite.config.ts             # Vite build config
```

### Shared Packages

**neutron_core** - Core SQL engine:
```
packages/neutron_core/
├── engine.py                  # NeutronEngine class (DuckDB wrapper)
└── __init__.py
```

**neutron_utils** - Utilities:
```
packages/neutron_utils/
├── config.py                  # Configuration management
├── csv_ops.py                 # CSV normalization
├── excel_ops.py               # Excel reading
├── json_utils.py              # JSON utilities
└── sql_utils.py               # SQL helpers (column cleaning)
```

**pulsar_core** - JSON pipeline:
```
packages/pulsar_core/
├── engine.py                  # JsonToExcelEngine
├── json_parser.py             # V1 parser (safe, non-expanding)
├── json_parser_v2.py          # V2 parser (array expansion)
├── json_streamer.py           # Streaming parser (large files)
├── json_normalizer.py         # Feed.json normalizer
└── excel_writer.py            # Excel export
```

## Key Concepts

### 1. Offline-First Architecture

**Everything works without internet**:
- AI inference (Ollama runs locally)
- Data processing (DuckDB in-memory)
- Encryption (client-side with Web Crypto API)
- Team collaboration (P2P mesh with libp2p)
- File storage (local SQLite + filesystem)

**What needs internet** (optional):
- Ollama model downloads (first-time setup)
- Python package updates
- Software updates

### 2. "Dumb Core That Always Works"

The Neutron Star Engine is intentionally simple:
- No cloud dependencies
- No complex ML in core path
- Fallback chains for everything (DuckDB → pandas → stream)
- Always returns a result (even if it's "file is empty")

Smart features are **layered on top**:
- Metal 4 GPU acceleration (optional)
- Auto-type inference (optional)
- RAG embeddings (optional)

### 3. Zero-Knowledge Encryption

The vault is **client-side encrypted**:
- Server stores only encrypted blobs
- Server cannot read vault contents
- Server cannot verify passwords
- Decryption happens entirely in browser (Web Crypto API)

This enables **plausible deniability**:
- Two vaults: "real" and "decoy"
- Different passwords unlock different vaults
- No way to prove which is real

### 4. P2P Mesh Networking

Team collaboration works **without server**:
- libp2p for peer-to-peer connections
- Bonjour/mDNS for LAN discovery
- Connection codes for manual pairing
- Multi-hop routing (A → B → C)

Critical for field operations without internet.

### 5. Apple Silicon Optimization

**Metal 4 GPU**:
- 5-10x faster embeddings
- 10-50x faster vector search
- Custom compute shaders

**ANE (Apple Neural Engine)**:
- Ultra-low power inference
- 50% battery savings for small tasks
- Automatic routing via adaptive learning

## Development Workflow

### Making Changes

1. **Create a feature branch**:
```bash
git checkout -b feature/my-feature
```

2. **Make your changes**

3. **Run linting** (optional, but recommended):
```bash
# Python
ruff check apps/backend/api/

# Frontend
cd apps/frontend
npm run lint
```

4. **Test locally** - Manual testing only (no automated tests yet)

5. **Commit changes**:
```bash
git add .
git commit -m "feat: Add my feature"
```

Pre-commit hooks will run:
- Black (Python formatting)
- isort (import sorting)
- Ruff (linting with auto-fix)
- ESLint (TypeScript/JavaScript)

6. **Push to remote**:
```bash
git push origin feature/my-feature
```

### Code Style

**Python**:
- Black formatting (line length 120)
- isort for import sorting
- Type hints encouraged (but not enforced)
- Docstrings for public functions

**TypeScript**:
- ESLint for linting
- Prettier for formatting (via ESLint)
- Functional components with hooks

### Common Tasks

**Add a new API endpoint**:
1. Add route to `main.py` or create new router
2. Add permission check (`@require_perm("feature.access")`)
3. Update frontend API client (`src/lib/api.ts`)
4. Add UI component

**Add a new database table**:
1. Create migration file in `apps/backend/api/migrations/`
2. Run migration (currently manual)
3. Update data model documentation

**Add a new Zustand store**:
1. Create file in `apps/frontend/src/stores/`
2. Use `createWithEqualityFn` from `zustand/traditional`
3. Import and use in components

## Troubleshooting

### Backend won't start

**Error**: `RuntimeError: ELOHIM_JWT_SECRET environment variable is required`

**Fix**: Set JWT secret:
```bash
export ELOHIM_JWT_SECRET=$(openssl rand -base64 32)
```

### Ollama not responding

**Error**: Models not appearing in chat dropdown

**Fix**: Start Ollama:
```bash
ollama serve
```

Check models:
```bash
ollama list
```

Pull missing models:
```bash
ollama pull qwen2.5-coder:14b
```

### Database locked error

**Error**: `sqlite3.OperationalError: database is locked`

**Fix**: Close other processes using the database:
```bash
lsof | grep elohimos_app.db
kill <PID>
```

### Port already in use

**Error**: `Address already in use: 8000`

**Fix**: Kill process on port:
```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:4200 | xargs kill -9
```

Or use the startup script which does this automatically:
```bash
./elohim
```

### Metal 4 not available

**Error**: `Metal 4 not available - using CPU`

**Check**: Verify macOS and chip:
```bash
sw_vers  # Should be macOS 12+
sysctl -n machdep.cpu.brand_string  # Should contain "Apple"
```

**Note**: Metal 4 requires Apple Silicon (M1/M2/M3). Falls back to CPU if unavailable.

## Next Steps

1. **Read System Architecture** - `docs/architecture/SYSTEM_ARCHITECTURE.md`
2. **Review Database Schema** - `docs/database/SCHEMA.md`
3. **Explore a subsystem** - Pick one and read its README
4. **Make your first contribution** - Start with a small bug fix or docs improvement

## Getting Help

- **Documentation**: `docs/` directory
- **Code Comments**: Inline documentation in source files
- **Git History**: See recent commits for context

## Tips for Success

1. **Start small** - Don't try to understand everything at once
2. **Follow the data** - Trace a feature from UI → API → database
3. **Use the debugger** - VSCode debugger for Python, Chrome DevTools for frontend
4. **Ask questions** - Better to ask than make incorrect assumptions
5. **Document as you learn** - Update docs when you figure something out

Welcome to the team!
