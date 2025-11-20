# ElohimOS Authorization & Identity Roadmap

**Status:** Phase 1-6 Complete ✅ (as of 2025-11-20)
**Scope:** Turn ElohimOS into a "local IAM appliance" – a robust, offline‑first authorization system with durable DB schema, clear roles, strong audit, and safe update behavior.
**Audience:** You / future backend + security engineers working on auth/permissions in ElohimOS.

## Implementation Status

- ✅ **AUTH-P1**: Auth DB schema & migrations (Complete - 2025-11-20)
- ✅ **AUTH-P2**: Normalize Founder account (Complete - 2025-11-20)
- ✅ **AUTH-P3**: RBAC coverage & policy tests (Complete - 2025-11-20)
- ✅ **AUTH-P4**: Token & session hardening (Complete - 2025-11-20)
- ✅ **AUTH-P5**: Audit log coverage & consistency (Complete - 2025-11-20)
- ✅ **AUTH-P6**: Update safety & device identity (Complete - 2025-11-20)
- 🔜 **Future**: Update server/client for automatic updates

---

This roadmap assumes:

- ElohimOS is **fully offline by default**.
- There is exactly one “tiny update API” that connects to a secure update server **only when the user explicitly chooses**.
- All real work (users, roles, workflows, agent actions) happens on the **local device**.

The goal is to make authn/authz feel **boringly reliable** in the field:

- Multiple engineers can share a device safely.
- Roles and permissions are explicit and testable.
- Audit logs are trustworthy.
- Updates never silently “blow away” identity data.

---

## 0. Design Goals & Non‑Negotiables

### 0.1 Goals

- **Offline‑first IAM**:
  - All users, teams, roles, permissions, sessions, and audit logs live in a local DB (SQLite).
  - No dependency on cloud identity providers.

- **Predictable behavior**:
  - Clear schema and invariants.
  - No hidden “magic env‑based” behavior beyond an explicit dev/prod switch.

- **Multi‑user, multi‑role**:
  - Multiple humans (engineers, admins) can share one device without stepping on each other.
  - Roles and permissions define who can do what.

- **Auditable & explainable**:
  - Every sensitive action is traceable:
    - Who, what, when, on which workflow/work item.

- **Update‑safe**:
  - Software updates never silently corrupt or reset identity data.
  - Migrations are explicit, versioned, and idempotent.

### 0.2 Non‑Negotiables

- **No silent privilege escalation**:
  - No “if ENV=dev then skip checks” in production builds.
  - Founder/Backdoor accounts must be explicit and auditable.

- **No runtime schema drift**:
  - Schema changes only via migrations.
  - No ad‑hoc `CREATE TABLE IF NOT EXISTS` in request handlers.

- **No credentials over the update channel**:
  - The update server never receives user passwords or tokens.
  - At most, it sees minimal device metadata (if needed).

---

## 1. Current State Snapshot

> This section is descriptive; update as needed if code evolves.

- Identity:
  - JWT‑based auth for `/api/v1/*` endpoints.
  - Founder account (special “God rights” user) controlled via env vars.
  - User model stored in a local DB (SQLite), but some behavior still keyed off env (`ELOHIM_ENV`, `ELOHIM_FOUNDER_PASSWORD`).

- Authorization:
  - Modular `api.permissions` package:
    - `types.py`, `engine.py`, `decorators.py`, `admin.py`, `storage.py`.
  - Permission checks via `@require_perm` and `@require_perm_team`.
  - Already integrated into most backend services/routes.

- Auditing:
  - `audit_logger` records many admin and agent/workflow actions.
  - Some actions still lack systematic DB‑backed audit entries.

- Multi‑tenancy:
  - Workflows:
    - `visibility: personal|team|global`, `owner_user_id`, `owner_team_id`.
    - Enforced in storage + services; tested with multi‑user tests.
  - Agent sessions:
    - Strictly per‑user; tests in `test_session_scoping.py`.

The roadmap below turns this into a **first‑class authorization subsystem** with a stable DB schema and documented behavior.

---

## 2. Phase 1 – Stabilize Auth DB Schema & Migrations (Low–Medium)

**Goal:** Freeze and document the schema for identity/authorization, and introduce proper migrations so it never drifts or gets “auto‑created” in handlers.

### 2.1 Define the canonical schema

Using the existing `api.permissions` and auth code as a starting point, define tables (even if some already exist) such as:

- `auth_users`
  - `id` (PK), `username`, `password_hash`, `salt`, `status` (active/locked), `created_at`, `last_login_at`.
- `auth_teams`
  - `id`, `name`, `description`.
- `auth_roles`
  - `id`, `name`, `description`, `scope` (`global`/`team`), `is_system`.
- `auth_permissions`
  - `id`, `key` (e.g. `code.use`), `description`.
- `auth_role_permissions`
  - `role_id`, `permission_id`, `effect` (`allow`/`deny`).
- `auth_user_roles`
  - `user_id`, `role_id`, `team_id` (nullable when global).
- `auth_sessions`
  - `id`, `user_id`, `created_at`, `expires_at`, `meta_json`.
- `auth_audit_log`
  - `id`, `timestamp`, `user_id`, `action`, `resource`, `details_json`.

Note: not all of these need to be introduced at once if some structures already live elsewhere; the key is to have a **single schema story** rather than scattered tables.

### 2.2 Introduce explicit migrations

Backend:

- Add a small, central migration system for authz:
  - A `schema_migrations` table with:
    - `id`, `applied_at`, `version`, `description`.
  - Migration scripts under something like:
    - `apps/backend/api/migrations/auth/0001_initial.py`, etc.
  - On startup, run pending migrations:
    - Idempotent and transactional.

### 2.3 Document schema

Docs:

- Create `docs/architecture/AUTH_DB_SCHEMA.md`:
  - Explain each table, its fields, and invariants.
  - Note how it interacts with:
    - `api.permissions.storage`
    - `auth routes` and `get_current_user`
    - Workflow visibility and sessions.

Tests:

- Add a simple migration test:
  - Run migrations against an empty DB in CI and ensure:
    - Tables exist.
    - Basic inserts work.

---

## 3. Phase 2 – Normalize Founder Account (Medium)

**Goal:** Make the Founder account a normal row in the auth DB with a special role, not a magical env‑based backdoor.

### 3.1 Represent Founder in the DB

Backend:

- Add a **bootstrap routine** that:
  - Runs at startup.
  - If `ELOHIM_ENV=development` or during initial setup:
    - Ensures there is exactly one Founder user with:
      - `username = ELOHIM_FOUNDER_USERNAME` (default `elohim_founder`).
      - A password based on `ELOHIM_FOUNDER_PASSWORD` (or a guided setup).
    - Assigns a special `founder` role:
      - High‑privilege role with explicit permissions, not “skip all checks.”

- Remove any code paths that:
  - Auto‑bypass RBAC if env is set.
  - Treat Founder as a wholly separate mechanism from roles/permissions.

### 3.2 Initial device setup story

Design:

- First‑run behavior on a new device:
  - Present a **setup wizard** (frontend) that:
    - Creates either:
      - A Founder account **or**
      - An “Owner” admin account (if you want to reserve Founder for special cases).
  - Store this in `auth_users` and `auth_user_roles`.

### 3.3 Dev‑mode defaults

Keep dev easy, but explicit:

- In dev:
  - If no users exist:
    - Auto‑create a Founder user with a known dev password.
    - Log this clearly (“DEV ONLY: Auto‑created Founder account”).

- In prod:
  - Never auto‑create Founder; require explicit setup.

Tests:

- Add tests for:
  - Dev bootstrap creating founder.
  - No bootstrap in prod without explicit configuration.

---

## 4. Phase 3 – Token & Session Hardening (Medium)

**Goal:** Make the token + session story explicit, predictable, and robust across restarts and field use.

### 4.1 Token semantics

Backend:

- Fix and document:
  - Token lifetime (e.g. 7 days absolute, 1 hour idle).
  - What happens on backend restart:
    - If `ELOHIMOS_JWT_SECRET_KEY` is stable, existing tokens remain valid.
    - If secret changes, all tokens are invalidated (document this).

- Ensure all tokens:
  - Include `user_id`, `roles`, and `team_ids` or a way to derive them cheaply.

### 4.2 Session table usage

- Use `auth_sessions` as the canonical record of:
  - Active sessions (token family).
  - Creation/expiry times.
  - Device or client metadata.

- On login:
  - Create `auth_sessions` row.

- On logout / expiry:
  - Mark session as terminated.

### 4.3 Cleanup & resilience

- Add a periodic cleanup (or startup cleanup) that:
  - Deletes expired sessions from `auth_sessions`.

Tests:

- Multi‑login/multi‑user tests to ensure:
  - Tokens are denied after expiry.
  - Sessions are cleaned up.

---

## 5. Phase 4 – RBAC Coverage & Policy Tests (Medium–High)

**Goal:** Ensure every sensitive endpoint and action uses the RBAC engine consistently, and that behavior is covered by tests.

### 5.1 RBAC coverage audit

Backend:

- Systematically scan:
  - `api/routes/*` and service layers for any direct permission logic.
  - Ensure they consistently use `@require_perm` / `@require_perm_team` decorators or centralized checks.

Focus areas:

- Admin/support routes.
- Workflow visibility/management.
- Agent apply operations (auto‑apply in particular).
- Data export/import endpoints.

### 5.2 Policy tests

Add targeted tests that exercise:

- **Roles**:
  - Founder vs normal admin vs engineer vs viewer.
- **Permissions**:
  - User with `workflows.view` but not `workflows.manage`.
  - User with `code.use` but not `code.edit`.
  - Behavior of `@require_perm_team` when user is not in the owner team.

Testing strategy:

- Build a small `auth_test_utils` module to:
  - Seed users/teams/roles/permissions for tests.
  - Generate tokens with appropriate claims.

---

## 6. Phase 5 – Audit Log Coverage & Consistency (Medium–High)

**Goal:** Make audit logging comprehensive and consistent, backed by the auth DB.

### 6.1 Unify audit logging

Backend:

- Standardize on a single audit log helper that:
  - Writes to both:
    - `auth_audit_log` (DB).
    - Existing log sink (e.g. `audit_logger` / file / console).
  - Accepts:
    - `user_id`, `action`, `resource`, `details` (as dict).

### 6.2 Coverage

Ensure audit entries for:

- Admin/support operations:
  - User management, password resets, account unlocks.
  - Role/permission edits.
- Workflow & visibility changes:
  - Creating/deleting workflows.
  - Changing `visibility` (personal → team → global).
- Agent & automation:
  - Agent auto‑apply actions (what changed).
  - Trigger firing and WorkItem creation based on events.

### 6.3 Query & introspection

Optionally add a support/admin endpoint to:

- Query `auth_audit_log` with filters (time range, user, action).
- Export audit logs for offline triage (e.g. JSON or CSV).

Tests:

- Confirm audit records are created for key actions.
- Verify no sensitive secrets are logged (e.g. raw passwords).

---

## 7. Phase 6 – Update Safety & Device Identity ✅ (Complete)

**Goal:** Ensure software updates never accidentally break or reset auth data, and define a safe "device identity" story for the update channel.

**Status:** Complete (2025-11-20)

### 7.1 Update‑safe migrations ✅

**Implementation:**

- Auth migrations integrated into startup via `startup_migrations.py`:
  - Auth migrations run **first** (before other migrations)
  - Migration tracking via shared `migrations` table
  - Each migration checks if already applied before running
  - All migrations use `CREATE TABLE IF NOT EXISTS` for idempotency

**Guidelines followed:**

- ✅ Never drop auth tables without migration path
- ✅ Never auto-reset credentials during updates
- ✅ Migrations are additive and non-destructive
- ✅ Update flow = Normal startup with new migrations

**Files:**
- `api/migrations/auth/runner.py` - Migration orchestration
- `api/migrations/auth/0001_initial.py` - Consolidated auth schema
- `api/migrations/auth/0002_founder_role.py` - Founder role normalization
- `api/migrations/auth/0003_device_identity.py` - Device identity (NEW)

### 7.2 Device identity for update channel ✅

**Implementation:**

- Device identity table created: `device_identity`
  - `device_id` (UUID) - Primary identifier for this machine
  - `machine_id` (hardware-based) - Stable across reboots
  - Persists across user account changes/deletions
  - Tracked: first boot, last boot, platform metadata

- Machine ID generation:
  - Based on: hostname, platform, MAC address, processor
  - Cached to `~/.elohimos/machine_id` for stability
  - Fallback: UUID based on `uuid.getnode()`

- Integration:
  - `ensure_device_identity()` called on every startup
  - Creates device identity if missing
  - Updates `last_boot_at` on each boot

**Security:**

- ✅ Device identity separate from user accounts
- ✅ No user credentials in device identity
- ✅ Stable machine identification for future update server

**Files:**
- `api/device_identity.py` - Device identity helpers
- `api/startup_migrations.py` - Calls `ensure_device_identity()` on startup

### 7.3 Tests ✅

**Test suite:** `tests/test_auth_update_safety.py` (7 tests)

**Coverage:**
1. ✅ `test_existing_user_survives_migration` - User data preserved across migrations
2. ✅ `test_all_auth_migrations_preserve_users` - Complete migration path preserves users
3. ✅ `test_device_identity_is_stable` - Device ID stable across restarts
4. ✅ `test_device_identity_persists_after_user_deletion` - Independent of user accounts
5. ✅ `test_migrations_are_idempotent` - Safe to run multiple times
6. ✅ `test_device_identity_migration_is_idempotent` - Migration 0003 idempotent
7. ✅ `test_complete_update_flow` - Full update simulation (old → new schema)

**Results:** All 7 tests passing

**Documentation:**
- `docs/architecture/AUTH_DB_SCHEMA.md` - Updated with device_identity table
- `docs/roadmap/AUTHORIZATION_SYSTEM_ROADMAP.md` - This file

---

## 8. Suggested Implementation Order

From easiest/lowest risk to most complex:

1. **Phase 1 – Auth DB schema + migrations**
   - Low risk.
   - Unblocks all later work.

2. **Phase 2 – Normalize Founder account**
   - Clarifies identity model.
   - Makes dev/prod behavior explicit.

3. **Phase 3 – Token & session hardening**
   - Improves reliability in the field.

4. **Phase 4 – RBAC coverage & tests**
   - Locks in secure behavior for multi‑user devices.

5. **Phase 5 – Audit log coverage**
   - Gives you traceability when things go wrong.

6. **Phase 6 – Update safety & device identity**
   - Ties everything into your “tiny update server” story.

At each phase:

- Keep behavior **backwards compatible** where possible.
- Extend **E2E smoke tests** to cover the new auth behaviors.
- Update docs (`AUTH_DB_SCHEMA.md`, `AGENT_WORKFLOW_USER_GUIDE.md`, and CI docs) so the mental model stays aligned with the implementation.

