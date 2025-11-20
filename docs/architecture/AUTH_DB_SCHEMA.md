# Auth Database Schema

**Status**: Stabilized (AUTH-P1)
**Last Updated**: 2025-11-20

## Overview

ElohimOS uses a consolidated auth database schema managed through an explicit migration system. All authentication, authorization, and permissions data lives in `elohimos_app.db` (or `auth.db` in legacy deployments).

**Key Principles**:
- **Offline-first**: Single-device SQLite database with WAL mode
- **Migration-managed**: All schema changes go through `api/migrations/auth/` system
- **Multi-user ready**: Supports multiple engineers with role-based access control
- **Auditable**: Permission checks logged for security analysis

---

## Database: `elohimos_app.db`

**Location**: `.neutron_data/elohimos_app.db` (default)
**Mode**: SQLite with WAL (Write-Ahead Logging)
**Migrations**: `api/migrations/auth/`

---

## Schema Tables

### 1. Authentication

#### `users` - Identity and credentials
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,       -- PBKDF2-HMAC-SHA256, 600k iterations
    device_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_login TEXT,
    is_active INTEGER DEFAULT 1,
    role TEXT DEFAULT 'member',        -- founder_rights, super_admin, admin, member, guest
    job_role TEXT                      -- Optional: engineer, manager, etc.
)
```

**Roles**:
- `founder_rights` - Superuser with full bypass (Founder account)
- `super_admin` - All permissions unless explicitly denied
- `admin` - Most features, limited system permissions
- `member` - Core features, own resources
- `guest` - Read-only access

#### `sessions` - JWT token sessions
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    refresh_token_hash TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,           -- Token expiration (default: 7 days)
    refresh_expires_at TEXT,            -- Refresh token expiration (30 days)
    device_fingerprint TEXT,
    last_activity TEXT,                 -- For idle timeout tracking
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

**Indexes**:
- `idx_sessions_user` on `(user_id)`
- `idx_sessions_expires` on `(expires_at)`
- `idx_sessions_last_activity` on `(last_activity)`
- `idx_sessions_expires_user` on `(expires_at, user_id)` - Composite for cleanup queries

---

### 2. User Profiles

#### `user_profiles` - Profile data separate from auth
```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    device_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    avatar_color TEXT,
    bio TEXT,
    role_changed_at TEXT,
    role_changed_by TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
)
```

**Purpose**: Separates profile/display data from authentication credentials.

---

### 3. Permissions Registry

#### `permissions` - All available permissions
```sql
CREATE TABLE permissions (
    permission_id TEXT PRIMARY KEY,
    permission_key TEXT NOT NULL UNIQUE,      -- e.g., "vault.documents.read"
    permission_name TEXT NOT NULL,
    permission_description TEXT,
    category TEXT NOT NULL,                   -- feature, resource, system
    subcategory TEXT,                          -- vault, workflows, docs, etc.
    permission_type TEXT NOT NULL CHECK(permission_type IN ('boolean', 'level', 'scope')),
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
)
```

**Permission Types**:
- `boolean` - Simple true/false (e.g., `chat.use`)
- `level` - Hierarchical levels: `none`, `read`, `write`, `admin` (e.g., `vault.documents.read`)
- `scope` - Scope-based with JSON data (future expansion)

**Categories**:
- `feature` - High-level feature access (chat, vault, workflows)
- `resource` - CRUD operations on resources
- `system` - Administrative operations (manage users, view audit logs)

**Indexes**:
- `idx_permissions_key` on `(permission_key)`
- `idx_permissions_category` on `(category)`

---

### 4. RBAC Profiles

#### `permission_profiles` - Reusable permission bundles
```sql
CREATE TABLE permission_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL,
    profile_description TEXT,
    team_id TEXT,                             -- NULL = system-wide, non-NULL = team-scoped
    applies_to_role TEXT CHECK(applies_to_role IN ('admin', 'member', 'guest', 'any')),
    created_by TEXT,
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
)
```

**Base Profiles**:
- `profile_admin_base` - Default admin permissions
- `profile_member_base` - Default member permissions
- `profile_guest_base` - Default guest permissions

#### `profile_permissions` - Permissions in profiles
```sql
CREATE TABLE profile_permissions (
    profile_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    is_granted INTEGER DEFAULT 1,
    permission_level TEXT CHECK(permission_level IN ('none', 'read', 'write', 'admin')),
    permission_scope TEXT,                     -- JSON for scope-based permissions
    PRIMARY KEY (profile_id, permission_id),
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
)
```

**Indexes**:
- `idx_profiles_role` on `(applies_to_role)`
- `idx_profiles_active` on `(is_active)`

---

### 5. Permission Sets

#### `permission_sets` - Ad-hoc permission grants
```sql
CREATE TABLE permission_sets (
    permission_set_id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,
    set_description TEXT,
    team_id TEXT,                             -- NULL = system-wide
    created_by TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
)
```

**Purpose**: Grant specific permissions to users without creating a full profile. Useful for temporary access or exceptions.

#### `permission_set_permissions` - Permissions in sets
```sql
CREATE TABLE permission_set_permissions (
    permission_set_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    is_granted INTEGER DEFAULT 1,
    permission_level TEXT CHECK(permission_level IN ('none','read','write','admin')),
    permission_scope TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (permission_set_id, permission_id),
    FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
)
```

**Indexes**:
- `idx_permission_set_permissions_set_id` on `(permission_set_id)`

---

### 6. User Assignments

#### `user_permission_profiles` - User → profile assignments
```sql
CREATE TABLE user_permission_profiles (
    user_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (user_id, profile_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE
)
```

#### `user_permission_sets` - User → permission set assignments
```sql
CREATE TABLE user_permission_sets (
    user_id TEXT NOT NULL,
    permission_set_id TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at TEXT NOT NULL,
    expires_at TEXT,                          -- Optional expiration for temporary grants
    PRIMARY KEY (user_id, permission_set_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id) ON DELETE CASCADE
)
```

**Indexes**:
- `idx_user_profiles_user` on `(user_id)`
- `idx_user_profiles_profile` on `(profile_id)`
- `idx_user_sets_user` on `(user_id)`
- `idx_user_sets_set` on `(permission_set_id)`
- `idx_user_permission_sets_user_id` on `(user_id)`
- `idx_user_permission_profiles_user_id` on `(user_id)`

---

### 7. Optional Caching

#### `user_permissions_cache` - Cached permission resolutions
```sql
CREATE TABLE user_permissions_cache (
    user_id TEXT PRIMARY KEY,
    permissions_json TEXT NOT NULL,           -- JSON of resolved permissions
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
)
```

**Purpose**: Optional DB-level caching for permission resolution. In-memory caching in `PermissionEngine` is primary.

---

### 8. Migration Tracking

#### `migrations` - Schema version tracking
```sql
CREATE TABLE migrations (
    migration_name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
)
```

**Auth Migrations**:
- `auth_0001_initial` - Consolidated auth/permissions schema (AUTH-P1)

---

## Permission Resolution Logic

**Order of Resolution** (in `PermissionEngine`):
1. **Check role**:
   - `founder_rights`: Always allow (bypass)
   - `super_admin`: Allow unless explicitly denied
2. **Load base role permissions**: Default baseline for `admin`, `member`, `guest`
3. **Apply profile grants**: Add/override from assigned profiles
4. **Apply permission set grants**: Add/override from assigned sets (highest priority)
5. **Evaluate permission**:
   - Boolean: Check if `True`
   - Level: Check if user level ≥ required level
   - Scope: Check scope intersection (future)

**Caching**:
- In-memory cache in `PermissionEngine` (per user + team context)
- Invalidate on role changes, profile assignments, permission set grants

---

## Migration System

**Location**: `apps/backend/api/migrations/auth/`

**Structure**:
```
api/migrations/auth/
├── __init__.py           # Exports run_auth_migrations
├── runner.py             # Migration runner
└── 0001_initial.py       # Initial schema migration
```

**Running Migrations**:
Migrations run automatically on application startup via `startup_migrations.py`:

```python
from api.migrations.auth import run_auth_migrations
conn = sqlite3.connect(str(app_db_path))
run_auth_migrations(conn)
conn.close()
```

**Adding New Migrations**:
1. Create `apps/backend/api/migrations/auth/XXXX_description.py`
2. Implement `apply_migration(conn: sqlite3.Connection)` function
3. Add to `runner.py` migrations list
4. Migration will run automatically on next startup

---

## Related Files

| File | Purpose |
|------|---------|
| `api/auth_middleware.py` | Authentication service, JWT validation |
| `api/permissions/engine.py` | Permission evaluation engine |
| `api/permissions/storage.py` | Database connection helpers |
| `api/migrations/auth/` | Auth schema migrations |
| `api/startup_migrations.py` | Migration runner (startup) |
| `tests/test_auth_migrations.py` | Auth migration tests |

---

## Security Notes

1. **Password Hashing**: PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2023 recommendation)
2. **JWT Secret**: Persisted to `.neutron_data/.jwt_secret` or set via `ELOHIMOS_JWT_SECRET_KEY` env var
3. **Token Expiration**: 7 days (access token), 30 days (refresh token)
4. **Idle Timeout**: Tracked via `sessions.last_activity`
5. **Founder Account**: Hardcoded backdoor with `ELOHIM_FOUNDER_PASSWORD` (field support)
6. **Audit Logging**: Permission denials logged to audit log (see `audit_logger.py`)

---

## Next Steps (AUTH-P2+)

- [ ] **AUTH-P2**: Normalize Founder into DB (no more hardcoded backdoor)
- [ ] **AUTH-P3**: Tighten RBAC boundaries (audit all `@require_perm` usage)
- [ ] **AUTH-P4**: Harden tokens & sessions (stable secrets, explicit expiry)
- [ ] **AUTH-P5**: Expand audit coverage (all admin/RBAC operations)
