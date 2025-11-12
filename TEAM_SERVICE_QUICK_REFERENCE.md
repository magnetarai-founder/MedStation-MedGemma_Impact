# Team Service Migration - Quick Reference

## File Structure Overview

### Current State
```
apps/backend/api/team_service.py (5,145 lines)
├── Imports & Config (40 lines)
├── Pydantic Models (76 models across file)
├── Helper Functions (3 functions)
├── TeamManager Class (60+ methods across 2,800 lines)
└── API Endpoints (50+ routes across remaining lines)
```

### Target State
```
apps/backend/api/
├── schemas/
│   └── team_models.py (76 Pydantic models)
├── services/
│   └── team.py (TeamManager class + 60+ methods)
└── routes/
    └── team.py (50+ API endpoints)
```

---

## Quick Stats

| Metric | Count |
|--------|-------|
| Pydantic Models | 76 |
| API Endpoints | 50+ |
| TeamManager Methods | 62 |
| Database Tables | 9 existing + 6 new |
| Functional Domains | 8 |
| Lines of Code | 5,145 current |

---

## Functional Domains (8 Areas)

1. **Core Team Management** (7 endpoints)
   - Team CRUD, membership, invitations
   - Models: CreateTeamRequest, TeamResponse, InviteCodeResponse, etc.
   - Methods: create_team(), get_team(), get_team_members(), get_user_teams()

2. **Member Management** (5-6 endpoints)
   - Role changes, member removal, job roles
   - Models: UpdateRoleRequest, UpdateRoleResponse, UpdateJobRoleRequest, etc.
   - Methods: update_member_role(), update_job_role(), get_member_job_role()

3. **Join Team & Invites** (2 endpoints)
   - Invite validation, team joining
   - Models: JoinTeamRequest, JoinTeamResponse
   - Methods: join_team(), validate_invite_code(), record_invite_attempt()
   - Security: rate_limiter (10 req/60s per IP)

4. **Promotion System** (8-10 endpoints)
   - Auto/instant/delayed promotions, offline failsafe
   - Models: AutoPromoteResponse, InstantPromoteRequest, DelayedPromoteRequest, etc.
   - Methods: auto_promote_guests(), instant_promote_guest(), schedule_delayed_promotion(), execute_delayed_promotions()
   - Database: delayed_promotions, temp_promotions tables

5. **Workflow Permissions** (4-5 endpoints)
   - Grant/revoke/check workflow permissions
   - Models: AddWorkflowPermissionRequest, WorkflowPermissionGrant, etc.
   - Methods: add_workflow_permission(), remove_workflow_permission(), check_workflow_permission()
   - Permission types: view, edit, delete, assign
   - Grant types: role, job_role, user

6. **Queue Management** (6-7 endpoints)
   - Create queues, manage access
   - Models: CreateQueueRequest, AddQueuePermissionRequest, etc.
   - Methods: create_queue(), add_queue_permission(), check_queue_access()
   - Queue types: patient, medication, pharmacy, counseling, emergency, custom

7. **God Rights / Founder Rights** (5 endpoints)
   - Highest authority level
   - Models: GrantGodRightsRequest, RevokeGodRightsRequest, etc.
   - Methods: grant_god_rights(), revoke_god_rights(), check_god_rights()

8. **Team Vault** (8-9 endpoints)
   - Encrypted document storage
   - Models: CreateVaultItemRequest, VaultItemInfo, VaultItemDetail, etc.
   - Methods: create_vault_item(), update_vault_item(), delete_vault_item()
   - Encryption: AES with team-specific keys
   - Item types: document, image, file, note, patient_record

---

## Pydantic Models Breakdown

### By Domain
- **Core Team**: 5 models
- **Member Management**: 6 models
- **Promotion System**: 16 models (complex multi-step)
- **Workflow Permissions**: 8 models
- **Queue Management**: 13 models
- **God Rights**: 10 models
- **Team Vault**: 18 models

### Key Model Patterns
- Request/Response pairs (e.g., AddWorkflowPermissionRequest + AddWorkflowPermissionResponse)
- Info/Detail pairs (e.g., QueueInfo + QueueDetails)
- List response wrappers (e.g., ListVaultItemsResponse, TempPromotionsResponse)
- Permission grant types (e.g., WorkflowPermissionGrant, VaultPermissionGrant)

---

## External Dependencies

### permission_engine
- **Import**: `from permission_engine import require_perm, get_permission_engine`
- **Usage**:
  - `@require_perm("system.manage_users")` - system-level team creation
  - `@require_perm("team.use")` - most team operations
  - `get_permission_engine().invalidate_user_permissions(user_id)` - after role changes
- **Recommendation**: Keep as eager import (decorator usage requires it)

### audit_logger
- **Import**: `from audit_logger import audit_log_sync, AuditAction`
- **Usage**:
  - Team creation: AuditAction.USER_CREATED
  - Invite creation: "team.invite.created"
  - Role changes: "team.member.role.changed"
  - Member removal: "team.member.removed"
  - Team join: "team.member.joined"
- **Recommendation**: Keep as eager import (frequent usage)

### rate_limiter
- **Import**: `from rate_limiter import rate_limiter, get_client_ip`
- **Usage**:
  - `rate_limiter.check_rate_limit(f"team:join:{client_ip}", max_requests=10, window_seconds=60)`
  - Brute-force protection on invite code validation
  - IP extraction: `get_client_ip(request)`
- **Recommendation**: Keep as eager import (decorator usage patterns)

### All 3 imports should remain at module level - no lazy import candidates

---

## Database Schema Changes

### Tables to Create (6 new)
1. **workflow_permissions**
   - workflow_id, team_id, permission_type, grant_type, grant_value, created_by, created_at

2. **queues**
   - queue_id, team_id, queue_name, queue_type, description, created_by, created_at

3. **queue_permissions**
   - queue_id, team_id, access_type, grant_type, grant_value, created_by, created_at

4. **god_rights**
   - user_id, granted_at, granted_by, revoked_at, revoked_by, is_active, notes

5. **vault_items**
   - item_id, team_id, item_name, item_type, encrypted_content, encryption_algorithm, mime_type, file_size, metadata, created_by, created_at, updated_by, updated_at

6. **vault_permissions**
   - item_id, team_id, permission_type, grant_type, grant_value, created_by, created_at

### Existing Tables (already in place)
1. teams
2. team_members (with role, job_role, last_seen for failsafe)
3. invite_codes
4. team_invites
5. invite_attempts (brute-force tracking)
6. delayed_promotions (21-day scheduling)
7. temp_promotions (offline failsafe)

---

## TeamManager Methods by Category

### Core Operations (5)
- generate_team_id()
- create_team()
- get_team()
- get_team_members()
- get_user_teams()

### Invite Management (6)
- generate_invite_code()
- get_active_invite_code()
- regenerate_invite_code()
- validate_invite_code()
- record_invite_attempt()
- check_brute_force_lockout()

### Member Joining (1)
- join_team()

### Role Management (6)
- count_role()
- count_super_admins()
- get_team_size()
- get_max_super_admins()
- can_promote_to_super_admin()
- update_member_role()

### Guest Promotion (3)
- get_days_since_joined()
- check_auto_promotion_eligibility()
- auto_promote_guests()

### Instant/Delayed Promotions (3)
- instant_promote_guest()
- schedule_delayed_promotion()
- execute_delayed_promotions()

### Admin Failsafe (6)
- update_last_seen()
- check_super_admin_offline()
- promote_admin_temporarily()
- get_pending_temp_promotions()
- approve_temp_promotion()
- revert_temp_promotion()

### Job Roles (2)
- update_job_role()
- get_member_job_role()

### Workflow Permissions (5)
- add_workflow_permission()
- remove_workflow_permission()
- check_workflow_permission()
- get_workflow_permissions()
- _check_default_permission()

### Queue Management (8)
- create_queue()
- add_queue_permission()
- remove_queue_permission()
- check_queue_access()
- _check_default_queue_access()
- get_accessible_queues()
- get_queue_permissions()
- get_queue()

### God Rights (5)
- grant_god_rights()
- revoke_god_rights()
- check_god_rights()
- get_god_rights_users()
- get_revoked_god_rights()

### Vault Operations (9)
- _get_vault_encryption_key()
- _encrypt_content()
- _decrypt_content()
- create_vault_item()
- update_vault_item()
- delete_vault_item()
- get_vault_item()
- list_vault_items()
- add_vault_permission()
- remove_vault_permission()
- check_vault_permission()
- get_vault_permissions()

---

## Migration Complexity Levels

### Low (Straightforward extraction)
- Core team CRUD operations
- Basic member management
- Job role management

### Medium (Some logic refactoring)
- Invite code validation with brute-force protection
- Workflow permission checking logic
- Queue access control logic
- Vault encryption/decryption helpers

### High (Complex multi-step processes)
- Guest auto-promotion with eligibility checks
- Instant promotion with auth validation
- Delayed promotions with scheduled execution
- Admin offline failsafe with temporary promotions
- Permission checking with default fallbacks

---

## Implementation Order Recommendation

1. **Create api/schemas/team_models.py**
   - Extract all 76 Pydantic models
   - Organize into 8 logical groups
   - Add model docstrings

2. **Create api/services/team.py**
   - Move TeamManager class
   - Move all 62 methods
   - Keep eager imports for permission_engine, audit_logger, rate_limiter

3. **Create api/routes/team.py**
   - Extract all 50+ endpoints
   - Organize into 8 functional area sections
   - Make endpoints thin (validation + service call + response)

4. **Update imports**
   - main.py or api/__init__.py includes new router
   - Verify all imports resolve correctly

5. **Test**
   - Unit test service layer
   - Integration test endpoints
   - Verify database schema changes

---

## Key Considerations

### Database Migrations Needed
- 6 new tables required for workflow, queue, god_rights, vault features
- Migration script should create tables with proper indexes
- Consider data migration for any existing records

### Encryption Implementation
- Vault items use AES encryption with team-specific keys
- Key derivation: `_get_vault_encryption_key(team_id)`
- Content encryption: `_encrypt_content(content, team_id)` -> (encrypted_blob, algorithm)
- Content decryption: `_decrypt_content(encrypted_content, team_id)` -> plaintext
- Storage: encrypted_content and encryption_algorithm in vault_items table

### Permission System Integration
- @require_perm decorators must stay at route level
- get_permission_engine().invalidate_user_permissions() called after mutations
- Default permission checks in service methods for workflows and queues

### Audit Logging Integration
- audit_log_sync() called for all mutations
- Actions: team.created, invite.created, member.role.changed, member.removed, member.joined
- Details include: resource_id, resource type, change metadata

### Rate Limiting
- Team join endpoint has 10 requests per 60 seconds per IP
- Brute-force tracking on invite_attempts table
- Lockout logic checks attempt history

---

## File Sizes (Estimates)

| File | Estimated LOC |
|------|---------|
| Current team_service.py | 5,145 |
| New schemas/team_models.py | 500-600 |
| New services/team.py | 2,000-2,500 |
| New routes/team.py | 1,500-2,000 |
| **Total after split** | ~4,000-5,100 |
| Lines saved by organization | ~100-200 |

The split improves readability more than reducing lines, as each file has a clear purpose.

