# Team Service Migration Plan - Comprehensive Analysis

## Executive Summary
The `team_service.py` file is 5,145 lines containing a monolithic module with:
- **61 Pydantic models** (request/response schemas)
- **1 main class**: `TeamManager` with 60+ business logic methods
- **50+ API endpoints** organized as a single router
- **3 major external dependencies**: permission_engine, audit_logger, rate_limiter

**Migration Strategy**: Decompose into three separate modules organized by functional domain.

---

## Part 1: Pydantic Models (61 Total)

### Group A: Core Team Management (5 models)
```
1. CreateTeamRequest(BaseModel)
   - name: str
   - description: Optional[str]
   - creator_user_id: str

2. TeamResponse(BaseModel)
   - team_id: str
   - name: str
   - description: Optional[str]
   - created_at: str
   - created_by: str
   - invite_code: str

3. InviteCodeResponse(BaseModel)
   - code: str
   - team_id: str
   - expires_at: Optional[str]

4. InviteRequest(BaseModel)
   - email_or_username: str
   - role: str

5. JoinTeamRequest(BaseModel)
   - (needs verification from file)

6. JoinTeamResponse(BaseModel)
   - (needs verification from file)
```

### Group B: Member Management & Role Changes (6 models)
```
7. ChangeRoleBody(BaseModel)
   - role: str

8. UpdateRoleRequest(BaseModel)
   - new_role: str
   - requesting_user_role: Optional[str]
   - requesting_user_id: Optional[str]

9. UpdateRoleResponse(BaseModel)
   - success: bool
   - message: str
   - user_id: str
   - team_id: str
   - new_role: str

10. UpdateJobRoleRequest(BaseModel)
    - (job_role assignment)

11. UpdateJobRoleResponse(BaseModel)
    - (confirmation response)

12. JobRoleResponse(BaseModel)
    - (job_role retrieval)
```

### Group C: Promotion & Temporary Admin Management (10 models)
```
13. AutoPromoteResponse(BaseModel)
    - promoted_users: List[Dict]
    - total_promoted: int

14. InstantPromoteRequest(BaseModel)
    - (immediate promotion request)

15. InstantPromoteResponse(BaseModel)
    - (promotion confirmation)

16. DelayedPromoteRequest(BaseModel)
    - (21-day delayed promotion)

17. DelayedPromoteResponse(BaseModel)
    - (scheduling confirmation)

18. ExecuteDelayedResponse(BaseModel)
    - (execution results)

19. HeartbeatRequest(BaseModel)
    - (super admin status check)

20. HeartbeatResponse(BaseModel)
    - (online status update)

21. OfflineSuperAdminsResponse(BaseModel)
    - (list of offline admins)

22. PromoteTempAdminRequest(BaseModel)
    - (temporary promotion during failsafe)

23. PromoteTempAdminResponse(BaseModel)
    - (confirmation)

24. TempPromotionsResponse(BaseModel)
    - (list of pending temp promotions)

25. ApproveTempPromotionRequest(BaseModel)
    - (approve scheduled promotion)

26. ApproveTempPromotionResponse(BaseModel)
    - (approval confirmation)

27. RevertTempPromotionRequest(BaseModel)
    - (revert temp promotion)

28. RevertTempPromotionResponse(BaseModel)
    - (revert confirmation)
```

### Group D: Workflow Permissions (7 models)
```
29. AddWorkflowPermissionRequest(BaseModel)
    - permission_type: str  # view, edit, delete, assign
    - grant_type: str       # role, job_role, user
    - grant_value: str
    - created_by: str

30. AddWorkflowPermissionResponse(BaseModel)
    - success: bool
    - message: str
    - workflow_id: str
    - permission_type: str
    - grant_type: str
    - grant_value: str

31. RemoveWorkflowPermissionRequest(BaseModel)
    - permission_type: str
    - grant_type: str
    - grant_value: str

32. RemoveWorkflowPermissionResponse(BaseModel)
    - success: bool
    - message: str

33. WorkflowPermissionGrant(BaseModel)
    - (permission grant detail)

34. GetWorkflowPermissionsResponse(BaseModel)
    - (list of permissions)

35. CheckWorkflowPermissionRequest(BaseModel)
    - (permission check request)

36. CheckWorkflowPermissionResponse(BaseModel)
    - (permission check result)
```

### Group E: Queue Management & Permissions (10 models)
```
37. CreateQueueRequest(BaseModel)
    - queue_name: str
    - queue_type: str      # patient, medication, pharmacy, etc.
    - description: str
    - created_by: str

38. CreateQueueResponse(BaseModel)
    - success: bool
    - message: str
    - queue_id: str

39. AddQueuePermissionRequest(BaseModel)
    - access_type: str     # view, manage, assign
    - grant_type: str      # role, job_role, user
    - grant_value: str
    - created_by: str

40. AddQueuePermissionResponse(BaseModel)
    - success: bool
    - message: str
    - queue_id: str
    - access_type: str
    - grant_type: str
    - grant_value: str

41. RemoveQueuePermissionRequest(BaseModel)
    - access_type: str
    - grant_type: str
    - grant_value: str

42. RemoveQueuePermissionResponse(BaseModel)
    - success: bool
    - message: str

43. QueuePermissionGrant(BaseModel)
    - (permission grant detail)

44. GetQueuePermissionsResponse(BaseModel)
    - (list of queue permissions)

45. CheckQueueAccessRequest(BaseModel)
    - (access check request)

46. CheckQueueAccessResponse(BaseModel)
    - (access check result)

47. QueueInfo(BaseModel)
    - (queue summary info)

48. GetAccessibleQueuesResponse(BaseModel)
    - (queues accessible to user)

49. QueueDetails(BaseModel)
    - (full queue details)
```

### Group F: God Rights / Founder Rights (5 models)
```
50. GrantGodRightsRequest(BaseModel)
    - user_id: str
    - delegated_by: Optional[str]
    - auth_key: Optional[str]
    - notes: Optional[str]

51. GrantGodRightsResponse(BaseModel)
    - success: bool
    - message: str

52. RevokeGodRightsRequest(BaseModel)
    - user_id: str
    - revoked_by: str

53. RevokeGodRightsResponse(BaseModel)
    - success: bool
    - message: str

54. CheckGodRightsRequest(BaseModel)
    - (rights check request)

55. CheckGodRightsResponse(BaseModel)
    - (rights check result)

56. GodRightsUser(BaseModel)
    - (user with god rights)

57. GetGodRightsUsersResponse(BaseModel)
    - (list of god rights users)

58. RevokedGodRightsUser(BaseModel)
    - (revoked user detail)

59. GetRevokedGodRightsResponse(BaseModel)
    - (list of revoked god rights users)
```

### Group G: Team Vault (12 models)
```
60. CreateVaultItemRequest(BaseModel)
    - item_name: str
    - item_type: str       # document, image, file, note, patient_record
    - content: str
    - mime_type: Optional[str]
    - metadata: Optional[str]
    - created_by: str

61. CreateVaultItemResponse(BaseModel)
    - success: bool
    - message: str
    - item_id: str

62. VaultItemInfo(BaseModel)
    - item_id: str
    - item_name: str
    - item_type: str
    - file_size: int
    - mime_type: Optional[str]
    - created_at: str
    - created_by: str
    - updated_at: Optional[str]
    - updated_by: Optional[str]
    - metadata: Optional[str]

63. ListVaultItemsResponse(BaseModel)
    - team_id: str
    - user_id: str
    - items: List[VaultItemInfo]
    - count: int

64. VaultItemDetail(BaseModel)
    - (full vault item details)

65. UpdateVaultItemRequest(BaseModel)
    - (update request)

66. UpdateVaultItemResponse(BaseModel)
    - (update confirmation)

67. DeleteVaultItemRequest(BaseModel)
    - (delete request)

68. DeleteVaultItemResponse(BaseModel)
    - (delete confirmation)

69. AddVaultPermissionRequest(BaseModel)
    - permission_type: str
    - grant_type: str
    - grant_value: str
    - created_by: str

70. AddVaultPermissionResponse(BaseModel)
    - success: bool
    - message: str

71. RemoveVaultPermissionRequest(BaseModel)
    - permission_type: str
    - grant_type: str
    - grant_value: str

72. RemoveVaultPermissionResponse(BaseModel)
    - success: bool
    - message: str

73. VaultPermissionGrant(BaseModel)
    - (permission grant detail)

74. GetVaultPermissionsResponse(BaseModel)
    - (list of vault permissions)

75. CheckVaultPermissionRequest(BaseModel)
    - user_id: str
    - permission_type: str

76. CheckVaultPermissionResponse(BaseModel)
    - has_permission: bool
    - reason: str
```

---

## Part 2: Functional Areas & API Endpoints

### Domain 1: Core Team Management (7 endpoints)
**Purpose**: Team CRUD, basic membership, and invitations

**Endpoints**:
1. `POST /` - Create team
   - @require_perm("system.manage_users")
   - Handler: create_team_v3()
   - Service: team_manager.create_team()

2. `GET /{team_id}` - Get team details
   - No permission check
   - Handler: get_team()
   - Service: team_manager.get_team()

3. `GET /{team_id}/members` - List team members
   - @require_perm("team.use")
   - Handler: get_team_members_v3()
   - Service: Custom query in endpoint

4. `POST /{team_id}/invites` - Create invite
   - @require_perm("team.use")
   - Handler: invite_to_team_v3()
   - Service: Custom insert in endpoint
   - Security: require_team_admin() check

5. `POST /invites/{invite_id}/accept` - Accept invite
   - No permission check
   - Handler: (needs verification)
   - Security: rate_limiter.check_rate_limit() with 10 requests/60s

6. `GET /{team_id}/invite-code` - Get current invite code
   - Handler: (needs verification)
   - Service: team_manager.get_active_invite_code()

7. `POST /{team_id}/invite-code/regenerate` - Regenerate invite code
   - Handler: (needs verification)
   - Service: team_manager.regenerate_invite_code()

**Helper Functions**:
- is_team_member(team_id, user_id) -> Optional[str]
  Returns user's role if member
- require_team_admin(team_id, user_id) -> None
  Raises HTTPException(403) if not admin/super_admin
- _get_app_conn() -> sqlite3.Connection
  Gets connection to app_db with row factory

**Database Tables Used**:
- teams
- team_members
- team_invites
- invite_attempts (brute-force protection)

---

### Domain 2: Member Management & Job Roles (5 endpoints)
**Purpose**: Update roles, remove members, manage job titles

**Endpoints**:
1. `PUT /{team_id}/members/{user_id}/role` - Change member role
   - @require_perm("team.use")
   - Handler: change_member_role_v3()
   - Service: Custom UPDATE in endpoint
   - Side effects: get_permission_engine().invalidate_user_permissions()

2. `DELETE /{team_id}/members/{user_id}` - Remove member
   - @require_perm("team.use")
   - Handler: remove_member_v3()
   - Service: Custom DELETE in endpoint
   - Side effects: get_permission_engine().invalidate_user_permissions()

3. `POST /{team_id}/members/{user_id}/role` - Update member role (v2)
   - Handler: update_member_role()
   - Service: team_manager.update_member_role()

4. `POST /{team_id}/members/{user_id}/job-role` - Set job role
   - Handler: (needs verification)
   - Service: team_manager.update_job_role()

5. `GET /{team_id}/members/{user_id}/job-role` - Get job role
   - Handler: (needs verification)
   - Service: team_manager.get_member_job_role()

6. `GET /user/{user_id}/teams` - Get user's teams
   - Handler: get_user_teams()
   - Service: team_manager.get_user_teams()

**Database Tables Used**:
- team_members (role, job_role)

---

### Domain 3: Join Team & Invite Validation (2 endpoints)
**Purpose**: Join via invite code with brute-force protection

**Endpoints**:
1. `POST /join` - Join team via invite code
   - Handler: (join_team_v3 or similar)
   - Service: team_manager.join_team(), team_manager.validate_invite_code()
   - Security: rate_limiter.check_rate_limit(f"team:join:{client_ip}", max=10, window=60s)
   - Side effects: get_permission_engine().invalidate_user_permissions()

2. `POST /create` - Alternative create team endpoint
   - Handler: (needs verification)
   - Service: team_manager.create_team()

**Database Tables Used**:
- invite_codes
- invite_attempts (brute-force tracking)
- team_members (on successful join)

---

### Domain 4: Promotion & Admin Failsafe (8 endpoints)
**Purpose**: Guest->Member->Admin promotions, super admin offline failsafe

**Endpoints**:
1. `POST /{team_id}/members/auto-promote` - Auto-promote guests
   - Handler: auto_promote_guests()
   - Service: team_manager.auto_promote_guests()
   - Logic: Promotes guests who've been members for X days

2. `POST /{team_id}/members/{user_id}/instant-promote` - Instant promotion
   - Handler: (needs verification)
   - Service: team_manager.instant_promote_guest()
   - Security: Requires real password auth

3. `POST /{team_id}/members/{user_id}/delayed-promote` - Schedule 21-day promotion
   - Handler: (needs verification)
   - Service: team_manager.schedule_delayed_promotion()
   - Purpose: Decoy password delay before promotion

4. `POST /delayed-promotions/execute` - Execute pending promotions
   - Handler: (needs verification)
   - Service: team_manager.execute_delayed_promotions()
   - Can be called manually or by background job

5. `POST /{team_id}/members/heartbeat` - Record super admin activity
   - Handler: (needs verification)
   - Service: team_manager.update_last_seen()
   - Purpose: Track super admin online status

6. `GET /{team_id}/super-admins/status` - Check super admin online status
   - Handler: (needs verification)
   - Service: team_manager.check_super_admin_offline()
   - Returns: Admins offline for >5 minutes

7. `POST /{team_id}/promote-temp-admin` - Temporary failsafe promotion
   - Handler: (needs verification)
   - Service: team_manager.promote_admin_temporarily()
   - Purpose: When super admin is offline

8. `GET /{team_id}/temp-promotions` - List pending temp promotions
   - Handler: (needs verification)
   - Service: team_manager.get_pending_temp_promotions()

9. `POST /{team_id}/temp-promotions/{temp_promotion_id}/approve` - Approve temp promotion
   - Handler: (needs verification)
   - Service: team_manager.approve_temp_promotion()

10. `POST /{team_id}/temp-promotions/{temp_promotion_id}/revert` - Revert temp promotion
    - Handler: (needs verification)
    - Service: team_manager.revert_temp_promotion()

**Database Tables Used**:
- team_members (role, joined_at, last_seen)
- delayed_promotions (21-day scheduled promos)
- temp_promotions (offline failsafe promos)

---

### Domain 5: Workflow Permissions (5 endpoints)
**Purpose**: Grant/revoke/check permissions on workflows

**Endpoints**:
1. `POST /{team_id}/workflows/{workflow_id}/permissions` - Add workflow permission
   - Handler: add_workflow_permission()
   - Service: team_manager.add_workflow_permission()
   - Permission types: view, edit, delete, assign
   - Grant types: role, job_role, user

2. `DELETE /{team_id}/workflows/{workflow_id}/permissions` - Remove workflow permission
   - Handler: (needs verification)
   - Service: team_manager.remove_workflow_permission()

3. `GET /{team_id}/workflows/{workflow_id}/permissions` - List workflow permissions
   - Handler: (needs verification)
   - Service: team_manager.get_workflow_permissions()

4. `POST /{team_id}/workflows/{workflow_id}/check-permission` - Check permission
   - Handler: (needs verification)
   - Service: team_manager.check_workflow_permission()
   - Returns: Boolean + reason

**Database Tables Used**:
- workflow_permissions (new table needed)

---

### Domain 6: Queue Management & Access Control (7 endpoints)
**Purpose**: Create queues and manage queue access permissions

**Endpoints**:
1. `POST /{team_id}/queues` - Create queue
   - Handler: create_queue()
   - Service: team_manager.create_queue()
   - Queue types: patient, medication, pharmacy, counseling, emergency, custom

2. `POST /{team_id}/queues/{queue_id}/permissions` - Add queue permission
   - Handler: add_queue_permission()
   - Service: team_manager.add_queue_permission()
   - Access types: view, manage, assign

3. `DELETE /{team_id}/queues/{queue_id}/permissions` - Remove queue permission
   - Handler: (needs verification)
   - Service: team_manager.remove_queue_permission()

4. `GET /{team_id}/queues/{queue_id}/permissions` - List queue permissions
   - Handler: (needs verification)
   - Service: team_manager.get_queue_permissions()

5. `POST /{team_id}/queues/{queue_id}/check-access` - Check queue access
   - Handler: (needs verification)
   - Service: team_manager.check_queue_access()

6. `GET /{team_id}/queues/accessible/{user_id}` - Get accessible queues
   - Handler: (needs verification)
   - Service: team_manager.get_accessible_queues()

7. `GET /{team_id}/queues/{queue_id}` - Get queue details
   - Handler: (needs verification)
   - Service: team_manager.get_queue()

**Database Tables Used**:
- queues (new table needed)
- queue_permissions (new table needed)

---

### Domain 7: God Rights / Founder Rights (5 endpoints)
**Purpose**: Grant/revoke/check highest authority level in ElohimOS

**Endpoints**:
1. `POST /god-rights/grant` - Grant Founder Rights
   - Handler: grant_god_rights()
   - Service: team_manager.grant_god_rights()
   - Security: Can be granted by founder or delegated by existing Founder Rights users
   - Optional: auth_key for additional security

2. `POST /god-rights/revoke` - Revoke Founder Rights
   - Handler: revoke_god_rights()
   - Service: team_manager.revoke_god_rights()
   - Restriction: Only Founder Rights users can revoke

3. `POST /god-rights/check` - Check Founder Rights
   - Handler: (needs verification)
   - Service: team_manager.check_god_rights()

4. `GET /god-rights/users` - List Founder Rights users
   - Handler: (needs verification)
   - Service: team_manager.get_god_rights_users()

5. `GET /god-rights/revoked` - List revoked Founder Rights users
   - Handler: (needs verification)
   - Service: team_manager.get_revoked_god_rights()

**Database Tables Used**:
- god_rights (new table needed)

---

### Domain 8: Team Vault (9 endpoints)
**Purpose**: Encrypted team document storage with permission control

**Endpoints**:
1. `POST /{team_id}/vault/items` - Create vault item
   - Handler: create_vault_item()
   - Service: team_manager.create_vault_item()
   - Item types: document, image, file, note, patient_record
   - Encryption: team_manager._encrypt_content() using team-specific key

2. `GET /{team_id}/vault/items` - List vault items
   - Handler: list_vault_items()
   - Service: team_manager.list_vault_items()
   - Filtering: By item_type, user_id

3. `GET /{team_id}/vault/items/{item_id}` - Get vault item detail
   - Handler: (needs verification)
   - Service: team_manager.get_vault_item()
   - Decryption: team_manager._decrypt_content()

4. `PUT /{team_id}/vault/items/{item_id}` - Update vault item
   - Handler: (needs verification)
   - Service: team_manager.update_vault_item()

5. `DELETE /{team_id}/vault/items/{item_id}` - Delete vault item
   - Handler: (needs verification)
   - Service: team_manager.delete_vault_item()

6. `POST /{team_id}/vault/items/{item_id}/permissions` - Add vault permission
   - Handler: (needs verification)
   - Service: team_manager.add_vault_permission()

7. `DELETE /{team_id}/vault/items/{item_id}/permissions` - Remove vault permission
   - Handler: (needs verification)
   - Service: team_manager.remove_vault_permission()

8. `GET /{team_id}/vault/items/{item_id}/permissions` - List vault permissions
   - Handler: (needs verification)
   - Service: team_manager.get_vault_permissions()

9. `POST /{team_id}/vault/items/{item_id}/check-permission` - Check vault permission
   - Handler: check_vault_permission()
   - Service: team_manager.check_vault_permission()

**Database Tables Used**:
- vault_items (new table needed)
- vault_permissions (new table needed)

**Encryption Support**:
- team_manager._get_vault_encryption_key(team_id) -> bytes
- team_manager._encrypt_content(content, team_id) -> (encrypted, algorithm)
- team_manager._decrypt_content(encrypted_content, team_id) -> str

---

## Part 3: TeamManager Service Methods (60+ methods)

### Organizational Structure by Functional Area

#### Core Team Operations (4 methods)
1. generate_team_id(team_name) -> str
2. create_team(name, creator_user_id, description) -> Dict
3. get_team(team_id) -> Optional[Dict]
4. get_team_members(team_id) -> List[Dict]
5. get_user_teams(user_id) -> List[Dict]

#### Invite Code Management (5 methods)
6. generate_invite_code(team_id, expires_days) -> str
7. get_active_invite_code(team_id) -> Optional[str]
8. regenerate_invite_code(team_id, expires_days) -> str
9. validate_invite_code(invite_code, ip_address) -> Optional[str]
10. record_invite_attempt(invite_code, ip_address, success)
11. check_brute_force_lockout(invite_code, ip_address) -> bool

#### Member Joining (1 method)
12. join_team(team_id, user_id, role) -> bool

#### Role Management & Validation (5 methods)
13. count_role(team_id, role) -> int
14. count_super_admins(team_id) -> int
15. get_team_size(team_id) -> int
16. get_max_super_admins(team_size) -> int [static]
17. can_promote_to_super_admin(team_id, requesting_user_role) -> tuple[bool, str]
18. update_member_role(team_id, user_id, new_role, ...) -> tuple[bool, str]

#### Guest->Member Auto-Promotion (3 methods)
19. get_days_since_joined(team_id, user_id) -> Optional[int]
20. check_auto_promotion_eligibility(team_id, user_id, required_days) -> tuple[bool, str, int]
21. auto_promote_guests(team_id, required_days) -> List[Dict]

#### Instant & Delayed Promotions (3 methods)
22. instant_promote_guest(team_id, user_id, approved_by_user_id, auth_type) -> tuple[bool, str]
23. schedule_delayed_promotion(team_id, user_id, delay_days, ...) -> tuple[bool, str]
24. execute_delayed_promotions(team_id) -> List[Dict]

#### Admin Offline Failsafe (4 methods)
25. update_last_seen(team_id, user_id) -> tuple[bool, str]
26. check_super_admin_offline(team_id, offline_threshold_minutes) -> List[Dict]
27. promote_admin_temporarily(team_id, offline_super_admin_id, ...) -> tuple[bool, str]
28. get_pending_temp_promotions(team_id) -> List[Dict]
29. approve_temp_promotion(team_id, temp_promotion_id, approved_by) -> tuple[bool, str]
30. revert_temp_promotion(team_id, temp_promotion_id, reverted_by) -> tuple[bool, str]

#### Job Role Management (2 methods)
31. update_job_role(team_id, user_id, job_role) -> tuple[bool, str]
32. get_member_job_role(team_id, user_id) -> Optional[str]

#### Workflow Permissions (4 methods)
33. add_workflow_permission(workflow_id, team_id, permission_type, grant_type, grant_value, created_by) -> tuple[bool, str]
34. remove_workflow_permission(workflow_id, team_id, permission_type, grant_type, grant_value) -> tuple[bool, str]
35. check_workflow_permission(workflow_id, team_id, user_id, permission_type) -> tuple[bool, str]
36. get_workflow_permissions(workflow_id, team_id) -> List[Dict]
37. _check_default_permission(user_role, permission_type) -> tuple[bool, str]

#### Queue Management (7 methods)
38. create_queue(team_id, queue_name, queue_type, description, created_by) -> tuple[bool, str, str]
39. add_queue_permission(queue_id, team_id, access_type, grant_type, grant_value, created_by) -> tuple[bool, str]
40. remove_queue_permission(queue_id, team_id, access_type, grant_type, grant_value) -> tuple[bool, str]
41. check_queue_access(queue_id, team_id, user_id, access_type) -> tuple[bool, str]
42. _check_default_queue_access(user_role, access_type) -> tuple[bool, str]
43. get_accessible_queues(team_id, user_id, access_type) -> List[Dict]
44. get_queue_permissions(queue_id, team_id) -> List[Dict]
45. get_queue(queue_id, team_id) -> Optional[Dict]

#### God Rights / Founder Rights (5 methods)
46. grant_god_rights(user_id, delegated_by, auth_key, notes) -> tuple[bool, str]
47. revoke_god_rights(user_id, revoked_by) -> tuple[bool, str]
48. check_god_rights(user_id) -> tuple[bool, str]
49. get_god_rights_users() -> List[Dict]
50. get_revoked_god_rights() -> List[Dict]

#### Vault Operations (9 methods)
51. _get_vault_encryption_key(team_id) -> bytes
52. _encrypt_content(content, team_id) -> tuple[str, str]
53. _decrypt_content(encrypted_content, team_id) -> str
54. create_vault_item(team_id, item_name, item_type, content, created_by, ...) -> tuple[bool, str, str]
55. update_vault_item(item_id, team_id, item_name, content, updated_by, ...) -> tuple[bool, str]
56. delete_vault_item(item_id, team_id) -> tuple[bool, str]
57. get_vault_item(item_id, team_id) -> Optional[Dict]
58. list_vault_items(team_id, user_id, item_type) -> List[Dict]
59. add_vault_permission(item_id, team_id, permission_type, grant_type, grant_value, created_by) -> tuple[bool, str]
60. remove_vault_permission(item_id, team_id, permission_type, grant_type, grant_value) -> tuple[bool, str]
61. check_vault_permission(item_id, team_id, user_id, permission_type) -> tuple[bool, str]
62. get_vault_permissions(item_id, team_id) -> List[Dict]

---

## Part 4: External Dependencies & Lazy Imports

### Current Imports (Lines 32-39)
```python
from rate_limiter import rate_limiter, get_client_ip
from permission_engine import require_perm, get_permission_engine
from audit_logger import audit_log_sync, AuditAction
```

### Usage in Code

#### permission_engine (5+ uses)
- `@require_perm()` decorator on endpoints:
  - "system.manage_users" - for create_team_v3
  - "team.use" - for most team endpoints
- `get_permission_engine().invalidate_user_permissions(user_id)` - called after:
  - Role changes
  - Member removal
  - Join team

**Recommendation**: Keep at module level (used heavily)

#### audit_logger (8+ uses)
- `audit_log_sync(user_id, action, resource, resource_id, details)` called for:
  - Team creation: AuditAction.USER_CREATED
  - Invite creation: "team.invite.created"
  - Role changes: "team.member.role.changed"
  - Member removal: "team.member.removed"
  - Join team: "team.member.joined"

**Recommendation**: Keep at module level (used frequently)

#### rate_limiter (1-2 uses)
- `rate_limiter.check_rate_limit()` in join_team endpoint:
  - Key: f"team:join:{client_ip}"
  - Limit: 10 requests per 60 seconds
- `get_client_ip()` to extract IP from request

**Recommendation**: Keep at module level (simple usage)

### Lazy Import Candidates
None of these are truly "lazy" candidates because:
1. They're used at module load time (@require_perm on function definitions)
2. They're used in high-traffic endpoints
3. The overhead of lazy imports would outweigh benefits

**All 3 should remain as eager imports at module level**

---

## Part 5: Database Schema

### Existing Tables (9)
```sql
-- Core team management
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1
)

CREATE TABLE team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,              -- super_admin, admin, member, guest
    job_role TEXT DEFAULT 'unassigned',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, user_id)
)

-- Invite codes
CREATE TABLE invite_codes (
    code TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    used_by TEXT,
    used_at TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
)

CREATE TABLE team_invites (
    invite_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    email_or_username TEXT NOT NULL,
    role TEXT,
    invited_by TEXT,
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT DEFAULT 'pending',    -- pending, accepted, rejected, expired
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
)

-- Brute-force protection
CREATE TABLE invite_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invite_code TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL
)

-- Promotion scheduling
CREATE TABLE delayed_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    from_role TEXT NOT NULL,
    to_role TEXT NOT NULL,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execute_at TIMESTAMP NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    reason TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, user_id, executed)
)

CREATE TABLE temp_promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT NOT NULL,
    original_super_admin_id TEXT NOT NULL,
    promoted_admin_id TEXT NOT NULL,
    promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reverted_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',  -- active, approved, reverted
    reason TEXT,
    approved_by TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    UNIQUE(team_id, promoted_admin_id, status)
)
```

### New Tables Needed (for new features)
```sql
-- Workflow permissions
CREATE TABLE workflow_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    permission_type TEXT NOT NULL,  -- view, edit, delete, assign
    grant_type TEXT NOT NULL,       -- role, job_role, user
    grant_value TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(workflow_id, team_id, permission_type, grant_type, grant_value)
)

-- Queue management
CREATE TABLE queues (
    queue_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    queue_name TEXT NOT NULL,
    queue_type TEXT,                -- patient, medication, pharmacy, etc.
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
)

CREATE TABLE queue_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    access_type TEXT NOT NULL,     -- view, manage, assign
    grant_type TEXT NOT NULL,      -- role, job_role, user
    grant_value TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (queue_id) REFERENCES queues(queue_id),
    UNIQUE(queue_id, access_type, grant_type, grant_value)
)

-- God rights / Founder Rights
CREATE TABLE god_rights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,
    revoked_at TIMESTAMP,
    revoked_by TEXT,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT
)

-- Team vault
CREATE TABLE vault_items (
    item_id TEXT PRIMARY KEY,
    team_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT,                 -- document, image, file, note, patient_record
    encrypted_content TEXT,         -- encrypted blob
    encryption_algorithm TEXT,      -- encryption method used
    mime_type TEXT,
    file_size INTEGER,
    metadata TEXT,                  -- encrypted metadata
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
)

CREATE TABLE vault_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    permission_type TEXT NOT NULL,  -- view, edit, delete
    grant_type TEXT NOT NULL,       -- role, job_role, user
    grant_value TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES vault_items(item_id),
    UNIQUE(item_id, permission_type, grant_type, grant_value)
)
```

---

## Part 6: Migration Action Plan

### Step 1: Create api/schemas/team_models.py
Extract all 76 Pydantic models into organized groups:
- Team core (CreateTeamRequest, TeamResponse, etc.)
- Member management (UpdateRoleRequest, UpdateRoleResponse, etc.)
- Promotion system (AutoPromoteResponse, DelayedPromoteRequest, etc.)
- Workflow permissions (AddWorkflowPermissionRequest, etc.)
- Queue management (CreateQueueRequest, AddQueuePermission, etc.)
- God rights (GrantGodRightsRequest, CheckGodRightsResponse, etc.)
- Vault (CreateVaultItemRequest, VaultItemInfo, etc.)

File size: ~500-600 lines

### Step 2: Create api/services/team.py
Move TeamManager class with all 60+ methods organized by functional area:
- Core operations
- Invite management
- Member management
- Role validation
- Promotion system (auto/instant/delayed)
- Admin offline failsafe
- Job role management
- Workflow permissions
- Queue management
- God rights
- Vault (with encryption)

File size: ~2000-2500 lines

### Step 3: Create api/routes/team.py
Extract all 50 API endpoints organized by functional area:
- Core team endpoints (5-7 endpoints)
- Member management (5-6 endpoints)
- Join & invite (2 endpoints)
- Promotion system (8-10 endpoints)
- Workflow permissions (4-5 endpoints)
- Queue management (6-7 endpoints)
- God rights (5 endpoints)
- Vault (8-9 endpoints)

Each endpoint is now thin: just validation + service call + response

File size: ~1500-2000 lines

### Step 4: Update imports
- api/routes/team.py imports from api/services/team.py
- Both import from api/schemas/team_models.py
- Keep permission_engine, audit_logger, rate_limiter at appropriate levels

### Step 5: Update api/__init__.py or main.py
Include the new router:
```python
from api.routes.team import router as team_router
app.include_router(team_router)
```

---

## Summary Table

| Aspect | Count | Notes |
|--------|-------|-------|
| **Pydantic Models** | 76 | Across 8 functional groups |
| **API Endpoints** | 50+ | Organized by domain |
| **TeamManager Methods** | 62 | Well-organized helpers |
| **Database Tables** | 9 existing + 6 new | Schema needs updates |
| **External Dependencies** | 3 | All eager imports, no lazy needed |
| **Lines of Code** | 5,145 | Current monolithic file |
| **Target after split** | ~4,000 | team.py + routes.py + models.py |

---

## Key Insights

1. **The file is well-structured** despite its size - methods are logically grouped
2. **Database-heavy** - lots of SQL operations, could benefit from query builders
3. **Permission-intensive** - every endpoint has @require_perm decorators
4. **Audit-enabled** - all mutations are logged via audit_logger
5. **Three main phases**:
   - Phase 3: App_db migration (invite, team core)
   - Phase 5: Workflow/Queue permissions
   - Phase 6: God rights + Vault

6. **Encryption needed** - Vault items require team-specific encryption keys
7. **Promotion system complex** - Multiple types (auto, instant, delayed, temp failsafe)
8. **Brute-force protection** - Rate limiting on invite code validation

---

## Recommended File Structure

```
apps/backend/api/
├── schemas/
│   └── team_models.py (76 models)
├── services/
│   └── team.py (TeamManager + 62 methods)
└── routes/
    └── team.py (50+ endpoints)
```

This structure enables:
- Clear separation of concerns
- Easy testing of service layer
- Thin, readable route handlers
- Reusable models
- Simplified imports
