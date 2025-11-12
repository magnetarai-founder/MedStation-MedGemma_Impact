"""
Team-related Pydantic models for ElohimOS API.

Models for team management, member management, promotions, permissions,
queues, Founder Rights, and team vault functionality.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ============================================================================
# Core Team Management
# ============================================================================

class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None
    creator_user_id: str


class TeamResponse(BaseModel):
    team_id: str
    name: str
    description: Optional[str]
    created_at: str
    created_by: str
    invite_code: str


class InviteCodeResponse(BaseModel):
    code: str
    team_id: str
    expires_at: Optional[str]


class JoinTeamRequest(BaseModel):
    invite_code: str
    user_id: str


class JoinTeamResponse(BaseModel):
    success: bool
    team_id: str
    team_name: str
    user_role: str


# ============================================================================
# Member Management
# ============================================================================

class InviteRequest(BaseModel):
    email_or_username: str
    role: str = "member"


class ChangeRoleBody(BaseModel):
    role: str


class UpdateRoleRequest(BaseModel):
    new_role: str
    requesting_user_role: Optional[str] = None
    requesting_user_id: Optional[str] = None


class UpdateRoleResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    team_id: str
    new_role: str


class HeartbeatRequest(BaseModel):
    user_id: str


class HeartbeatResponse(BaseModel):
    success: bool
    message: str


# ============================================================================
# Promotion System
# ============================================================================

class AutoPromoteResponse(BaseModel):
    promoted_users: List[Dict]
    total_promoted: int


class InstantPromoteRequest(BaseModel):
    approved_by_user_id: str
    auth_type: str = 'real_password'


class InstantPromoteResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    new_role: str


class DelayedPromoteRequest(BaseModel):
    delay_days: int = 21
    approved_by_user_id: str
    reason: str = "Decoy password delay"


class DelayedPromoteResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    execute_date: str
    delay_days: int


class ExecuteDelayedResponse(BaseModel):
    executed_promotions: List[Dict]
    total_executed: int


class OfflineSuperAdminsResponse(BaseModel):
    offline_admins: List[Dict]
    count: int
    threshold_minutes: int


class PromoteTempAdminRequest(BaseModel):
    offline_super_admin_id: str
    requesting_user_role: Optional[str] = None


class PromoteTempAdminResponse(BaseModel):
    success: bool
    message: str
    promoted_admin_id: Optional[str] = None


class TempPromotionsResponse(BaseModel):
    temp_promotions: List[Dict]
    count: int


class ApproveTempPromotionRequest(BaseModel):
    approved_by: str


class ApproveTempPromotionResponse(BaseModel):
    success: bool
    message: str


class RevertTempPromotionRequest(BaseModel):
    reverted_by: str


class RevertTempPromotionResponse(BaseModel):
    success: bool
    message: str


# ============================================================================
# Job Roles
# ============================================================================

class UpdateJobRoleRequest(BaseModel):
    job_role: str


class UpdateJobRoleResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    job_role: str


class JobRoleResponse(BaseModel):
    user_id: str
    job_role: Optional[str]


# ============================================================================
# Workflow Permissions
# ============================================================================

class AddWorkflowPermissionRequest(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str
    created_by: str


class AddWorkflowPermissionResponse(BaseModel):
    success: bool
    message: str
    workflow_id: str
    permission_type: str
    grant_type: str
    grant_value: str


class RemoveWorkflowPermissionRequest(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str


class RemoveWorkflowPermissionResponse(BaseModel):
    success: bool
    message: str


class WorkflowPermissionGrant(BaseModel):
    id: int
    permission_type: str
    grant_type: str
    grant_value: str
    created_at: str
    created_by: str


class GetWorkflowPermissionsResponse(BaseModel):
    workflow_id: str
    team_id: str
    permissions: List[WorkflowPermissionGrant]
    count: int


class CheckWorkflowPermissionRequest(BaseModel):
    user_id: str
    permission_type: str


class CheckWorkflowPermissionResponse(BaseModel):
    has_permission: bool
    message: str
    workflow_id: str
    user_id: str
    permission_type: str


# ============================================================================
# Queue Management
# ============================================================================

class CreateQueueRequest(BaseModel):
    queue_name: str
    queue_type: str
    description: str
    created_by: str


class CreateQueueResponse(BaseModel):
    success: bool
    message: str
    queue_id: str


class AddQueuePermissionRequest(BaseModel):
    access_type: str
    grant_type: str
    grant_value: str
    created_by: str


class AddQueuePermissionResponse(BaseModel):
    success: bool
    message: str
    queue_id: str
    access_type: str
    grant_type: str
    grant_value: str


class RemoveQueuePermissionRequest(BaseModel):
    access_type: str
    grant_type: str
    grant_value: str


class RemoveQueuePermissionResponse(BaseModel):
    success: bool
    message: str


class QueuePermissionGrant(BaseModel):
    id: int
    access_type: str
    grant_type: str
    grant_value: str
    created_at: str
    created_by: str


class GetQueuePermissionsResponse(BaseModel):
    queue_id: str
    team_id: str
    permissions: List[QueuePermissionGrant]
    count: int


class CheckQueueAccessRequest(BaseModel):
    user_id: str
    access_type: str


class CheckQueueAccessResponse(BaseModel):
    has_access: bool
    message: str
    queue_id: str
    user_id: str
    access_type: str


class QueueInfo(BaseModel):
    queue_id: str
    queue_name: str
    queue_type: str
    description: str
    created_at: str
    created_by: str
    access_reason: str


class GetAccessibleQueuesResponse(BaseModel):
    team_id: str
    user_id: str
    access_type: str
    queues: List[QueueInfo]
    count: int


class QueueDetails(BaseModel):
    queue_id: str
    queue_name: str
    queue_type: str
    description: str
    created_at: str
    created_by: str
    is_active: bool


# ============================================================================
# Founder Rights (God Rights)
# ============================================================================

class GrantGodRightsRequest(BaseModel):
    user_id: str
    delegated_by: Optional[str] = None
    auth_key: Optional[str] = None
    notes: Optional[str] = None


class GrantGodRightsResponse(BaseModel):
    success: bool
    message: str


class RevokeGodRightsRequest(BaseModel):
    user_id: str
    revoked_by: str


class RevokeGodRightsResponse(BaseModel):
    success: bool
    message: str


class CheckGodRightsRequest(BaseModel):
    user_id: str


class CheckGodRightsResponse(BaseModel):
    has_god_rights: bool
    message: str


class GodRightsUser(BaseModel):
    user_id: str
    delegated_by: Optional[str] = None
    created_at: str
    notes: Optional[str] = None
    is_founder: bool


class GetGodRightsUsersResponse(BaseModel):
    users: List[GodRightsUser]
    count: int


class RevokedGodRightsUser(BaseModel):
    user_id: str
    delegated_by: Optional[str] = None
    created_at: str
    revoked_at: str
    notes: Optional[str] = None


class GetRevokedGodRightsResponse(BaseModel):
    users: List[RevokedGodRightsUser]
    count: int


# ============================================================================
# Team Vault
# ============================================================================

class CreateVaultItemRequest(BaseModel):
    item_name: str
    item_type: str
    content: str
    mime_type: Optional[str] = None
    metadata: Optional[str] = None
    created_by: str


class CreateVaultItemResponse(BaseModel):
    success: bool
    message: str
    item_id: str


class VaultItemInfo(BaseModel):
    item_id: str
    item_name: str
    item_type: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: str
    created_by: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    metadata: Optional[str] = None


class ListVaultItemsResponse(BaseModel):
    team_id: str
    user_id: str
    items: List[VaultItemInfo]
    count: int


class VaultItemDetail(BaseModel):
    item_id: str
    team_id: str
    item_name: str
    item_type: str
    content: str
    file_size: int
    mime_type: Optional[str] = None
    created_at: str
    created_by: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    metadata: Optional[str] = None


class UpdateVaultItemRequest(BaseModel):
    content: str
    updated_by: str


class UpdateVaultItemResponse(BaseModel):
    success: bool
    message: str


class DeleteVaultItemRequest(BaseModel):
    deleted_by: str


class DeleteVaultItemResponse(BaseModel):
    success: bool
    message: str


class AddVaultPermissionRequest(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str
    created_by: str


class AddVaultPermissionResponse(BaseModel):
    success: bool
    message: str


class RemoveVaultPermissionRequest(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str


class RemoveVaultPermissionResponse(BaseModel):
    success: bool
    message: str


class VaultPermissionGrant(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str
    created_at: str
    created_by: str


class GetVaultPermissionsResponse(BaseModel):
    item_id: str
    team_id: str
    permissions: List[VaultPermissionGrant]
    count: int


class CheckVaultPermissionRequest(BaseModel):
    user_id: str
    permission_type: str


class CheckVaultPermissionResponse(BaseModel):
    has_permission: bool
    reason: str
