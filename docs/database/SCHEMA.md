# ElohimOS Database Schema Documentation

**Version**: 1.0
**Last Updated**: 2025-11-14
**Total Databases**: 3 (consolidated)

---

## Overview

ElohimOS uses **3 consolidated SQLite databases** under `.neutron_data/`:

- **elohimos_app.db** - Main application database (users, auth, sessions, docs, chat memory, workflows, RBAC, analytics, etc.)
- **vault.db** - Vault documents/files/folders, ACL and vault-specific metadata
- **datasets.db** - Datasets for data engine

All previous separate databases are consolidated into `app_db` via `PATHS` (see `apps/backend/api/config_paths.py`). Legacy database references (users_db, auth_db, docs_db, etc.) are compatibility aliases pointing to `elohimos_app.db`.

All databases use:
- **WAL Mode** (Write-Ahead Logging) for concurrent access
- **PRAGMA synchronous=NORMAL** for balance of safety and performance
- **Memory-mapped I/O** (30GB mmap_size) for performance

**Storage Location**: `.neutron_data/`

---

## Database 1: elohimos_app.db (Main Application)

**Size**: ~260 KB
**Purpose**: User authentication, teams, permissions, RBAC system

### Users & Authentication

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,              -- PBKDF2
    device_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_login TEXT,
    is_active INTEGER DEFAULT 1,
    must_change_password INTEGER DEFAULT 0,   -- enforced on first login when reset
    role TEXT DEFAULT 'member',               -- System role
    job_role TEXT DEFAULT 'unassigned'        -- Organizational role
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,                 -- JWT hash
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    device_fingerprint TEXT,
    last_activity TEXT,
    refresh_token_hash TEXT,
    refresh_expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

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
);
```

**Indexes**:
- `idx_sessions_user` on sessions(user_id)
- `idx_sessions_expires` on sessions(expires_at)

### RBAC System

```sql
CREATE TABLE permissions (
    permission_id TEXT PRIMARY KEY,
    permission_key TEXT NOT NULL UNIQUE,      -- e.g., 'workflows.create'
    permission_name TEXT NOT NULL,
    permission_description TEXT,
    category TEXT NOT NULL,                   -- e.g., 'Workflows'
    subcategory TEXT,
    permission_type TEXT NOT NULL,            -- 'boolean', 'level', 'scope'
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE permission_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL,
    profile_description TEXT,
    team_id TEXT,                              -- NULL = system-wide
    applies_to_role TEXT,                      -- 'admin', 'member', 'guest', 'any'
    created_by TEXT,
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE profile_permissions (
    profile_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,
    is_granted INTEGER DEFAULT 1,
    permission_level TEXT,                     -- 'none', 'read', 'write', 'admin'
    permission_scope TEXT,                     -- JSON scope definition
    PRIMARY KEY (profile_id, permission_id),
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(permission_id) ON DELETE CASCADE
);

CREATE TABLE permission_sets (
    permission_set_id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,
    set_description TEXT,
    team_id TEXT,                              -- NULL = system-wide
    created_by TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE user_permission_profiles (
    user_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (user_id, profile_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id) ON DELETE CASCADE
);

CREATE TABLE user_permission_sets (
    user_id TEXT NOT NULL,
    permission_set_id TEXT NOT NULL,
    assigned_by TEXT,
    assigned_at TEXT NOT NULL,
    expires_at TEXT,                           -- Optional expiration
    PRIMARY KEY (user_id, permission_set_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id) ON DELETE CASCADE
);
```

### Migrations

```sql
CREATE TABLE migrations (
    migration_name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);
```

---

## Database 2: teams.db (Team Collaboration)

**Size**: ~116 KB
**Purpose**: Team management, invite codes, delayed promotions, vault permissions

### Teams & Members

```sql
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL
);

CREATE TABLE team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,                        -- 'super_admin', 'admin', 'member', 'guest'
    job_role TEXT DEFAULT 'unassigned',        -- Organizational role
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, user_id)
);
```

### Invite System

```sql
CREATE TABLE invite_codes (
    code TEXT PRIMARY KEY,                     -- OMNI-XXXX-XXXX format
    team_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    used_by TEXT,
    used_at TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE invite_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invite_code TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL
);
```

**Index**:
- `idx_invite_attempts_code_ip` on invite_attempts(invite_code, ip_address, attempt_timestamp DESC)

**Brute-Force Protection**: 5 failed attempts per IP per hour → block

### Delayed Promotions (Decoy Password Feature)

```sql
CREATE TABLE delayed_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    from_role TEXT NOT NULL,
    to_role TEXT NOT NULL,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execute_at TIMESTAMP NOT NULL,             -- 21 days from join
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    reason TEXT,                                -- 'decoy_password'
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, user_id, executed)
);
```

**Use Case**: User enters decoy password → joins as Guest → auto-promoted to Member after 21 days

### Offline Super Admin Failsafe

```sql
CREATE TABLE temp_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    original_super_admin_id TEXT NOT NULL,
    promoted_admin_id TEXT NOT NULL,
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reverted_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    reason TEXT,
    approved_by TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, promoted_admin_id, status)
);
```

**Use Case**: Super Admin offline >30 days → Admin can request temp promotion

### Team Vault

```sql
CREATE TABLE team_vault_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,                   -- 'document', 'file', etc.
    encrypted_content TEXT NOT NULL,           -- Client-encrypted
    encryption_key_hash TEXT,                  -- For verification
    file_size INTEGER,
    mime_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    deleted_by TEXT,
    metadata TEXT,                              -- JSON
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(item_id, team_id)
);

CREATE TABLE team_vault_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    permission_type TEXT NOT NULL,             -- 'read', 'write', 'admin'
    grant_type TEXT NOT NULL,                  -- 'role', 'user'
    grant_value TEXT NOT NULL,                 -- role name or user_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(item_id, team_id, permission_type, grant_type, grant_value)
);
```

### Workflow Permissions

```sql
CREATE TABLE workflow_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    permission_type TEXT NOT NULL,
    grant_type TEXT NOT NULL,
    grant_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(workflow_id, team_id, permission_type, grant_type, grant_value)
);
```

### Queues

```sql
CREATE TABLE queues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    queue_name TEXT NOT NULL,
    queue_type TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(queue_id, team_id)
);

CREATE TABLE queue_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    access_type TEXT NOT NULL,
    grant_type TEXT NOT NULL,
    grant_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(queue_id, team_id, access_type, grant_type, grant_value)
);
```

### God Rights (Founder Rights)

```sql
CREATE TABLE god_rights_auth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    auth_key_hash TEXT,
    delegated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    notes TEXT
);
```

---

## Database 3: workflows.db (Workflow Automation)

**Size**: ~112 KB
**Purpose**: Workflow definitions, work items, stage transitions

### Workflows

```sql
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    category TEXT,
    stages TEXT NOT NULL,                      -- JSON array of stage definitions
    triggers TEXT NOT NULL,                    -- JSON array of triggers
    enabled INTEGER DEFAULT 1,
    allow_manual_creation INTEGER DEFAULT 1,
    require_approval_to_start INTEGER DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    tags TEXT,                                 -- JSON array
    user_id TEXT,                              -- User isolation
    team_id TEXT,                              -- Team isolation (NULL = personal)
    workflow_type TEXT DEFAULT 'team'
);

CREATE TABLE starred_workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    starred_at TEXT NOT NULL,
    UNIQUE(user_id, workflow_id),
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);
```

**Indexes**:
- `idx_workflows_user` on workflows(user_id)
- `idx_workflows_team` on workflows(team_id)
- `idx_starred_user` on starred_workflows(user_id)
- `idx_starred_workflow` on starred_workflows(workflow_id)

### Work Items

```sql
CREATE TABLE work_items (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    current_stage_id TEXT NOT NULL,
    current_stage_name TEXT NOT NULL,
    status TEXT NOT NULL,                      -- 'QUEUED', 'CLAIMED', 'IN_PROGRESS', 'COMPLETED'
    priority TEXT NOT NULL,                    -- 'Low', 'Normal', 'High', 'Urgent'
    assigned_to TEXT,
    claimed_at TEXT,
    data TEXT NOT NULL,                        -- JSON (accumulated stage data)
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    sla_due_at TEXT,
    is_overdue INTEGER DEFAULT 0,
    tags TEXT,                                 -- JSON array
    reference_number TEXT,
    user_id TEXT,
    team_id TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

**Indexes**:
- `idx_work_items_workflow` on work_items(workflow_id)
- `idx_work_items_status` on work_items(status)
- `idx_work_items_assigned` on work_items(assigned_to)
- `idx_work_items_overdue` on work_items(is_overdue)
- `idx_work_items_user` on work_items(user_id)
- `idx_work_items_team` on work_items(team_id)

### Stage Transitions

```sql
CREATE TABLE stage_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_item_id TEXT NOT NULL,
    from_stage_id TEXT,
    to_stage_id TEXT,
    transitioned_at TEXT NOT NULL,
    transitioned_by TEXT,
    notes TEXT,
    duration_seconds INTEGER,
    user_id TEXT,
    team_id TEXT,
    FOREIGN KEY (work_item_id) REFERENCES work_items(id)
);
```

**Indexes**:
- `idx_transitions_work_item` on stage_transitions(work_item_id)
- `idx_transitions_user` on stage_transitions(user_id)
- `idx_transitions_team` on stage_transitions(team_id)

### Attachments

```sql
CREATE TABLE attachments (
    id TEXT PRIMARY KEY,
    work_item_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    user_id TEXT,
    team_id TEXT,
    FOREIGN KEY (work_item_id) REFERENCES work_items(id)
);
```

**Indexes**:
- `idx_attachments_user` on attachments(user_id)
- `idx_attachments_team` on attachments(team_id)

---

## Database 4: datasets.db (Data Engine)

**Purpose**: Uploaded files and metadata

### Dataset Metadata

```sql
CREATE TABLE dataset_metadata (
    dataset_id TEXT PRIMARY KEY,
    original_filename TEXT,
    table_name TEXT UNIQUE,                   -- e.g., 'ds_abc12345'
    upload_timestamp TEXT,
    row_count INTEGER,
    column_count INTEGER,
    schema_json TEXT,                         -- JSON schema definition
    file_hash TEXT,
    file_type TEXT,                           -- '.xlsx', '.csv', '.json'
    session_id TEXT
);
```

**Index**:
- `idx_metadata_session` on dataset_metadata(session_id)

### Dynamic Tables

**Format**: `ds_{hash}` (created dynamically per upload)

Example:
```sql
CREATE TABLE ds_abc12345 (
    column1 VARCHAR,
    column2 DOUBLE,
    column3 DATE,
    ...
);
```

**Note**: These tables are created in DuckDB (in-memory) during query execution, NOT in SQLite.

---

## Database 5: chat_memory.db (AI Chat)

**Size**: ~28 KB (varies with usage)
**Purpose**: Chat sessions and message history

### Chat Sessions

```sql
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    team_id TEXT,                              -- Optional team context
    title TEXT,
    model TEXT,                                -- Ollama model name
    created_at TEXT,
    updated_at TEXT,
    message_count INTEGER DEFAULT 0
);
```

### Chat Messages

```sql
CREATE TABLE chat_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,                        -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TEXT,
    files JSON,                                -- Attached files
    model TEXT,
    tokens INTEGER,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);
```

### Chat Summaries (Rolling Summaries)

```sql
CREATE TABLE chat_summaries (
    summary_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    messages_covered INTEGER,                  -- How many messages summarized
    created_at TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);
```

---

## Database 6: learning.db (Adaptive Learning)

**Size**: ~20 KB
**Purpose**: User behavior patterns and performance metrics

### Learned Patterns

```sql
CREATE TABLE learned_patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_type TEXT,                         -- 'query', 'workflow', 'preference'
    pattern_data JSON,                         -- Pattern definition
    frequency INTEGER,
    last_seen TEXT,
    user_id TEXT
);
```

### Performance Metrics

```sql
CREATE TABLE performance_metrics (
    metric_id TEXT PRIMARY KEY,
    backend TEXT,                              -- 'ane', 'metal4', 'cpu'
    task_type TEXT,
    latency_ms REAL,
    throughput REAL,
    power_mw REAL,                             -- Estimated power consumption
    timestamp TEXT
);
```

---

## Database 7: audit.db (Audit Logging)

**Size**: ~40 KB
**Purpose**: Comprehensive audit trail (90-day retention)

### Audit Log

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,                      -- Action type (see AuditAction enum)
    resource TEXT,                             -- Resource type
    resource_id TEXT,                          -- Resource identifier
    ip_address TEXT,
    user_agent TEXT,
    timestamp TEXT NOT NULL,
    details TEXT                               -- JSON (sanitized)
);
```

**Indexes**:
- `idx_audit_user_id` on audit_log(user_id)
- `idx_audit_action` on audit_log(action)
- `idx_audit_timestamp` on audit_log(timestamp)
- `idx_audit_resource` on audit_log(resource, resource_id)

**Retention**: Auto-delete after 90 days

**Standard Actions** (from `AuditAction` enum):
- Authentication: `user.login`, `user.logout`, `user.login.failed`
- Vault: `vault.accessed`, `vault.item.created`, `vault.item.viewed`
- Workflows: `workflow.created`, `workflow.executed`
- Teams: `team.created`, `team.member.added`, `team.role.changed`
- Security: `panic_mode.activated`, `encryption_key.rotated`
- Admin: `admin.list.users`, `admin.view.user_chats`

---

## Database 8: vault.db (Encrypted Storage)

**Purpose**: Encrypted document and file storage

**Note**: Schema not shown in current dump. Likely structure:

### Vault Documents

```sql
CREATE TABLE vault_documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    vault_type TEXT CHECK(vault_type IN ('real', 'decoy')),
    encrypted_blob TEXT NOT NULL,             -- Client-encrypted document
    encrypted_metadata TEXT NOT NULL,         -- Client-encrypted metadata
    created_at TEXT,
    updated_at TEXT,
    size_bytes INTEGER,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,
    UNIQUE(id, user_id, vault_type)
);
```

### Vault Files

```sql
CREATE TABLE vault_files (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    vault_type TEXT CHECK(vault_type IN ('real', 'decoy')),
    filename TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    encrypted_path TEXT NOT NULL,             -- Path to encrypted file on disk
    folder_path TEXT DEFAULT '/',
    created_at TEXT,
    updated_at TEXT,
    is_deleted INTEGER DEFAULT 0,
    UNIQUE(id, user_id, vault_type)
);
```

**Security**: All encryption happens client-side (Web Crypto API). Server cannot read vault contents.

---

## Relationships

### Cross-Database Relationships

```
elohimos_app.db
├── users.user_id
│   ├──> sessions.user_id
│   ├──> user_profiles.user_id
│   ├──> user_permission_profiles.user_id
│   ├──> user_permission_sets.user_id
│   ├──> chat_memory.db::chat_sessions.user_id
│   ├──> workflows.db::workflows.user_id
│   ├──> workflows.db::work_items.user_id
│   └──> vault.db::vault_documents.user_id
│
└── teams.db::teams.team_id
    ├──> team_members.team_id
    ├──> team_vault_items.team_id
    ├──> workflows.db::workflows.team_id
    └──> workflows.db::work_items.team_id
```

**Note**: Cross-database relationships are **logical**, not enforced by foreign keys (SQLite doesn't support cross-database FKs).

---

## Data Types

### Text Fields
- `TEXT` - Variable-length strings
- `JSON` - JSON-encoded data stored as TEXT (parsed in application)

### Numeric Fields
- `INTEGER` - 64-bit signed integers
- `REAL` - 64-bit floating point
- `BOOLEAN` - Stored as INTEGER (0 or 1)

### Timestamps
- Format: ISO 8601 strings (`YYYY-MM-DDTHH:MM:SS.ffffff`)
- Example: `2025-11-11T21:00:00.123456`
- SQLite `CURRENT_TIMESTAMP` for defaults

---

## Migrations

### Migration Strategy

**Current**: Manual SQL scripts in `apps/backend/api/migrations/`

**Files**:
- `phase1_sessions_refresh_tokens.sql`
- `phase2_permission_system.sql`
- `phase3_team_workflows.sql`
- `phase4_performance_indexes.sql`
- etc.

**Tracking**: `migrations` table in `elohimos_app.db`

**Process**:
1. Create migration SQL file
2. Apply manually via `sqlite3 .neutron_data/elohimos_app.db < migration.sql`
3. Record in migrations table

**Future**: Automated migration framework (Alembic or similar)

---

## Backup & Recovery

### Backup Strategy

**Automatic**:
- Daily backups to external drive
- 7-day retention
- WAL checkpoint before backup

**Manual**:
```bash
# Backup all databases
tar -czf neutron_data_backup_$(date +%Y%m%d).tar.gz .neutron_data/

# Backup single database
sqlite3 .neutron_data/elohimos_app.db ".backup backup_app.db"
```

### Recovery

**From Backup**:
```bash
# Extract backup
tar -xzf neutron_data_backup_YYYYMMDD.tar.gz

# Verify integrity
sqlite3 .neutron_data/elohimos_app.db "PRAGMA integrity_check;"
```

**From Audit Log** (if database corrupted):
1. Restore from last good backup
2. Replay audit log entries
3. Verify data consistency

---

## Performance Considerations

### Indexes

**Strategy**: Index frequently queried columns
- Foreign keys (user_id, team_id, workflow_id)
- Status fields (status, is_active, is_deleted)
- Timestamps (created_at, expires_at)
- Compound indexes for common queries

**Examples**:
- `idx_work_items_status` - Fast queue lookups
- `idx_audit_timestamp` - Fast audit log queries
- `idx_invite_attempts_code_ip` - Brute-force protection

### WAL Mode

**Advantages**:
- Concurrent reads (no blocking)
- Better crash recovery
- Faster writes

**Disadvantages**:
- 2-3x disk space usage (WAL + SHM files)
- Requires `PRAGMA checkpoint` periodically

**Checkpoint Strategy**: Weekly VACUUM (automatic)

### Query Optimization

**Tips**:
- Use prepared statements (prevent SQL injection)
- Limit result sets (`LIMIT` clause)
- Avoid `SELECT *` (fetch only needed columns)
- Use indexes for `WHERE`, `ORDER BY`, `JOIN`

---

## Security

### Encryption

**Vault Database**: Client-side encryption (AES-256-GCM)
- Server stores only encrypted blobs
- Decryption in browser (Web Crypto API)

**Other Databases**: Filesystem-level encryption (FileVault on macOS)
- Optional: SQLCipher for database-level encryption

### Password Storage

**Algorithm**: PBKDF2-HMAC-SHA256
**Iterations**: 600,000
**Salt**: Random per user

### Audit Trail

**Coverage**: All sensitive operations logged
**Immutability**: Append-only table (no updates)
**Retention**: 90 days, then auto-delete

---

## Future Enhancements

1. **Automated Migrations**: Alembic or similar framework
2. **Database Sharding**: Split large tables across multiple databases
3. **Replication**: Multi-device sync with conflict resolution
4. **Full-Text Search**: FTS5 for document search
5. **Compression**: zlib compression for large TEXT fields
6. **Monitoring**: Database size, query performance metrics

---

## Troubleshooting

### Database Locked

**Error**: `sqlite3.OperationalError: database is locked`

**Causes**:
- Long-running transaction
- Abandoned write lock
- Process crash without releasing lock

**Fixes**:
```bash
# Find processes using database
lsof | grep elohimos_app.db

# Kill process
kill <PID>

# Force checkpoint (if safe)
sqlite3 .neutron_data/elohimos_app.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Disk Space

**Check database sizes**:
```bash
du -h .neutron_data/*.db
du -h .neutron_data/*-wal
du -h .neutron_data/*-shm
```

**Reclaim space** (VACUUM):
```bash
sqlite3 .neutron_data/elohimos_app.db "VACUUM;"
```

### Corruption

**Check integrity**:
```bash
sqlite3 .neutron_data/elohimos_app.db "PRAGMA integrity_check;"
```

**Recovery**:
1. Restore from backup
2. Export uncorrupted data: `sqlite3 bad.db .dump | sqlite3 good.db`

---

## Schema Version

**Current Version**: 1.0
**Last Schema Change**: 2025-11-07 (Phase 5 - Security Hardening)

To check applied migrations:
```sql
SELECT * FROM migrations ORDER BY applied_at DESC;
```
