# ElohimOS Permission Model

**Version**: 1.0
**Last Updated**: 2025-11-12
**Based on**: `apps/backend/api/permission_engine.py`

## Overview

ElohimOS uses a **Salesforce-style RBAC (Role-Based Access Control)** permission engine with:

- **Role-based baselines** (founder_rights, super_admin, admin, member, guest)
- **Permission profiles** (reusable role-based permission bundles)
- **Permission sets** (ad-hoc grants for specific users)
- **Team-aware permissions** (local-only vs team-scoped)
- **Founder Rights bypass** (complete override for founders)
- **In-memory caching** with invalidation for performance

---

## Architecture

### Core Concepts

#### 1. **Roles** (Base Permission Level)

| Role | Description | Baseline Access |
|------|-------------|-----------------|
| `founder_rights` | Founder(s) only - complete bypass | ALL (bypasses all checks) |
| `super_admin` | Default for all users (local-only) | Full local access + limited admin panel |
| `admin` | Team administrator | Most features, limited system perms |
| `member` | Regular team member | Core features (chat, vault, workflows, docs) |
| `guest` | Read-only access | View-only permissions |

#### 2. **Permission Types**

1. **Boolean Permissions**: Simple true/false (e.g., `chat.use`, `vault.use`)
2. **Level Permissions**: Hierarchical access (NONE → READ → WRITE → ADMIN)
3. **Scope Permissions**: JSON-based scoped access (future expansion)

#### 3. **Permission Resolution Order**

1. **Founder Rights Check**: If `role == 'founder_rights'` → ALLOW (bypass all)
2. **Role Baseline**: Default permissions for the role
3. **Permission Profiles**: Reusable permission bundles (applied to user)
4. **Permission Sets**: Ad-hoc grants (override profiles)

**Merge Strategy**: Later wins (Permission Sets > Profiles > Role Baseline)

---

## Permission Keys

All permission keys use **neutral naming** (no "team." prefix). Team scoping is applied at check time via `require_perm_team()`.

### Feature Permissions (Boolean)

```json
{
  "chat.use": true,              // Access to chat/AI features
  "vault.use": true,             // Access to vault/secure storage
  "workflows.use": true,         // Access to workflow automation
  "docs.use": true,              // Access to document management
  "data.run_sql": true,          // Execute SQL queries
  "data.export": true,           // Export data
  "insights.use": true,          // Access to analytics/insights
  "code.use": true,              // Access to code editor
  "team.use": true,              // Access to team features
  "panic.use": true,             // Emergency panic mode
  "backups.use": false           // System backups (restricted)
}
```

### Resource Permissions (Level-based)

Level hierarchy: `NONE` (0) → `READ` (1) → `WRITE` (2) → `ADMIN` (3)

```json
{
  // Vault Resources
  "vault.documents.create": "write",
  "vault.documents.read": "admin",
  "vault.documents.update": "write",
  "vault.documents.delete": "admin",
  "vault.documents.share": "read",

  // Workflow Resources
  "workflows.create": "write",
  "workflows.view": "read",
  "workflows.edit": "write",
  "workflows.delete": "admin",
  "workflows.manage": "admin",

  // Document Resources
  "docs.create": "write",
  "docs.read": "admin",
  "docs.update": "write",
  "docs.delete": "admin",
  "docs.share": "read"
}
```

### System Permissions (Boolean)

```json
{
  "system.view_admin_dashboard": true,   // View admin dashboard
  "system.manage_users": true,           // Manage users
  "system.view_audit_logs": true,        // View audit logs
  "system.manage_permissions": true,     // Manage permissions
  "system.manage_settings": true         // Manage system settings
}
```

---

## Role Baselines

### Founder Rights (`founder_rights`)

**Special Handling**: BYPASSES ALL PERMISSION CHECKS

- Identified by `role == 'founder_rights'` in permission engine
- Requires `ELOHIM_FOUNDER_PASSWORD` authentication
- Not a static user list - role-based bypass
- Can access EVERYTHING (all local + all teams)

**Implementation**:
```python
# permission_engine.py
if user_ctx.role == 'founder_rights':
    return True  # bypass all checks
```

### Super Admin (`super_admin`)

**Default role for all users in local-only mode**

**Access**:
- ✅ All features (chat, vault, workflows, docs, SQL, export, insights, code, team, panic)
- ✅ Full control over local resources (ADMIN level)
- ✅ Limited admin panel (view dashboard, manage users/settings)
- ❌ Cannot manage permissions by default (requires grant)
- ❌ Cannot access team resources (unless in team context)

**Baseline Permissions**:
```json
{
  "chat.use": true,
  "vault.use": true,
  "workflows.use": true,
  "docs.use": true,
  "data.run_sql": true,
  "data.export": true,
  "insights.use": true,
  "code.use": true,
  "team.use": true,
  "panic.use": true,
  "backups.use": true,
  "vault.documents.create": "admin",
  "vault.documents.read": "admin",
  "vault.documents.update": "admin",
  "vault.documents.delete": "admin",
  "vault.documents.share": "admin",
  "workflows.create": "admin",
  "workflows.view": "admin",
  "workflows.edit": "admin",
  "workflows.delete": "admin",
  "workflows.manage": "admin",
  "docs.create": "admin",
  "docs.read": "admin",
  "docs.update": "admin",
  "docs.delete": "admin",
  "docs.share": "admin",
  "system.view_admin_dashboard": true,
  "system.manage_users": true,
  "system.view_audit_logs": true,
  "system.manage_permissions": true,
  "system.manage_settings": true
}
```

### Admin (`admin`)

**Team administrator with most permissions**

**Access**:
- ✅ Most features (chat, vault, workflows, docs, SQL, export, insights, code, team, panic)
- ✅ Write-level resource access (can create, edit, view)
- ✅ Limited admin dashboard
- ❌ Backups require explicit grant
- ❌ Delete/share permissions limited to READ

**Baseline Permissions**:
```json
{
  "chat.use": true,
  "vault.use": true,
  "workflows.use": true,
  "docs.use": true,
  "data.run_sql": true,
  "data.export": true,
  "insights.use": true,
  "code.use": true,
  "team.use": true,
  "panic.use": true,
  "backups.use": false,
  "vault.documents.create": "write",
  "vault.documents.read": "write",
  "vault.documents.update": "write",
  "vault.documents.delete": "write",
  "vault.documents.share": "read",
  "workflows.create": "write",
  "workflows.view": "write",
  "workflows.edit": "write",
  "workflows.delete": "write",
  "workflows.manage": "write",
  "docs.create": "write",
  "docs.read": "write",
  "docs.update": "write",
  "docs.delete": "write",
  "docs.share": "read",
  "system.view_admin_dashboard": true,
  "system.manage_users": false,
  "system.view_audit_logs": true,
  "system.manage_permissions": false,
  "system.manage_settings": false
}
```

### Member (`member`)

**Regular team member with core access**

**Access**:
- ✅ Core features (chat, vault, workflows, docs)
- ✅ Read-level resource access
- ❌ No system permissions
- ❌ Cannot manage team

**Baseline Permissions**:
```json
{
  "chat.use": true,
  "vault.use": true,
  "workflows.use": true,
  "docs.use": true,
  "data.run_sql": false,
  "data.export": false,
  "insights.use": false,
  "code.use": false,
  "team.use": false,
  "panic.use": false,
  "backups.use": false,
  "vault.documents.create": "none",
  "vault.documents.read": "read",
  "vault.documents.update": "none",
  "vault.documents.delete": "none",
  "vault.documents.share": "none",
  "workflows.create": "none",
  "workflows.view": "read",
  "workflows.edit": "none",
  "workflows.delete": "none",
  "workflows.manage": "none",
  "docs.create": "none",
  "docs.read": "read",
  "docs.update": "none",
  "docs.delete": "none",
  "docs.share": "none",
  "system.view_admin_dashboard": false,
  "system.manage_users": false,
  "system.view_audit_logs": false,
  "system.manage_permissions": false,
  "system.manage_settings": false
}
```

### Guest (`guest`)

**Read-only access to shared resources**

**Access**:
- ✅ View-only access to shared content
- ❌ Cannot create, edit, or delete
- ❌ No system permissions

**Baseline Permissions**:
```json
{
  "chat.use": false,
  "vault.use": false,
  "workflows.use": false,
  "docs.use": true,
  "data.run_sql": false,
  "data.export": false,
  "insights.use": false,
  "code.use": false,
  "team.use": false,
  "panic.use": false,
  "backups.use": false,
  "vault.documents.create": "none",
  "vault.documents.read": "read",
  "vault.documents.update": "none",
  "vault.documents.delete": "none",
  "vault.documents.share": "none",
  "workflows.create": "none",
  "workflows.view": "read",
  "workflows.edit": "none",
  "workflows.delete": "none",
  "workflows.manage": "none",
  "docs.create": "none",
  "docs.read": "read",
  "docs.update": "none",
  "docs.delete": "none",
  "docs.share": "none",
  "system.view_admin_dashboard": false,
  "system.manage_users": false,
  "system.view_audit_logs": false,
  "system.manage_permissions": false,
  "system.manage_settings": false
}
```

---

## Team-Aware Permissions

### Context Switching (Solo ↔ Team)

**Solo Mode** (Local-Only):
- No permissions checks (local resources)
- User has full control over their own data
- Role baseline applies (usually `super_admin`)

**Team Mode** (Team-Scoped):
- RBAC applies (permissions checked)
- Resources filtered by `team_id`
- Role + profiles + permission sets determine access

### Team-Aware Permission Checks

Permission keys are **neutral** (e.g., `docs.read`, not `team.docs.read`). Team context is applied at check time:

**Decorator Usage**:
```python
from api.permission_engine import require_perm_team

@router.post("/teams/{team_id}/documents")
@require_perm_team("docs.create", level="write", team_kw="team_id")
async def create_team_document(
    team_id: str,
    doc: DocumentCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new team document (requires docs.create at write level)"""
    # Permission already checked by decorator
    # team_id ensures user has this permission in THIS team
    ...
```

**How Team Context Works**:
1. User requests access to team resource with `team_id`
2. Permission engine loads user context **for that team**
3. Filters profiles/permission sets by team scope
4. Evaluates permission in team context
5. Allows/denies based on resolved permissions

---

## Permission Caching

**Phase 2.5 Feature**: In-memory caching with invalidation

**Cache Key**: `{user_id}:{team_id}` (team_id can be `None` for local-only)

**Cache Invalidation**:
```python
# Invalidate user's cache when permissions change
permission_engine.invalidate_cache(user_id, team_id=None)  # All teams
permission_engine.invalidate_cache(user_id, team_id="team_123")  # Specific team
```

**Performance**:
- ~100x faster for cached lookups
- Automatic invalidation on permission changes

---

## Diagnostics

**Enable Diagnostics**:
```bash
export ELOHIMOS_PERMS_EXPLAIN=1
```

**What It Shows**:
- Permission check decisions (allow/deny)
- Reason for decision (founder bypass, role baseline, profile grant, etc.)
- Effective permission value
- Cache hit/miss

**Example Log**:
```
[PERMS] user_123 → docs.read in team_456: ALLOWED (level: admin)
        Reason: Super Admin baseline + Profile "Content Manager" grant
        Cache: HIT
```

---

## Database Schema

### Tables

1. **`permissions`**: Registry of all available permissions
   - `permission_id`, `permission_key`, `permission_type`, `description`

2. **`permission_profiles`**: Reusable permission bundles
   - `profile_id`, `profile_name`, `description`, `is_active`

3. **`profile_permissions`**: Grants for profiles
   - `profile_id`, `permission_id`, `is_granted`, `permission_level`, `permission_scope`

4. **`permission_sets`**: Ad-hoc permission grants
   - `permission_set_id`, `set_name`, `description`

5. **`permission_set_permissions`**: Grants for permission sets
   - `permission_set_id`, `permission_id`, `is_granted`, `permission_level`, `permission_scope`

6. **`user_permission_profiles`**: User-to-profile assignments
   - `user_id`, `profile_id`, `team_id`, `assigned_at`

7. **`user_permission_sets`**: User-to-permission-set assignments
   - `user_id`, `permission_set_id`, `team_id`, `assigned_at`

---

## Usage Examples

### 1. Check Boolean Permission

```python
from api.permission_engine import get_permission_engine

engine = get_permission_engine()
user_ctx = engine.load_user_context(user_id="user_123", team_id=None)

# Check if user can use chat
can_chat = engine.has_permission(user_ctx, "chat.use")
```

### 2. Check Level Permission

```python
# Check if user has WRITE access to docs
has_write = engine.has_permission(user_ctx, "docs.create", level="write")
```

### 3. Use Decorator in FastAPI Route

```python
from fastapi import APIRouter, Depends
from api.permission_engine import require_perm_team

router = APIRouter()

@router.post("/documents")
@require_perm_team("docs.create", level="write")
async def create_document(
    doc: DocumentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a document (requires docs.create at write level)"""
    # Permission already checked
    ...
```

### 4. Founder Rights Bypass

```python
# Founder authentication (requires ELOHIM_FOUNDER_PASSWORD)
user_ctx = engine.load_user_context(user_id="founder_user")

# All permission checks return True
assert engine.has_permission(user_ctx, "any.permission") == True
```

---

## Migration Notes

### From Static Lists to Role-Based

**Before** (Phase 0):
```python
FOUNDERS = ["user_123", "user_456"]  # Static list
if user_id in FOUNDERS:
    return True
```

**After** (Current):
```python
if user_ctx.role == 'founder_rights':
    return True  # Role-based bypass
```

### Adding New Permissions

1. **Register permission**:
   ```sql
   INSERT INTO permissions (permission_id, permission_key, permission_type, description)
   VALUES ('perm_new_feature', 'new_feature.use', 'boolean', 'Access to new feature');
   ```

2. **Add to role baselines** (if default):
   ```python
   # In permission_engine.py → _get_role_baseline()
   if role == 'super_admin':
       return {
           ...
           'new_feature.use': True,
       }
   ```

3. **Grant via profile/permission set** (if restricted):
   ```sql
   INSERT INTO profile_permissions (profile_id, permission_id, is_granted)
   VALUES ('profile_power_user', 'perm_new_feature', 1);
   ```

---

## Troubleshooting

### User Can't Access Feature

1. **Check role baseline**: Does the role have this permission by default?
2. **Check profiles**: Are they assigned the right profile?
3. **Check permission sets**: Do they have an override grant/deny?
4. **Check team context**: Are they in the right team?
5. **Enable diagnostics**: `ELOHIMOS_PERMS_EXPLAIN=1` to see decision path

### Permission Changes Not Taking Effect

1. **Invalidate cache**:
   ```python
   engine.invalidate_cache(user_id, team_id=None)  # All teams
   ```

2. **Check database**: Did the profile/permission set update persist?

3. **Restart app** (cache will rebuild)

---

## Security Considerations

1. **Founder Password**: `ELOHIM_FOUNDER_PASSWORD` must be set in production (no default)
2. **Super Admin Baseline**: Currently grants many permissions - may be restricted in future phases
3. **Cache Invalidation**: Always invalidate after permission changes
4. **Team Scoping**: Ensure team_id is passed correctly to prevent cross-team access
5. **Audit Logging**: All permission checks are logged (when diagnostics enabled)

---

## Future Enhancements

- **Scope-based permissions**: Fine-grained access control (e.g., folder-level, document-level)
- **Permission inheritance**: Team → sub-team → user cascading
- **Time-based grants**: Temporary permission elevation
- **Approval workflows**: Request → approve → grant flow
- **UI for permission management**: Admin panel for assigning profiles/permission sets

---

## References

- **Implementation**: `apps/backend/api/permission_engine.py`
- **Database Schema**: `apps/backend/api/database/schema_migrations.sql`
- **Roadmap**: `/Users/indiedevhipps/Desktop/ELOHIMOS_FOUNDATION_ROADMAP.md`
- **Configuration**: `config_paths.py` (data_dir/elohimos_app.db)
