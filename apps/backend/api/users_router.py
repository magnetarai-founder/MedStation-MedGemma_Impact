"""
Users & RBAC API Router
Exposes endpoints for user management and role-based access control
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users-rbac"])


class User(BaseModel):
    id: str
    username: str
    role: str
    created_at: str
    role_changed_at: Optional[str] = None
    role_changed_by: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    role: str = "member"


class RoleUpdate(BaseModel):
    role: str


class Permission(BaseModel):
    name: str
    description: str
    roles: list[str]


# Mock current user for development - replace with actual auth
async def get_current_user() -> User:
    """Get current authenticated user"""
    # TODO: Replace with actual authentication
    return User(
        id="dev-user-1",
        username="developer",
        role="super_admin",
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information

    Returns the authenticated user's profile
    """
    return current_user


@router.get("", response_model=list[User])
async def get_all_users(current_user: User = Depends(get_current_user)):
    """
    Get all users (Admin only)

    Returns list of all users in the system
    """
    try:
        from permissions import require_permission, Permission as Perm

        # Check if user has permission to view all users
        if current_user.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # TODO: Replace with actual user database query
        # For now, return mock data
        users = [
            User(
                id="user-1",
                username="admin",
                role="super_admin",
                created_at="2025-01-01T00:00:00Z"
            ),
            User(
                id="user-2",
                username="john_doe",
                role="admin",
                created_at="2025-01-02T00:00:00Z"
            ),
            User(
                id="user-3",
                username="jane_smith",
                role="member",
                created_at="2025-01-03T00:00:00Z"
            ),
            User(
                id="user-4",
                username="viewer_user",
                role="viewer",
                created_at="2025-01-04T00:00:00Z"
            ),
        ]

        return users
    except ImportError:
        raise HTTPException(status_code=503, detail="RBAC service not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """
    Get user by ID

    Args:
        user_id: The user ID to retrieve
    """
    try:
        # TODO: Replace with actual user database query
        if user_id == current_user.id:
            return current_user

        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/role", response_model=User)
async def update_user_role(
    user_id: str,
    role_update: RoleUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update user role (Super Admin only)

    Args:
        user_id: The user ID to update
        role_update: The new role

    Returns updated user
    """
    try:
        from permissions import UserRole

        # Only super admin can update roles
        if current_user.role != "super_admin":
            raise HTTPException(status_code=403, detail="Only Super Admin can update roles")

        # Validate role
        valid_roles = ["super_admin", "admin", "member", "viewer"]
        if role_update.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

        # Cannot change own role
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot change your own role")

        # TODO: Replace with actual database update
        updated_user = User(
            id=user_id,
            username="updated_user",
            role=role_update.role,
            created_at=datetime.utcnow().isoformat(),
            role_changed_at=datetime.utcnow().isoformat(),
            role_changed_by=current_user.id
        )

        logger.info(f"User {user_id} role changed to {role_update.role} by {current_user.id}")

        # Log to audit system
        try:
            from audit_logger import audit_log_sync, AuditAction
            audit_log_sync(
                user_id=current_user.id,
                action=AuditAction.USER_ROLE_CHANGED,
                resource="user",
                resource_id=user_id,
                details={
                    "new_role": role_update.role,
                    "changed_by": current_user.id
                }
            )
        except Exception as e:
            logger.debug(f"Could not log to audit: {e}")

        return updated_user
    except ImportError:
        raise HTTPException(status_code=503, detail="RBAC service not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=User)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create new user (Admin only)

    Args:
        user_create: User creation data

    Returns created user
    """
    try:
        # Only admin and super_admin can create users
        if current_user.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Admin cannot create other admins
        if current_user.role == "admin" and user_create.role in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Admins cannot create other admins")

        # TODO: Replace with actual user creation
        new_user = User(
            id=f"user-{datetime.utcnow().timestamp()}",
            username=user_create.username,
            role=user_create.role,
            created_at=datetime.utcnow().isoformat()
        )

        logger.info(f"User {new_user.id} created by {current_user.id}")

        return new_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete user (Admin only)

    Args:
        user_id: The user ID to delete

    Returns success message
    """
    try:
        # Only admin and super_admin can delete users
        if current_user.role not in ["super_admin", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Cannot delete yourself
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")

        # TODO: Check if last admin (protection)
        # TODO: Replace with actual user deletion

        logger.info(f"User {user_id} deleted by {current_user.id}")

        return {"success": True, "message": f"User {user_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions/list", response_model=list[Permission])
async def list_permissions(current_user: User = Depends(get_current_user)):
    """
    Get list of all permissions

    Returns permission matrix showing which roles have which permissions
    """
    try:
        from permissions import PERMISSIONS

        result = []
        for perm_name, perm_data in PERMISSIONS.items():
            result.append(Permission(
                name=perm_name,
                description=perm_data.get("description", ""),
                roles=perm_data.get("roles", [])
            ))

        return result
    except ImportError:
        # Return default permissions if service not available
        return [
            Permission(
                name="manage_users",
                description="Create, update, and delete users",
                roles=["super_admin", "admin"]
            ),
            Permission(
                name="create_admin",
                description="Create admin users",
                roles=["super_admin"]
            ),
            Permission(
                name="view_audit_logs",
                description="View audit logs",
                roles=["super_admin", "admin"]
            ),
        ]
    except Exception as e:
        logger.error(f"Error listing permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
