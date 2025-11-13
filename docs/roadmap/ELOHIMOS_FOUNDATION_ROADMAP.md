# ElohimOS Foundation Roadmap
**Systems Engineering Approach: Base Foundation → Full Platform**

> "The Lord is my rock, my fortress and my deliverer" - Psalm 18:2

**Date**: January 12, 2025
**Version**: 1.0
**Scope**: ElohimOS Base Foundation (Offline-First Core)
**Future Vision**: ElohimOS → MagnetarCloud Standard → MagnetarCloud Enterprise

---

## Executive Summary

ElohimOS is an **offline-first AI operating system** designed for field operations, missionaries, and distributed teams working in environments with unreliable or no network connectivity. This roadmap uses a **Systems Engineering** approach with clear **Separation of Concerns (SoC)** and **System of Systems (SoS)** architecture.

### Core Principles

1. **Offline-First, Always**: Every feature must work without network connectivity
2. **Local-by-Default**: User data is encrypted per-account using Secure Enclave
3. **No Hardcoded Defaults**: User-driven configuration via setup wizard
4. **Progressive Enhancement**: Local → P2P → Team → Cloud (MagnetarCloud)
5. **Zero Trust Foundation**: ElohimOS IS the engine; if it fails, everything fails

### Platform Evolution

```
ElohimOS (Foundation - This Roadmap)
    ↓
MagnetarCloud Standard (Small Teams, 2-20 people)
    ↓
MagnetarCloud Enterprise (Amazon/Government scale)
```

**Critical Success Factor**: ElohimOS must be bulletproof. No "Siri rewrite" disasters.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Permission Model](#permission-model)
3. [Resource Scoping](#resource-scoping)
4. [Implementation Roadmap](#implementation-roadmap)
   - [Phase 0: Foundation Infrastructure](#phase-0-foundation-infrastructure)
   - [Phase 1: First-Run Setup Wizard](#phase-1-first-run-setup-wizard)
   - [Phase 2: Local-Only Core Features](#phase-2-local-only-core-features)
   - [Phase 3: Team Collaboration Layer](#phase-3-team-collaboration-layer)
   - [Phase 4: Admin Panel & Management](#phase-4-admin-panel--management)
   - [Phase 5: ElohimOS SDK](#phase-5-elohimos-sdk)
   - [Phase 6: P2P Mesh Networking](#phase-6-p2p-mesh-networking)
   - [Phase 7: MagnetarCloud Integration](#phase-7-magnetarcloud-integration)
5. [Testing & Validation](#testing--validation)
6. [Success Metrics](#success-metrics)

---

## System Architecture

### System of Systems (SoS) Model

ElohimOS is composed of **7 independent systems** that work together:

```
┌─────────────────────────────────────────────────────────────┐
│                        ElohimOS Core                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   System 1   │  │   System 2   │  │   System 3   │     │
│  │ Auth & Users │  │ Data Storage │  │ AI Engine    │     │
│  │              │  │              │  │              │     │
│  │ • Local Auth │  │ • SQLite DBs │  │ • Ollama     │     │
│  │ • Encryption │  │ • DuckDB     │  │ • Metal 4    │     │
│  │ • Roles      │  │ • Secure     │  │ • MLX        │     │
│  │ • Sessions   │  │   Enclave    │  │ • Embeddings │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   System 4   │  │   System 5   │  │   System 6   │     │
│  │ Team Collab  │  │ Permissions  │  │   P2P Mesh   │     │
│  │              │  │              │  │              │     │
│  │ • Workspace  │  │ • RBAC       │  │ • Zeroconf   │     │
│  │ • Docs       │  │ • Profiles   │  │ • libp2p     │     │
│  │ • Vault      │  │ • Policies   │  │ • Device     │     │
│  │ • Workflows  │  │ • Audit Log  │  │   Sync       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐                                          │
│  │   System 7   │                                          │
│  │ ElohimOS SDK │                                          │
│  │              │                                          │
│  │ • Terminal   │                                          │
│  │ • Code Tab   │                                          │
│  │ • Offline    │                                          │
│  │   App Dev    │                                          │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

### Separation of Concerns (SoC)

Each system has **clear boundaries** and **single responsibility**:

| System | Responsibility | Dependencies | Data Store |
|--------|----------------|--------------|------------|
| **Auth & Users** | User accounts, login, encryption | Secure Enclave | `users.db` |
| **Data Storage** | Persistent data, encryption | None | SQLite, DuckDB |
| **AI Engine** | LLM inference, embeddings | Ollama, Metal 4 | JSON config (`model_hot_slots.json`) + runtime via Ollama |
| **Team Collab** | Shared workspace, team resources | Auth, Data Storage | `teams.db` |
| **Permissions** | RBAC, role management | Auth, Team Collab | `permissions.db` |
| **P2P Mesh** | Device-to-device sync | Auth, Data Storage | `p2p_sync.db` |
| **ElohimOS SDK** | Offline-first app development | All systems | User-defined |

### Data Flow Architecture

```
User Interaction (Frontend)
    ↓
Route Layer (FastAPI)
    ↓
Service Layer (Business Logic)
    ↓
Schema Layer (Validation)
    ↓
Data Layer (SQLite/DuckDB)
    ↓
Secure Enclave (Encryption)
```

**Key Principle**: Every layer is **stateless** and **testable independently**.

---

## Permission Model

### User Roles Hierarchy

```
Founder Rights (Override Everything)
    ↓
Super Admin (Local-only OR Team context)
    ↓
Admin (Team-only)
    ↓
Member (Team-only)
    ↓
Guest (Team-only, Read-only)
```

### Role Definitions

#### **1. Founder Rights**
- **Who**: You (founder) + co-founders
- **Scope**: EVERYTHING (local + all teams)
- **Access**: Admin Panel (always)
- **Powers**:
  - Delete user accounts (local)
  - Override any permission
  - View/edit any team's data
  - Deploy apps/workflows globally
  - Bypass all RBAC

**Use Case**: Field operations oversight, emergency management

**Implementation**:

Founder Rights is a role (`founder_rights`) enforced centrally by the permission engine. Founder bypass happens in the permission check path — not via a static user list.

**Conceptual Flow**:
- `permission_engine.has_permission`: if `user_ctx.role == 'founder_rights'` → allow
- **Development**: `ELOHIM_FOUNDER_PASSWORD` is required; default only in dev. Must be set in production.
- **No hardcoded founder lists**; identification is via auth + role

#### **2. Super Admin (Local-Only)**
- **Who**: Any user not in a team
- **Scope**: Local resources ONLY
- **Access**: Limited Admin Panel (view dashboard, manage users/settings; cannot manage permissions by default)
- **Powers**:
- Manage own/local data freely
- System-level (limited): view admin dashboard, manage users, manage settings
- Cannot manage permissions by default
- Cannot access team resources


**Note**: Current implementation grants several system permissions to `super_admin` baseline. This may be restricted further in future phases.

**Use Case**: Solo worker on shared laptop

**Implementation**:
**Implementation**:
- Founder Rights is a role (founder_rights) enforced centrally by the permission engine. Founder bypass happens in the permission check path — not via a static user list.
- Development: ELOHIM_FOUNDER_PASSWORD must be set in production (default only in dev).
- No hardcoded founder lists; identification is via auth + role.

```python
# permission_engine.py
if user_ctx.role == 'founder_rights':
    return True  # bypass
```

#### **3. Super Admin (Team Context)**
- **Who**: Team Super Admin assigned by team
- **Scope**: Team resources + Local resources
- **Access**: Admin Panel (team-scoped)
- **Powers**:
  - Manage team workspace
  - Add/remove team members
  - Change team roles
  - Deploy workflows/apps to team
  - Manage team permissions
  - Full control over local data
  - **CANNOT** delete other users' local accounts

**Use Case**: Team lead in field office

**Implementation**:
```python
team_member = {
    "user_id": "u_123",
    "team_id": "team_456",
    "role": "super_admin",  # Team role
    "permissions": {
        "team.admin_panel.access": True,
        "team.users.manage": True,
        "team.workflows.deploy": True
    }
}
```

#### **4. Admin (Team)**
- **Who**: Team admin
- **Scope**: Team resources + Local resources
- **Access**: Admin Panel (partial, team-scoped)
- **Powers**:
  - Manage team content
  - Assign permissions (if granted)
  - Full control over local data
  - **CANNOT** add/remove users
  - **CANNOT** deploy apps (unless granted)

#### **5. Member (Team)**
- **Who**: Regular team member
- **Scope**: Team resources (based on permissions) + Local resources
- **Access**: Limited Admin Panel (view dashboard, manage users/settings; cannot manage permissions by default)
- **Powers**:
  - Access team chat, docs, workflows (if permitted)
  - Execute workflows (if permitted)
  - Full control over local data
  - **CANNOT** manage team

**Use Case**: Developer building on ElohimOS SDK locally

**Example**:
```
Johnny (Member):
- Builds medical records app locally (super admin over local)
- Wants to deploy to team? → Needs permission: team.apps.deploy
- No permission? → Keeps building locally (no restrictions)
- Granted permission? → Deploys to team workspace
```

#### **6. Guest (Team)**
- **Who**: External collaborator
- **Scope**: Limited team resources + Local resources
- **Access**: NO Admin Panel
- **Powers**:
  - Read-only team docs (if permitted)
  - View team chat (if permitted)
  - Full control over local data
  - **CANNOT** edit team resources

---

## Resource Scoping

### Local-Only Resources (No Permissions Apply)

**Owner**: Individual user
**Encryption**: Per-user Secure Enclave key
**Access**: Super Admin (automatic)

**Resources**:
- Personal chat sessions
- Personal documents
- Personal vault items
- Personal workflows
- Personal spreadsheets
- Personal terminal/code projects
- ElohimOS SDK local development

**Implementation**:
```sql
-- All local resources have user_id, no team_id
SELECT * FROM chat_sessions WHERE user_id = ? AND team_id IS NULL;
SELECT * FROM documents WHERE user_id = ? AND team_id IS NULL;
SELECT * FROM vault_items WHERE user_id = ? AND team_id IS NULL;
```

**Key Principle**: User has 100% ownership. No permission checks. No sharing.

---

### Team-Scoped Resources (RBAC Applies)

**Owner**: Team (shared)
**Encryption**: Team vault key (shared secret)
**Access**: Based on role + permissions

**Resources**:
- Team workspace files
- Team documents & spreadsheets
- Team chat sessions
- Team vault (shared secrets)
- Team workflows (with queue system)
- Team deployed apps (ElohimOS SDK)

**Implementation**:
```sql
-- Team resources have team_id
SELECT * FROM chat_sessions WHERE team_id = ?;
SELECT * FROM documents WHERE team_id = ?;
SELECT * FROM workflows WHERE team_id = ?;
```

**Permission Examples**:
```json
{
  \"docs.read\": true,
  \"docs.write\": false,
  \"chat.use\": true,
  \"workflows.execute\": true,
  \"workflows.deploy\": false,
  \"vault.read\": true,
  \"vault.write\": false,
  \"apps.deploy\": false,
  \"system.view_admin_dashboard\": false
}
```

Team-awareness is applied at check time via require_perm_team(...), which loads permissions in the context of team_id. Keys are neutral (e.g., \"docs.read\").

**Team-Awareness**: Keys remain neutral (e.g., `docs.read`). Team scoping is applied at check time via `require_perm_team(permission_key, level, team_kw)` which loads permissions in the context of `team_id`. The permission resolver applies team context during evaluation.

---

### Context Switching (Solo ↔ Team)

**UI Component**: Header Toggle (top-right)

**States**:
```
[🔄 Local] → Local-only mode (super admin, no team resources)
[👥 Team: Engineering] → Team mode (RBAC active, team resources visible)
```

**Implementation**:
```typescript
interface UserContext {
  mode: 'local' | 'team'
  team_id: string | null
  role: 'founder_rights' | 'super_admin' | 'admin' | 'member' | 'guest'
  permissions: Record<string, boolean>
}

// Switch to local mode
const switchToLocal = () => {
  setContext({
    mode: 'local',
    team_id: null,
    role: 'super_admin',
    permissions: {} // No checks needed
  })
}

// Switch to team mode
const switchToTeam = (team_id: string) => {
  const teamRole = fetchTeamRole(user_id, team_id)
  const teamPermissions = fetchTeamPermissions(user_id, team_id)

  setContext({
    mode: 'team',
    team_id: team_id,
    role: teamRole,
    permissions: teamPermissions
  })
}
```

**Data Visibility**:
```
Local Mode:
- Show: Personal chat, personal docs, personal workflows
- Hide: Team resources

Team Mode (Engineering):
- Show: Personal resources + Engineering team resources
- Hide: Other teams' resources

Founder Rights:
- Show: EVERYTHING (all local + all teams)
```

Note: The permission engine already supports team context via require_perm_team(team_id). The Header toggle is planned UI work to set active team_id and pass it to endpoints.

---

## Implementation Roadmap

### Complexity Levels

- **L0**: Trivial (1-2 hours)
- **L1**: Low (3-6 hours)
- **L2**: Medium (1-2 days)
- **L3**: High (3-5 days)
- **L4**: Very High (1-2 weeks)

---

## Phase 0: Foundation Infrastructure

**Goal**: Fix current issues, establish baseline

**Duration**: 1-2 days
**Complexity**: L1-L2

### Tasks

#### 0.1: Fix Model Preloading Mystery (L1)
**Issue**: "No favorite models to preload" but model loads anyway

**Root Cause**:
- Hot slots are persisted in `model_hot_slots.json` (not a DB)
- Favorites (hot slots) are not the source of the startup load
- A default model is preloaded from the **frontend** after session creation (`App.tsx`), which can look like an "automatic preload"

**Solution**:
1. Add logging around model preloads (service + frontend) to ensure clarity
2. Make frontend default preload **user-controlled** (setting/toggle) or disable by default
3. Keep hot slots separate and user-driven

**Files**:
- `apps/frontend/src/App.tsx` (toggle/disable default preload)
- `apps/backend/api/model_manager.py` (logging around hot slot usage)

**Acceptance Criteria**:
- [ ] No preload occurs unless:
  - User explicitly assigns hot slots AND selects "Load hot slots", or
  - User enables the default preload in settings
- [ ] Logs clearly show source of preload ("Frontend preload" vs "Hot slot preload")

---

#### 0.2: Document Current Permission Model (L0)
**Goal**: Capture current RBAC implementation

**Deliverables**:
- `docs/architecture/PERMISSION_MODEL.md`
- Diagrams of current role hierarchy
- List of all permissions in use (using actual keys from `permission_engine.py`)

**Files**:
- `apps/backend/api/permission_engine.py` (analyze current implementation)

**Key Points to Document**:
- Permission keys use neutral naming (e.g., `docs.read`, `chat.use`)
- Team-awareness is applied via `require_perm_team(permission_key, level, team_id)` which loads user context with team scope
- Founder bypass is implemented in `has_permission` check (role == 'founder_rights')
- Current baselines for roles (super_admin/admin/member/guest) as implemented

---

#### 0.3: Create Recommended Models Config (L0)
**Goal**: No hardcoded models, user-driven selection

**Deliverables**:
- `apps/backend/api/config/recommended_models.json` **(new file, doesn't exist yet)**

**Schema**:
```json
{
  "version": "1.0",
  "updated": "2025-01-12",
  "categories": {
    "essential": {
      "description": "Minimal setup for 8GB RAM systems",
      "ram_required": "8GB",
      "total_size": "4.7GB",
      "models": [
        {
          "name": "qwen2.5-coder:7b-instruct",
          "size": "4.7GB",
          "use_cases": ["chat", "coding", "general"],
          "hot_slot_suggestion": 1
        }
      ]
    },
    "balanced": {
      "description": "Good performance for 16GB RAM systems",
      "ram_required": "16GB",
      "total_size": "10.6GB",
      "models": [
        {
          "name": "qwen2.5-coder:7b-instruct",
          "size": "4.7GB",
          "use_cases": ["chat", "coding"],
          "hot_slot_suggestion": 1
        },
        {
          "name": "deepseek-r1:8b",
          "size": "4.9GB",
          "use_cases": ["reasoning", "analysis"],
          "hot_slot_suggestion": 2
        },
        {
          "name": "qwen2.5-coder:1.5b",
          "size": "1.0GB",
          "use_cases": ["fast_edits", "autocomplete"],
          "hot_slot_suggestion": 3
        }
      ]
    },
    "power_user": {
      "description": "Full capabilities for 32GB+ RAM systems",
      "ram_required": "32GB",
      "total_size": "33.6GB",
      "models": [
        {
          "name": "qwen2.5-coder:32b-instruct",
          "size": "19GB",
          "use_cases": ["architecture", "complex_refactoring"],
          "hot_slot_suggestion": 1
        },
        {
          "name": "deepseek-r1:14b",
          "size": "8.9GB",
          "use_cases": ["deep_reasoning"],
          "hot_slot_suggestion": 2
        },
        {
          "name": "qwen2.5-coder:7b-instruct",
          "size": "4.7GB",
          "use_cases": ["balanced_tasks"],
          "hot_slot_suggestion": 3
        },
        {
          "name": "qwen2.5-coder:1.5b",
          "size": "1.0GB",
          "use_cases": ["fast_edits"],
          "hot_slot_suggestion": 4
        }
      ]
    }
  }
}
```

**Acceptance Criteria**:
- [ ] JSON file created and validated
- [ ] Contains at least 3 tiers (essential, balanced, power_user)
- [ ] Each model has size, use_cases, hot_slot_suggestion
- [ ] Referenced from setup wizard and model selection UIs

---

#### 0.4: Setup Tracking (Current vs Future) (L0)
**Goal**: Track if user completed first-run setup

**Current Implementation**:
- Uses `founder_setup` table with `setup_completed` flag
- Managed by `founder_setup_wizard.py`

**Future Option** (if needed):
- Migrate to per-user setup tracking in `users` table
- Add `setup_completed` and `current_context` columns

**Decision**: Keep current `founder_setup` table for now. Optionally migrate to per-user setup state later if needed.

**Files**:
- `apps/backend/api/founder_setup_wizard.py` (current)
- `apps/backend/api/startup_migrations.py` (future migration if needed)

**Acceptance Criteria**:
- [ ] Setup completion tracked (currently via `founder_setup` table)
- [ ] App checks flag on startup
- [ ] Wizard skipped if setup completed

---

### Phase 0 Deliverables

- [ ] Model preloading works predictably (frontend preload is user-controlled)
- [ ] `recommended_models.json` created
- [ ] Permission model documented
- [ ] `model_hot_slots.json` initialized on demand (first assignment)
- [ ] Logs identify preload sources explicitly (frontend vs hot slots)

**Estimated Time**: 1-2 days

---

## Phase 1: First-Run Setup Wizard

**Goal**: User-driven initial configuration (no hardcoded defaults)

**Duration**: 4-5 days
**Complexity**: L2-L3

**Note**: Current implementation has `founder_setup_wizard.py` with basic routes. This phase should consolidate and expand that into a full setup wizard experience.

### System Responsibilities

**System 1 (Auth & Users)**: Create local account
**System 3 (AI Engine)**: Detect Ollama, download models, configure hot slots
**System 2 (Data Storage)**: Initialize all databases

---

### 1.1: Backend - Setup Wizard Service (L2)

**File**: `apps/backend/api/services/setup_wizard.py` (consolidate with existing `founder_setup_wizard.py`)

**Class Design**:
```python
class SetupWizardService:
    """
    First-run setup wizard for new users

    Handles:
    - User account creation (local-only)
    - Ollama detection/installation guidance
    - Model downloads with recommendations
    - Hot slot configuration
    - Database initialization
    """

    async def is_first_run(self) -> bool:
        """Check if any users exist in system"""
        conn = sqlite3.connect(USERS_DB)
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return count == 0

    async def check_ollama_status(self) -> OllamaStatus:
        """
        Detect Ollama installation and service status

        Returns:
            OllamaStatus with:
            - installed: bool (binary exists)
            - running: bool (service responding)
            - version: str | None
            - base_url: str (http://localhost:11434)
        """

    async def load_model_recommendations(self) -> ModelRecommendations:
        """
        Load recommended_models.json

        Returns:
            ModelRecommendations with categories:
            - essential (8GB RAM)
            - balanced (16GB RAM)
            - power_user (32GB RAM)
        """

    async def detect_system_resources(self) -> SystemResources:
        """
        Detect system RAM and available disk space

        Returns:
            SystemResources with:
            - ram_gb: int (total system RAM)
            - disk_free_gb: int (available disk space)
            - recommended_tier: str (essential|balanced|power_user)
        """

    async def download_model(
        self,
        model_name: str,
        progress_callback: Callable[[float, str], None]
    ) -> bool:
        """
        Download single model via Ollama

        Args:
            model_name: Ollama model (e.g., "qwen2.5-coder:7b-instruct")
            progress_callback: Called with (progress_pct, status_msg)

        Returns:
            True if successful, False otherwise
        """

    async def configure_hot_slots(
        self,
        user_id: str,
        slots: Dict[int, str]
    ):
        """
        Initialize hot slots for user

        Args:
            user_id: User who owns these slots
            slots: {1: "model1", 2: "model2", ...}

        Persists to JSON (model_hot_slots.json)
        """

    async def create_local_account(
        self,
        username: str,
        password: str
    ) -> User:
        """
        Create super_admin account for local-only use

        Args:
            username: Unique username
            password: Plain text (will be hashed)

        Returns:
            User object with:
            - id: Generated user ID
            - username: As provided
            - role: "super_admin" (default for all non-founders)
            - current_context: "local"
            - setup_completed: 0 (will be set to 1 after wizard)
        """

    async def complete_setup(self, user_id: str):
        """
        Mark setup as completed

        Sets setup_completed = 1
        """
```

**Routes**: `apps/backend/api/routes/setup.py`

```python
router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

@router.get("/first-run")
async def check_first_run():
    """Check if this is first run (no users exist)"""

@router.get("/ollama/status")
async def get_ollama_status():
    """Detect Ollama installation and service status"""

@router.get("/system/resources")
async def get_system_resources():
    """Detect RAM and disk space"""

@router.get("/models/recommendations")
async def get_model_recommendations():
    """Load recommended_models.json"""

@router.post("/models/download")
async def download_model(model_name: str):
    """Download single model with progress updates (SSE)"""

@router.post("/account/create")
async def create_account(username: str, password: str):
    """Create local super_admin account"""

@router.post("/hot-slots/configure")
async def configure_hot_slots(slots: Dict[int, str]):
    """Set hot slots 1-4"""

@router.post("/complete")
async def complete_setup(user_id: str):
    """Mark setup as completed"""
```

**Acceptance Criteria**:
- [ ] All endpoints functional
- [ ] Ollama detection works (installed + running)
- [ ] System resource detection accurate
- [ ] Model download with real-time progress
- [ ] Hot slots saved to DB
- [ ] Account creation with proper encryption

---

### 1.2: Frontend - Setup Wizard UI (L3)

**Directory**: `apps/frontend/src/components/SetupWizard/`

**Structure**:
```
SetupWizard/
├── SetupWizard.tsx           # Main wizard container (stepper)
├── steps/
│   ├── WelcomeStep.tsx       # Step 0: Welcome screen
│   ├── AccountStep.tsx       # Step 1: Username/password creation
│   ├── OllamaStep.tsx        # Step 2: Ollama detection/install
│   ├── ModelsStep.tsx        # Step 3: Model tier selection
│   ├── DownloadStep.tsx      # Step 4: Model downloads (progress bars)
│   ├── HotSlotsStep.tsx      # Step 5: Quick slot assignment
│   └── CompletionStep.tsx    # Step 6: Setup complete
├── components/
│   ├── ModelCard.tsx         # Individual model info card
│   ├── DownloadProgress.tsx  # Progress bar for downloads
│   ├── SystemRequirements.tsx# RAM/disk usage display
│   └── StepIndicator.tsx     # Visual stepper (1/6, 2/6, etc.)
└── hooks/
    ├── useSetupWizard.ts     # Wizard state management
    └── useModelDownload.ts   # Download progress (SSE)
```

**Step Flow**:

#### Step 0: Welcome
```tsx
<WelcomeStep>
  <h1>Welcome to ElohimOS</h1>
  <p>Offline-First AI Operating System</p>
  <Quote>"The Lord is my rock and fortress" - Psalm 18:2</Quote>
  <Button onClick={handleNext}>Get Started</Button>
</WelcomeStep>
```

#### Step 1: Account Creation
```tsx
<AccountStep>
  <Form onSubmit={handleCreateAccount}>
    <Input
      label="Username"
      value={username}
      onChange={setUsername}
      validation={validateUsername}
    />
    <Input
      label="Password"
      type="password"
      value={password}
      onChange={setPassword}
      validation={validatePassword}
    />
    <Input
      label="Confirm Password"
      type="password"
      value={confirmPassword}
      onChange={setConfirmPassword}
    />
    <InfoBox>
      Your account is stored locally and never leaves your device.
    </InfoBox>
    <Button type="submit">Continue</Button>
  </Form>
</AccountStep>
```

**Validation**:
- Username: 3-20 chars, alphanumeric + underscore
- Password: Min 8 chars, at least 1 uppercase, 1 number
- Confirm matches password

#### Step 2: Ollama Detection
```tsx
<OllamaStep>
  {ollamaStatus.running ? (
    <SuccessCard>
      <CheckCircle /> Ollama Detected!
      <p>Running at {ollamaStatus.base_url}</p>
      <p>Version: {ollamaStatus.version}</p>
      <Button onClick={handleNext}>Continue</Button>
    </SuccessCard>
  ) : (
    <WarningCard>
      <AlertTriangle /> Ollama Not Detected
      <p>ElohimOS requires Ollama to run local AI models.</p>
      <InstallInstructions>
        <h4>Install via:</h4>
        <Code>brew install ollama</Code>
        <p>Or download from: https://ollama.com/download</p>
      </InstallInstructions>
      <Button onClick={handleRecheck}>Re-check</Button>
      <Button variant="secondary" onClick={openInstallGuide}>
        Install Instructions
      </Button>
    </WarningCard>
  )}
</OllamaStep>
```

#### Step 3: Model Tier Selection
```tsx
<ModelsStep>
  <SystemRequirements ram={systemResources.ram_gb} />
  <p>Recommended: {systemResources.recommended_tier}</p>

  <TierSelector>
    <TierCard
      tier="essential"
      selected={selectedTier === 'essential'}
      onClick={() => setSelectedTier('essential')}
    >
      <h3>Essential (4.7GB)</h3>
      <p>Best for: 8GB RAM systems</p>
      <ModelList>
        <li>qwen2.5-coder:7b-instruct</li>
      </ModelList>
    </TierCard>

    <TierCard
      tier="balanced"
      selected={selectedTier === 'balanced'}
      onClick={() => setSelectedTier('balanced')}
    >
      <h3>Balanced (10.6GB)</h3>
      <p>Best for: 16GB RAM systems</p>
      <ModelList>
        <li>qwen2.5-coder:7b-instruct</li>
        <li>deepseek-r1:8b</li>
        <li>qwen2.5-coder:1.5b</li>
      </ModelList>
    </TierCard>

    <TierCard
      tier="power_user"
      selected={selectedTier === 'power_user'}
      recommended={systemResources.recommended_tier === 'power_user'}
      onClick={() => setSelectedTier('power_user')}
    >
      <h3>Power User (33.6GB) ⭐</h3>
      <p>Best for: 32GB+ RAM systems</p>
      <ModelList>
        <li>qwen2.5-coder:32b-instruct</li>
        <li>deepseek-r1:14b</li>
        <li>qwen2.5-coder:7b-instruct</li>
        <li>qwen2.5-coder:1.5b</li>
      </ModelList>
    </TierCard>
  </TierSelector>

  <Button onClick={handleStartDownload}>Download Models</Button>
</ModelsStep>
```

#### Step 4: Model Downloads
```tsx
<DownloadStep>
  <h3>Downloading Models ({currentIndex + 1} of {totalModels})</h3>

  {models.map((model, idx) => (
    <DownloadProgress
      key={model.name}
      modelName={model.name}
      size={model.size}
      status={downloadStatuses[idx]} // 'pending' | 'downloading' | 'complete'
      progress={downloadProgress[idx]}
      speed={downloadSpeeds[idx]}
    />
  ))}

  {allComplete && (
    <Button onClick={handleNext}>Continue to Hot Slots</Button>
  )}
</DownloadStep>
```

**Download Progress Component**:
```tsx
<DownloadProgress>
  <ModelInfo>
    <ModelName>{modelName}</ModelName>
    <ModelSize>{size}</ModelSize>
  </ModelInfo>

  {status === 'complete' && <CheckCircle color="green" />}
  {status === 'downloading' && (
    <ProgressBar>
      <Bar width={`${progress}%`} />
      <Stats>
        {formatBytes(downloaded)} / {formatBytes(total)} ({speed})
      </Stats>
    </ProgressBar>
  )}
  {status === 'pending' && <Pause />}
</DownloadProgress>
```

#### Step 5: Hot Slots Assignment
```tsx
<HotSlotsStep>
  <h3>Assign Models to Quick Slots (1-4)</h3>
  <p>Quick slots let you switch models instantly</p>

  <SlotAssignment>
    <SlotSelector slot={1}>
      Slot 1:
      <Dropdown
        options={downloadedModels}
        value={slots[1]}
        onChange={(model) => setSlot(1, model)}
      />
    </SlotSelector>

    <SlotSelector slot={2}>
      Slot 2:
      <Dropdown
        options={downloadedModels}
        value={slots[2]}
        onChange={(model) => setSlot(2, model)}
      />
    </SlotSelector>

    <SlotSelector slot={3}>
      Slot 3:
      <Dropdown
        options={downloadedModels}
        value={slots[3]}
        onChange={(model) => setSlot(3, model)}
      />
    </SlotSelector>

    <SlotSelector slot={4}>
      Slot 4:
      <Dropdown
        options={[...downloadedModels, { name: 'Empty', value: null }]}
        value={slots[4]}
        onChange={(model) => setSlot(4, model)}
      />
    </SlotSelector>
  </SlotAssignment>

  <InfoBox>You can change these anytime in Settings</InfoBox>
  <Button onClick={handleComplete}>Complete Setup</Button>
</HotSlotsStep>
```

#### Step 6: Completion
```tsx
<CompletionStep>
  <SuccessIcon>🎉</SuccessIcon>
  <h2>ElohimOS is Ready!</h2>

  <ChecklistSummary>
    <CheckItem>✅ Account created</CheckItem>
    <CheckItem>✅ Ollama connected</CheckItem>
    <CheckItem>✅ {downloadedModels.length} models downloaded</CheckItem>
    <CheckItem>✅ Quick slots configured</CheckItem>
  </ChecklistSummary>

  <InfoBox>
    You're in Local Mode (super admin). Create or join teams anytime from the team toggle in the header.
  </InfoBox>

  <Button onClick={handleStart}>Start Using ElohimOS</Button>
</CompletionStep>
```

**State Management**: `hooks/useSetupWizard.ts`

```typescript
interface SetupWizardState {
  currentStep: number
  username: string
  password: string
  ollamaStatus: OllamaStatus
  systemResources: SystemResources
  selectedTier: 'essential' | 'balanced' | 'power_user'
  downloadedModels: Model[]
  downloadProgress: Record<string, number>
  hotSlots: Record<number, string | null>
  completed: boolean
}

const useSetupWizard = () => {
  const [state, setState] = useState<SetupWizardState>({
    currentStep: 0,
    username: '',
    password: '',
    ollamaStatus: null,
    systemResources: null,
    selectedTier: 'balanced',
    downloadedModels: [],
    downloadProgress: {},
    hotSlots: { 1: null, 2: null, 3: null, 4: null },
    completed: false
  })

  const nextStep = () => setState({ ...state, currentStep: state.currentStep + 1 })
  const prevStep = () => setState({ ...state, currentStep: state.currentStep - 1 })

  const createAccount = async (username: string, password: string) => {
    const response = await fetch('/api/v1/setup/account/create', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    })
    const user = await response.json()
    setState({ ...state, username, userId: user.id })
    nextStep()
  }

  const checkOllama = async () => {
    const response = await fetch('/api/v1/setup/ollama/status')
    const status = await response.json()
    setState({ ...state, ollamaStatus: status })
  }

  const downloadModels = async (models: string[]) => {
    for (const model of models) {
      await downloadModel(model, (progress) => {
        setState(prev => ({
          ...prev,
          downloadProgress: { ...prev.downloadProgress, [model]: progress }
        }))
      })
    }
    nextStep()
  }

  const configureHotSlots = async (slots: Record<number, string>) => {
    await fetch('/api/v1/setup/hot-slots/configure', {
      method: 'POST',
      body: JSON.stringify({ slots })
    })
    setState({ ...state, hotSlots: slots })
  }

  const completeSetup = async () => {
    await fetch('/api/v1/setup/complete', {
      method: 'POST',
      body: JSON.stringify({ user_id: state.userId })
    })
    setState({ ...state, completed: true })
  }

  return {
    state,
    nextStep,
    prevStep,
    createAccount,
    checkOllama,
    downloadModels,
    configureHotSlots,
    completeSetup
  }
}
```

**Acceptance Criteria**:
- [ ] All 7 steps render correctly
- [ ] Navigation (Next/Back) works
- [ ] Account creation validates input
- [ ] Ollama detection shows correct status
- [ ] Model tier selection persists
- [ ] Download progress updates in real-time
- [ ] Hot slots save successfully
- [ ] Redirects to main app on completion

---

### 1.3: App Startup Flow (L1)

**File**: `apps/frontend/src/App.tsx`

**Logic**:
```typescript
function App() {
  const [isFirstRun, setIsFirstRun] = useState<boolean | null>(null)
  const [setupComplete, setSetupComplete] = useState(false)

  useEffect(() => {
    checkFirstRun()
  }, [])

  const checkFirstRun = async () => {
    const response = await fetch('/api/v1/setup/first-run')
    const { first_run } = await response.json()
    setIsFirstRun(first_run)
  }

  if (isFirstRun === null) {
    return <LoadingScreen />
  }

  if (isFirstRun && !setupComplete) {
    return <SetupWizard onComplete={() => setSetupComplete(true)} />
  }

  return <MainApp />
}
```

**Acceptance Criteria**:
- [ ] First-run detection works
- [ ] Setup wizard shows for new installations
- [ ] Main app loads after setup completes
- [ ] No wizard for existing users

---

### Phase 1 Deliverables

- [ ] Setup wizard backend service complete
- [ ] Setup wizard UI with all 7 steps
- [ ] Model downloads functional with progress
- [ ] Hot slots initialized correctly
- [ ] Users table has setup_completed flag
- [ ] App startup checks first-run status

**Estimated Time**: 4-5 days

---

## Phase 2: Local-Only Core Features

**Goal**: Bulletproof offline-first experience (no network required)

**Duration**: 1 week
**Complexity**: L2-L3

### System Focus

**System 1 (Auth & Users)**: Local authentication, session management
**System 2 (Data Storage)**: SQLite optimization, Secure Enclave encryption
**System 3 (AI Engine)**: Ollama integration, Metal 4 acceleration

---

### 2.1: Local Authentication Hardening (L2)

**File**: `apps/backend/api/auth_middleware.py`

**Features**:
- Secure password hashing (argon2)
- Session tokens (JWT with short expiry)
- Secure Enclave integration for user data encryption
- Multi-user support on shared laptop

**Implementation**:
```python
class AuthService:
    def hash_password(self, password: str) -> str:
        """Hash password using argon2"""

    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash"""

    def create_session(self, user_id: str) -> str:
        """Create JWT session token (1 day expiry)"""

    def verify_session(self, token: str) -> dict:
        """Verify JWT and return user payload"""

    def get_user_encryption_key(self, user_id: str) -> bytes:
        """Get per-user encryption key from Secure Enclave"""
```

**Acceptance Criteria**:
- [ ] Password hashing uses argon2
- [ ] Session tokens expire after 24 hours
- [ ] Multiple users can login on same device
- [ ] User data encrypted per-user

---

### 2.2: Secure Enclave Integration (L3)

**File**: `apps/backend/api/secure_enclave.py`

**Goal**: Per-user encryption for local data

**Implementation**:
```python
class SecureEnclaveService:
    """
    Manages per-user encryption keys using macOS Secure Enclave

    Each user gets unique encryption key stored in keychain
    Keys never leave Secure Enclave
    """

    def create_user_key(self, user_id: str) -> bool:
        """Create encryption key for user in Secure Enclave"""

    def get_user_key(self, user_id: str) -> bytes:
        """Retrieve user's encryption key"""

    def encrypt_data(self, user_id: str, data: bytes) -> bytes:
        """Encrypt data using user's key"""

    def decrypt_data(self, user_id: str, encrypted: bytes) -> bytes:
        """Decrypt data using user's key"""

    def delete_user_key(self, user_id: str):
        """Delete user's encryption key (when user is deleted)"""
```

**Use Cases**:
- Alice's chat sessions encrypted with Alice's key
- Bob can't read Alice's data (even as local super admin)
- Founder can delete Alice's account → key is destroyed → data unrecoverable

**Acceptance Criteria**:
- [ ] Each user has unique encryption key
- [ ] Keys stored in macOS keychain
- [ ] Data encrypted at rest
- [ ] User data isolated

---

### 2.3: Chat Tab Offline Mode (L2)

**Goal**: Chat works 100% offline with Ollama

**Features**:
- Local chat sessions
- Model switching (hot slots)
- Message history persistence
- No network required

**Files**:
- `apps/backend/api/services/chat.py` (ensure no network calls)
- `apps/frontend/src/components/ChatInterface.tsx`

**Acceptance Criteria**:
- [ ] Chat works with Ollama offline
- [ ] Hot slot switching functional
- [ ] Message history persists to SQLite
- [ ] No errors when network unavailable

---

### 2.4: Vault Tab Offline Mode (L2)

**Goal**: Zero-knowledge vault works locally

**Features**:
- AES-256-GCM encryption
- Client-side encryption/decryption
- No cloud dependencies

**Files**:
- `apps/backend/api/vault_service.py`
- `apps/frontend/src/components/VaultInterface.tsx`

**Acceptance Criteria**:
- [ ] Vault items encrypted before storage
- [ ] Decryption happens client-side
- [ ] Works without network
- [ ] Password strength validation

---

### 2.5: Docs Tab Offline Mode (L2)

**Goal**: Document management fully local

**Features**:
- Create/edit/delete docs
- Rich text editing
- Local search
- No cloud sync

**Files**:
- `apps/backend/api/docs_service.py`
- `apps/frontend/src/components/DocsInterface.tsx`

**Acceptance Criteria**:
- [ ] CRUD operations work offline
- [ ] Documents persist to SQLite
- [ ] Search works locally
- [ ] No network calls

---

### 2.6: Workflows Tab Offline Mode (L2)

**Goal**: Workflow builder and executor work offline

**Features**:
- Create workflows
- Execute locally
- No dependencies on external services

**Files**:
- `apps/backend/api/services/workflows.py`
- `apps/frontend/src/components/WorkflowInterface.tsx`

**Acceptance Criteria**:
- [ ] Workflow builder functional
- [ ] Execution works locally
- [ ] Results persist
- [ ] No network required

---

### 2.7: Spreadsheets Tab Offline Mode (L2)

**Goal**: Spreadsheet functionality fully offline

**Features**:
- Create/edit spreadsheets
- Formulas work locally
- DuckDB for analytics

**Files**:
- `apps/backend/api/services/spreadsheets.py`
- `apps/frontend/src/components/SpreadsheetInterface.tsx`

**Acceptance Criteria**:
- [ ] Spreadsheet CRUD works
- [ ] Formulas calculate locally
- [ ] DuckDB analytics functional
- [ ] No cloud dependencies

---

### 2.8: Terminal/Code Tab Offline Mode (L2)

**Goal**: Local terminal and code editing

**Features**:
- Terminal access
- Code editor
- File browsing
- Git integration

**Files**:
- `apps/backend/api/terminal_api.py`
- `apps/frontend/src/components/TerminalInterface.tsx`

**Acceptance Criteria**:
- [ ] Terminal spawns locally
- [ ] Code editor works offline
- [ ] File operations local
- [ ] Git works offline

---

### Phase 2 Deliverables

- [ ] All 7 tabs work 100% offline
- [ ] Secure Enclave encryption active
- [ ] Multi-user support on shared device
- [ ] No network calls in local mode
- [ ] Data encrypted at rest per-user

**Estimated Time**: 1 week

---

## Phase 3: Team Collaboration Layer

**Goal**: Add team workspace with RBAC (opt-in, layered on top of local)

**Duration**: 2 weeks
**Complexity**: L3-L4

### System Focus

**System 4 (Team Collab)**: Team resources, shared workspace
**System 5 (Permissions)**: RBAC enforcement, role management

---

### 3.1: Team Creation & Management (L3)

**File**: `apps/backend/api/services/teams.py`

**Features**:
- Create team
- Invite members (via code)
- Assign roles
- Team settings

**Implementation**:
```python
class TeamService:
    async def create_team(
        self,
        name: str,
        creator_id: str
    ) -> Team:
        """
        Create new team

        Args:
            name: Team name
            creator_id: User creating team (becomes super_admin)

        Returns:
            Team with generated invite code
        """

    async def generate_invite_code(self, team_id: str) -> str:
        """Generate 6-character invite code (expires in 7 days)"""

    async def join_team(self, user_id: str, invite_code: str) -> bool:
        """Join team via invite code (default role: member)"""

    async def add_member(
        self,
        team_id: str,
        user_id: str,
        role: str
    ):
        """Add member to team with role"""

    async def remove_member(self, team_id: str, user_id: str):
        """Remove member from team (not delete local account)"""

    async def change_role(
        self,
        team_id: str,
        user_id: str,
        new_role: str
    ):
        """Change member's team role"""

    async def get_team_members(self, team_id: str) -> List[TeamMember]:
        """Get all members of team with roles"""
```

**Database**:
```sql
CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT,
    invite_code TEXT UNIQUE,
    invite_expires_at TEXT,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE team_members (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('super_admin', 'admin', 'member', 'guest')),
    joined_at TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(team_id, user_id)
);
```

**Acceptance Criteria**:
- [ ] Team creation works
- [ ] Invite codes generated (6 chars, 7-day expiry)
- [ ] Users can join via code
- [ ] Roles assigned correctly
- [ ] Members can be removed

---

### 3.2: Solo/Team Toggle UI (L2)

**File**: `apps/frontend/src/components/Header.tsx`

**Note**: This UI is not yet implemented. Current implementation uses implicit context (local-only by default, team context when team_id is present in requests).

**UI**:
```tsx
const TeamToggle = () => {
  const [currentContext, setCurrentContext] = useState<Context>({
    mode: 'local',
    team_id: null
  })
  const [teams, setTeams] = useState<Team[]>([])

  useEffect(() => {
    fetchUserTeams()
  }, [])

  const switchContext = async (context: 'local' | string) => {
    if (context === 'local') {
      setCurrentContext({ mode: 'local', team_id: null })
      // Show local resources only
    } else {
      setCurrentContext({ mode: 'team', team_id: context })
      // Show team resources for this team
    }
  }

  return (
    <Dropdown>
      <DropdownTrigger>
        {currentContext.mode === 'local' ? (
          <Button>🔄 Local</Button>
        ) : (
          <Button>👥 {getTeamName(currentContext.team_id)}</Button>
        )}
      </DropdownTrigger>

      <DropdownMenu>
        <DropdownItem
          icon={currentContext.mode === 'local' ? <Check /> : null}
          onClick={() => switchContext('local')}
        >
          🔄 Local (Super Admin)
        </DropdownItem>

        <DropdownSeparator />

        {teams.map(team => (
          <DropdownItem
            key={team.id}
            icon={currentContext.team_id === team.id ? <Check /> : null}
            onClick={() => switchContext(team.id)}
          >
            👥 {team.name}
            <Badge>{team.role}</Badge>
          </DropdownItem>
        ))}

        <DropdownSeparator />

        <DropdownItem onClick={openCreateTeamModal}>
          + Create Team
        </DropdownItem>

        <DropdownItem onClick={openJoinTeamModal}>
          🔗 Join Team
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  )
}
```

**Context Propagation**:
```typescript
// Global context provider
const UserContextProvider = ({ children }) => {
  const [context, setContext] = useState<UserContext>({
    mode: 'local',
    team_id: null,
    role: 'super_admin',
    permissions: {}
  })

  const switchToLocal = () => {
    setContext({
      mode: 'local',
      team_id: null,
      role: 'super_admin',
      permissions: {} // No checks
    })
  }

  const switchToTeam = async (team_id: string) => {
    const teamRole = await fetchTeamRole(user.id, team_id)
    const teamPermissions = await fetchTeamPermissions(user.id, team_id)

    setContext({
      mode: 'team',
      team_id: team_id,
      role: teamRole,
      permissions: teamPermissions
    })
  }

  return (
    <UserContext.Provider value={{ context, switchToLocal, switchToTeam }}>
      {children}
    </UserContext.Provider>
  )
}
```

**Acceptance Criteria**:
- [ ] Toggle visible in header
- [ ] Shows "Local" by default
- [ ] Lists all joined teams
- [ ] Context switches work
- [ ] Resources filter by context

---

### 3.3: Team-Scoped Resources (L3)

**Goal**: Separate local vs team resources

**Implementation Pattern**:
```sql
-- Local chat sessions
SELECT * FROM chat_sessions WHERE user_id = ? AND team_id IS NULL;

-- Team chat sessions
SELECT * FROM chat_sessions WHERE team_id = ?;
```

**Files to Update**:
- `apps/backend/api/services/chat.py` (add team_id parameter)
- `apps/backend/api/services/docs.py` (add team_id parameter)
- `apps/backend/api/services/vault.py` (add team_id parameter)
- `apps/backend/api/services/workflows.py` (add team_id parameter)
- `apps/backend/api/services/spreadsheets.py` (add team_id parameter)

**Database Migrations**:
```sql
-- Add team_id to all resource tables
ALTER TABLE chat_sessions ADD COLUMN team_id TEXT REFERENCES teams(id);
ALTER TABLE documents ADD COLUMN team_id TEXT REFERENCES teams(id);
ALTER TABLE vault_items ADD COLUMN team_id TEXT REFERENCES teams(id);
ALTER TABLE workflows ADD COLUMN team_id TEXT REFERENCES teams(id);
ALTER TABLE spreadsheets ADD COLUMN team_id TEXT REFERENCES teams(id);

-- Create indexes
CREATE INDEX idx_chat_sessions_team ON chat_sessions(team_id);
CREATE INDEX idx_documents_team ON documents(team_id);
CREATE INDEX idx_vault_items_team ON vault_items(team_id);
CREATE INDEX idx_workflows_team ON workflows(team_id);
CREATE INDEX idx_spreadsheets_team ON spreadsheets(team_id);
```

**Acceptance Criteria**:
- [ ] All resource tables have team_id
- [ ] Queries filter by context (local or team)
- [ ] Local resources always accessible
- [ ] Team resources require team membership

---

### 3.4: RBAC Permission Enforcement (L3)

**File**: `apps/backend/api/permission_engine.py`

**Current Implementation** (already exists, needs updates):
- Permission profiles
- Permission sets
- Role-based access

**New Features**:
- Team-scoped permissions
- Founder rights bypass
- Admin panel access control

**Permission Examples**:
```json
{
  \"docs.read\": true,
  \"docs.write\": false,
  \"chat.use\": true,
  \"workflows.execute\": true,
  \"workflows.deploy\": false,
  \"vault.read\": true,
  \"vault.write\": false,
  \"apps.deploy\": false,
  \"system.view_admin_dashboard\": false
}
```

Team-awareness is applied at check time via require_perm_team(...), which loads permissions in the context of team_id. Keys are neutral (e.g., \"docs.read\").

**Decorator Usage**:
```python
@router.post("/teams/{team_id}/documents")
@require_perm_team("team.docs.write")
async def create_team_document(
    team_id: str,
    doc: DocumentCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create document in team workspace"""
```

**Founder Override**:
```python
def require_perm_team(permission: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs['current_user']

            # Founder rights bypass
            if is_founder(user['user_id']):
                return await func(*args, **kwargs)

            # Check team permission
            team_id = kwargs.get('team_id')
            if not has_team_permission(user['user_id'], team_id, permission):
                raise HTTPException(403, f"Missing permission: {permission}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Acceptance Criteria**:
- [ ] Permissions enforced for team resources
- [ ] Local resources bypass permission checks
- [ ] Founder rights override all permissions
- [ ] Admin panel access restricted

---

### 3.5: Team Vault (Shared Secrets) (L2)

**Goal**: Team members share encrypted secrets

**Implementation**:
- Team vault encrypted with team key
- Team key stored in each member's keychain
- Key rotation on member removal

**File**: `apps/backend/api/services/team_vault.py`

```python
class TeamVaultService:
    async def create_team_vault_item(
        self,
        team_id: str,
        user_id: str,
        item: VaultItem
    ):
        """Create vault item encrypted with team key"""

    async def get_team_vault_items(
        self,
        team_id: str,
        user_id: str
    ):
        """Get all vault items for team (decrypted)"""

    async def rotate_team_key(self, team_id: str):
        """Rotate team vault key (when member removed)"""
```

**Acceptance Criteria**:
- [ ] Team vault items encrypted with team key
- [ ] Team members can read/write (if permitted)
- [ ] Key rotation works
- [ ] Removed members can't access

---

### 3.6: Team Workflows with Queue (L3)

**Goal**: Team workflows with shared execution queue

**Features**:
- Team workflow library
- Shared execution queue
- Permission to deploy workflows

**File**: `apps/backend/api/services/team_workflows.py`

```python
class TeamWorkflowService:
    async def deploy_workflow(
        self,
        team_id: str,
        user_id: str,
        workflow: Workflow
    ):
        """Deploy workflow to team (requires team.workflows.deploy)"""

    async def execute_team_workflow(
        self,
        team_id: str,
        workflow_id: str,
        user_id: str
    ):
        """Execute workflow (adds to team queue)"""

    async def get_team_queue(self, team_id: str):
        """Get workflow execution queue for team"""
```

**Database**:
```sql
CREATE TABLE team_workflow_queue (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (workflow_id) REFERENCES workflows(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Acceptance Criteria**:
- [ ] Workflows deploy to team
- [ ] Queue system functional
- [ ] Permissions enforced (deploy, execute)
- [ ] Queue visible to team members

---

### Phase 3 Deliverables

- [ ] Team creation and invite system
- [ ] Solo/Team toggle in header
- [ ] Team-scoped resources (chat, docs, vault, workflows, spreadsheets)
- [ ] RBAC enforced for team resources
- [ ] Team vault with shared encryption
- [ ] Team workflow queue system

**Estimated Time**: 2 weeks

---

## Phase 4: Admin Panel & Management

**Goal**: Admin interface for Founders and Team Super Admins

**Duration**: 1 week
**Complexity**: L3

---

### 4.1: Admin Panel Access Control (L2)

**Who Can Access**:
- ✅ Founder Rights (always, even if local-only)
- ✅ Team Super Admin (when team active)
- ✅ Team Admin (partial access, when team active)
- ❌ Local-Only Super Admin (never)
- ❌ Team Member/Guest (never)

**UI Location**: Settings → Admin Panel (only visible if permitted)

**File**: `apps/frontend/src/components/AdminPanel/AdminPanel.tsx`

```tsx
const AdminPanel = () => {
  const { user, context } = useUserContext()
  const [activeTab, setActiveTab] = useState('users')

  // Check access
  if (!canAccessAdminPanel(user, context)) {
    return <AccessDenied />
  }

  const isFounder = user.role === 'founder_rights'
  const isTeamSuperAdmin = context.mode === 'team' && context.role === 'super_admin'

  return (
    <AdminPanelLayout>
      <Sidebar>
        {isFounder && (
          <>
            <NavItem active={activeTab === 'users'} onClick={() => setActiveTab('users')}>
              All Users
            </NavItem>
            <NavItem active={activeTab === 'teams'} onClick={() => setActiveTab('teams')}>
              All Teams
            </NavItem>
            <NavItem active={activeTab === 'system'} onClick={() => setActiveTab('system')}>
              System Settings
            </NavItem>
          </>
        )}

        {(isFounder || isTeamSuperAdmin) && (
          <>
            <NavItem active={activeTab === 'team_users'} onClick={() => setActiveTab('team_users')}>
              Team Users
            </NavItem>
            <NavItem active={activeTab === 'team_workspace'} onClick={() => setActiveTab('team_workspace')}>
              Team Workspace
            </NavItem>
            <NavItem active={activeTab === 'team_deployments'} onClick={() => setActiveTab('team_deployments')}>
              Team Deployments
            </NavItem>
          </>
        )}
      </Sidebar>

      <Content>
        {activeTab === 'users' && isFounder && <AllUsersPanel />}
        {activeTab === 'teams' && isFounder && <AllTeamsPanel />}
        {activeTab === 'system' && isFounder && <SystemSettingsPanel />}
        {activeTab === 'team_users' && <TeamUsersPanel teamId={context.team_id} />}
        {activeTab === 'team_workspace' && <TeamWorkspacePanel teamId={context.team_id} />}
        {activeTab === 'team_deployments' && <TeamDeploymentsPanel teamId={context.team_id} />}
      </Content>
    </AdminPanelLayout>
  )
}
```

**Acceptance Criteria**:
- [ ] Admin panel only visible to permitted users
- [ ] Founders see all sections
- [ ] Team super admins see team sections only
- [ ] Access denied for others

---

### 4.2: User Management (Founder Only) (L2)

**Component**: `AllUsersPanel.tsx`

**Features**:
- View all users on device
- Delete user accounts (local)
- View user's team memberships

**UI**:
```tsx
<AllUsersPanel>
  <Table>
    <thead>
      <tr>
        <th>Username</th>
        <th>Role</th>
        <th>Created</th>
        <th>Teams</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {users.map(user => (
        <tr key={user.id}>
          <td>{user.username}</td>
          <td><Badge>{user.role}</Badge></td>
          <td>{formatDate(user.created_at)}</td>
          <td>{user.teams.length} teams</td>
          <td>
            <Button onClick={() => viewUser(user)}>View</Button>
            <Button
              variant="danger"
              onClick={() => deleteUser(user)}
              confirm="This will permanently delete the user's local account and all their data. Continue?"
            >
              Delete
            </Button>
          </td>
        </tr>
      ))}
    </tbody>
  </Table>
</AllUsersPanel>
```

**Backend**:
```python
@router.delete("/admin/users/{user_id}")
@require_founder_rights
async def delete_user_account(
    user_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete user's local account (Founder only)

    - Deletes user record
    - Deletes Secure Enclave key
    - Removes from all teams
    - Deletes all user's local resources
    """
```

**Acceptance Criteria**:
- [ ] All users visible
- [ ] User deletion works
- [ ] Secure Enclave key destroyed
- [ ] User removed from teams

---

### 4.3: Team Management (L2)

**Component**: `TeamUsersPanel.tsx`

**Features** (Team Super Admin):
- View team members
- Add members (via invite)
- Remove members from team
- Change member roles

**UI**:
```tsx
<TeamUsersPanel teamId={teamId}>
  <Header>
    <h2>Team Members</h2>
    <Button onClick={generateInviteCode}>Generate Invite Code</Button>
  </Header>

  {inviteCode && (
    <InviteCodeCard>
      <Code>{inviteCode}</Code>
      <CopyButton />
      <p>Expires: {inviteExpiry}</p>
    </InviteCodeCard>
  )}

  <Table>
    <thead>
      <tr>
        <th>User</th>
        <th>Role</th>
        <th>Joined</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {members.map(member => (
        <tr key={member.user_id}>
          <td>{member.username}</td>
          <td>
            <RoleSelector
              value={member.role}
              onChange={(role) => changeRole(member.user_id, role)}
              options={['super_admin', 'admin', 'member', 'guest']}
            />
          </td>
          <td>{formatDate(member.joined_at)}</td>
          <td>
            <Button
              variant="danger"
              onClick={() => removeMember(member.user_id)}
              confirm="Remove user from team? They will lose access to team resources."
            >
              Remove
            </Button>
          </td>
        </tr>
      ))}
    </tbody>
  </Table>
</TeamUsersPanel>
```

**Acceptance Criteria**:
- [ ] Team members listed
- [ ] Invite codes generated
- [ ] Members can be removed
- [ ] Roles can be changed

---

### 4.4: Team Workspace Management (L2)

**Component**: `TeamWorkspacePanel.tsx`

**Features**:
- View team resources (docs, workflows, etc.)
- Manage team vault
- View team activity logs

**Acceptance Criteria**:
- [ ] Team resources visible
- [ ] Activity logs functional
- [ ] Vault management works

---

### Phase 4 Deliverables

- [ ] Admin panel with role-based access
- [ ] User management (Founder)
- [ ] Team management (Super Admin)
- [ ] Team workspace overview
- [ ] Activity logging

**Estimated Time**: 1 week

---

## Phase 5: ElohimOS SDK

**Goal**: Enable developers to build offline-first apps on ElohimOS

**Duration**: 2-3 weeks
**Complexity**: L4

---

### 5.1: SDK Architecture (L3)

**Vision**: Developers build apps in Terminal/Code tab, deploy to teams

**SDK Structure**:
```
@elohimos/sdk
├── core
│   ├── storage (SQLite, DuckDB)
│   ├── ai (Ollama, Metal 4)
│   ├── encryption (Secure Enclave)
│   └── networking (P2P mesh)
├── ui
│   ├── components (React)
│   └── themes
└── cli
    ├── create-app
    ├── dev
    ├── build
    └── deploy
```

**Example App**:
```typescript
// medical-records/src/index.ts
import { ElohimApp, useStorage, useAI } from '@elohimos/sdk'

export default class MedicalRecordsApp extends ElohimApp {
  name = 'Medical Records'
  version = '1.0.0'

  async onInstall() {
    // Create database tables
    await this.storage.execute(`
      CREATE TABLE patients (
        id TEXT PRIMARY KEY,
        name TEXT,
        dob TEXT,
        encrypted_notes TEXT
      )
    `)
  }

  async addPatient(name: string, dob: string, notes: string) {
    const encrypted = await this.encrypt(notes)
    await this.storage.insert('patients', {
      id: this.generateId(),
      name,
      dob,
      encrypted_notes: encrypted
    })
  }

  async aiDiagnosis(symptoms: string) {
    const result = await this.ai.generate({
      model: 'medical-llm',
      prompt: `Analyze symptoms: ${symptoms}`
    })
    return result
  }
}
```

**Deployment**:
```bash
# Developer builds locally
elohim build

# Deploy to team (requires team.apps.deploy permission)
elohim deploy --team engineering
```

---

### 5.2: SDK CLI Tool (L3)

**File**: `packages/sdk-cli/`

**Commands**:
```bash
elohim create <app-name>      # Scaffold new app
elohim dev                     # Run in dev mode
elohim build                   # Build for production
elohim deploy --team <team>    # Deploy to team workspace
elohim logs                    # View app logs
elohim uninstall <app-name>    # Remove app
```

**Acceptance Criteria**:
- [ ] CLI commands functional
- [ ] App scaffolding works
- [ ] Dev mode with hot reload
- [ ] Build produces deployable package

---

### 5.3: App Deployment System (L3)

**Backend**: `apps/backend/api/services/app_deployments.py`

```python
class AppDeploymentService:
    async def deploy_app(
        self,
        team_id: str,
        user_id: str,
        app_package: bytes
    ):
        """
        Deploy app to team workspace

        Requires: team.apps.deploy permission

        - Validates app package
        - Installs to team workspace
        - Runs onInstall() hook
        - Makes available to team members
        """

    async def list_team_apps(self, team_id: str):
        """Get all apps deployed to team"""

    async def uninstall_app(self, team_id: str, app_id: str):
        """Remove app from team"""
```

**Database**:
```sql
CREATE TABLE team_apps (
    id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    deployed_by TEXT NOT NULL,
    deployed_at TEXT,
    manifest TEXT, -- JSON app metadata
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (deployed_by) REFERENCES users(id)
);
```

**Acceptance Criteria**:
- [ ] Apps deploy to teams
- [ ] Permission check enforced
- [ ] Apps visible to team members
- [ ] Uninstall works

---

### Phase 5 Deliverables

- [ ] SDK npm package
- [ ] CLI tool
- [ ] App deployment system
- [ ] Example apps (medical records, inventory)
- [ ] SDK documentation

**Estimated Time**: 2-3 weeks

---

## Phase 6: P2P Mesh Networking

**Goal**: Device-to-device sync without cloud

**Duration**: 2 weeks
**Complexity**: L4

---

### 6.1: P2P Discovery (L3)

**File**: `apps/backend/api/services/p2p_discovery.py`

**Technologies**:
- Zeroconf (mDNS/DNS-SD)
- libp2p

**Features**:
- Discover nearby devices
- Establish peer connections
- Maintain peer list

**Acceptance Criteria**:
- [ ] Devices discover each other on LAN
- [ ] Peer connections established
- [ ] Peer list updated

---

### 6.2: P2P Sync Protocol (L4)

**File**: `apps/backend/api/services/p2p_sync.py`

**Features**:
- Sync chat sessions
- Sync docs
- Sync workflows
- Conflict resolution

**Acceptance Criteria**:
- [ ] Data syncs between devices
- [ ] Conflicts resolved
- [ ] Works offline (no internet)

---

### Phase 6 Deliverables

- [ ] P2P discovery functional
- [ ] Sync protocol implemented
- [ ] Conflict resolution works
- [ ] Multi-device sync tested

**Estimated Time**: 2 weeks

---

## Phase 7: MagnetarCloud Integration

**Goal**: Optional cloud layer (future, beyond ElohimOS foundation)

**Duration**: TBD
**Complexity**: L4

**Note**: This is NOT part of ElohimOS foundation. ElohimOS must work 100% offline first.

**Future Features**:
- Cloud backup (optional)
- Team collaboration via cloud
- Cross-device sync via cloud
- Enterprise SSO

---

## Testing & Validation

### Test Strategy

**Unit Tests**:
- All service layer functions
- Permission checks
- Encryption/decryption

**Integration Tests**:
- End-to-end user flows
- Multi-user scenarios
- Team collaboration

**Field Tests**:
- Offline mode (airplane mode)
- Shared laptop (multiple users)
- Network unreliability
- Battery optimization

### Acceptance Criteria (Overall)

**ElohimOS Foundation is Complete When**:
- [ ] Setup wizard works for new users
- [ ] All tabs work 100% offline
- [ ] Multi-user support on shared device
- [ ] Team collaboration functional
- [ ] RBAC enforced correctly
- [ ] Founder rights bypass works
- [ ] Admin panel access controlled
- [ ] SDK apps deployable
- [ ] P2P sync works
- [ ] No network calls in local mode
- [ ] Data encrypted at rest
- [ ] Zero test failures

---

## Success Metrics

### Performance Targets

- **Startup Time**: < 3 seconds
- **Model Load Time**: < 5 seconds (hot slot models)
- **Chat Response**: < 2 seconds (first token)
- **Database Queries**: < 50ms (95th percentile)
- **Encryption/Decryption**: < 10ms

### Reliability Targets

- **Uptime**: 99.9% (local service)
- **Data Loss**: 0% (all data persisted)
- **Crash Recovery**: < 1 second

### User Experience Targets

- **Setup Wizard**: < 15 minutes (including model downloads)
- **Context Switch**: < 500ms (local ↔ team)
- **Search Latency**: < 100ms

---

## Conclusion

This roadmap provides a **systems engineering approach** to building ElohimOS from the ground up. Each phase is **independently testable** and delivers **tangible value**. The architecture follows **Separation of Concerns** and **System of Systems** principles, ensuring:

1. **Modularity**: Each system can be developed/tested independently
2. **Offline-First**: No network dependencies in core functionality
3. **Progressive Enhancement**: Local → P2P → Team → Cloud
4. **No Hardcoded Defaults**: User-driven configuration
5. **Foundation for Scale**: ElohimOS → MagnetarCloud Standard → Enterprise

**Critical Success Factor**: ElohimOS must be bulletproof. Every feature works offline. No exceptions.

---

**Next Steps**: Execute Phase 0 (fix current issues) → Phase 1 (setup wizard) → Phase 2 (local core) → ...

**Estimated Total Time**: 8-10 weeks for foundation (Phases 0-6)

---

**End of Roadmap**

---

## Alignment Notes (Codebase vs Roadmap) – 2025‑11‑12

This section documents concrete updates needed so the roadmap matches the current implementation.

1) Founder Rights – Implementation
- Replace static founder list with role‑based bypass.
- Implemented as: permission_engine.has_permission → if user_ctx.role == 'founder_rights' then allow.
- Development: ELOHIM_FOUNDER_PASSWORD must be set in production; default only in dev.

2) Super Admin (Local‑Only) – Access and Powers
- Update “Access” to: Limited Admin Panel (view dashboard, manage users/settings; cannot manage permissions by default).
- Powers reflect current baseline in permission_engine.py: may view admin dashboard, manage users, manage settings; cannot manage permissions by default.

3) Permission Key Naming & Team Context
- Use neutral keys (e.g., "docs.read", "chat.use").
- Team awareness is applied at check time via require_perm_team(...), which loads context with team_id.
- Replace “team.*” examples with:
  {
    "docs.read": true,
    "docs.write": false,
    "chat.use": true,
    "workflows.execute": true,
    "workflows.deploy": false,
    "vault.read": true,
    "vault.write": false,
    "apps.deploy": false,
    "system.view_admin_dashboard": false
  }

4) Phase 0.1: Model Preloading Clarification
- Actual behavior: default model is preloaded from the frontend (App.tsx) after session creation; hot slots are not the source of startup loads.
- Actions:
  - Add logging to distinguish "Frontend preload" vs "Hot slot preload".
  - Make frontend default preload user‑controlled (toggle) or disabled by default.
- Files: apps/frontend/src/App.tsx; apps/backend/api/model_manager.py (logging).
- Acceptance: no preload unless user assigns hot slots and loads them, or enables default preload.

5) Hot Slots Storage
- Current storage is JSON: data_dir/model_hot_slots.json (not a DB table).
- Update references from JSON (model_hot_slots.json) to JSON config; optional future migration can be planned separately.

6) Setup Completed Flag
- Current implementation uses founder_setup table with setup_completed flag.
- Keep this mechanism for now; optional future migration to users table if per-user setup state is needed.

7) Context Switching (Local ↔ Team)
- Permission engine already supports team context via require_perm_team(team_id).
- The Header UI toggle is not implemented yet; document as planned work to set active team_id and pass it to endpoints.

8) Phase 1: First‑Run Setup Wizard
- Extend existing Founder Setup Wizard (founder_setup_wizard + founder_setup_routes) to cover:
  - Local account creation
  - Ollama detection & model recommendations
  - Model downloads using config/recommended_models.json
  - Hot slot assignment (writes model_hot_slots.json)
- Introduce apps/backend/api/config/recommended_models.json per the schema in Phase 0.3.

9) Phase 0 Deliverables – Wording
- Replace “JSON (model_hot_slots.json) initialized on startup” with “model_hot_slots.json initialized on demand; logs identify preload sources clearly.”

10) Permission Model Documentation Deliverable
- Base documentation on permission_engine.py keys (e.g., docs.read, chat.use).
- Explain team‑aware checks (require_perm_team), founder bypass, and current role baselines (super_admin/admin/member/guest).

11) AI Engine Data Store Reference
- Replace “JSON (model_hot_slots.json)” with “JSON config (model_hot_slots.json) + runtime status via Ollama APIs.”

