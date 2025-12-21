"""
Team Service Core Logic

TeamManager class with all team operations:
- Team CRUD
- Member management
- Invite code generation and validation
- Role and promotion management
- Workflow and queue permissions
- God Rights (Founder Rights) management
- Team vault operations
"""

import sqlite3
import logging
import hashlib
import secrets
import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from api.config_paths import get_config_paths

# Import modular team service components
from . import storage
from . import members as members_mod
from . import invitations as invitations_mod
from . import roles as roles_mod
from . import founder_rights as founder_mod
from . import workflows as workflows_mod
from . import queues as queues_mod
from . import vault as vault_mod
from .types import SuccessResult, SuccessResultWithId

logger = logging.getLogger(__name__)

# Database path
PATHS = get_config_paths()

class TeamManager:
    """
    Manages team creation, member management, and invite codes
    """

    def __init__(self):
        # Phase 3: No longer maintain persistent connection, use _get_app_conn() per operation
        # self.conn is kept for backward compatibility but should not be used
        self.conn = None
        # Database is initialized via Phase 3 migration, not here
        # self._init_database()

    def _init_database(self) -> None:
        """Initialize team database tables"""
        cursor = self.conn.cursor()

        # Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL
            )
        """)

        # Team members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                job_role TEXT DEFAULT 'unassigned',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(team_id, user_id)
            )
        """)

        # Invite codes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_codes (
                code TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used BOOLEAN DEFAULT FALSE,
                used_by TEXT,
                used_at TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (team_id)
            )
        """)

        # Delayed promotions table (for decoy password 21-day delay)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delayed_promotions (
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
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(team_id, user_id, executed)
            )
        """)

        # Temporary promotions table (for offline Super Admin failsafe)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                original_super_admin_id TEXT NOT NULL,
                promoted_admin_id TEXT NOT NULL,
                promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reverted_at TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active',
                reason TEXT,
                approved_by TEXT,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(team_id, promoted_admin_id, status)
            )
        """)

        # Invite code attempts tracking (HIGH-05: Brute-force protection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_code TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL
            )
        """)

        # Index for fast lookup of recent attempts
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_invite_attempts_code_ip
            ON invite_attempts(invite_code, ip_address, attempt_timestamp DESC)
        """)

        # Workflow permissions table (Phase 5.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                permission_type TEXT NOT NULL,
                grant_type TEXT NOT NULL,
                grant_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(workflow_id, team_id, permission_type, grant_type, grant_value)
            )
        """)

        # Queues table (Phase 5.3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                queue_name TEXT NOT NULL,
                queue_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(queue_id, team_id)
            )
        """)

        # Queue permissions table (Phase 5.3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                access_type TEXT NOT NULL,
                grant_type TEXT NOT NULL,
                grant_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(queue_id, team_id, access_type, grant_type, grant_value)
            )
        """)

        # Founder Rights authorization table (Phase 6.1)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS god_rights_auth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                auth_key_hash TEXT,
                delegated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                notes TEXT
            )
        """)

        # Team vault items table (Phase 6.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_vault_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                encrypted_content TEXT NOT NULL,
                encryption_key_hash TEXT,
                file_size INTEGER,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP,
                deleted_by TEXT,
                metadata TEXT,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(item_id, team_id)
            )
        """)

        # Team vault permissions table (Phase 6.2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_vault_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                permission_type TEXT NOT NULL,
                grant_type TEXT NOT NULL,
                grant_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                UNIQUE(item_id, team_id, permission_type, grant_type, grant_value)
            )
        """)

        self.conn.commit()
        logger.info("Team database initialized")

    # ========================================================================
    # TEAM CREATION & BASIC MANAGEMENT
    # ========================================================================

    async def generate_team_id(self, team_name: str) -> str:
        """
        Generate a unique team ID based on team name
        Format: TEAMNAME-XXXXX (e.g., MEDICALMISSION-A7B3C)
        """
        # Clean team name (remove spaces, special chars, uppercase)
        clean_name = ''.join(c for c in team_name if c.isalnum()).upper()[:20]

        # Generate random suffix
        suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))

        team_id = f"{clean_name}-{suffix}"

        # Ensure uniqueness
        if storage.team_id_exists(team_id):
            # Collision, try again with different suffix
            return self.generate_team_id(team_name)

        return team_id

    async def generate_invite_code(self, team_id: str, expires_days: Optional[int] = None) -> str:
        """
        Generate a shareable invite code
        Format: XXXXX-XXXXX-XXXXX (e.g., A7B3C-D9E2F-G1H4I)
        """
        return await asyncio.to_thread(invitations_mod.generate_invite_code(team_id, expires_days))

    async def create_team(self, name: str, creator_user_id: str, description: Optional[str] = None) -> Dict:
        """
        Create a new team

        Args:
            name: Team name
            creator_user_id: User ID of team creator
            description: Optional team description

        Returns:
            Dict with team details and invite code
        """
        try:
            # Generate team ID
            team_id = self.generate_team_id(name)

            # Create team
            storage.create_team_record(team_id, name, creator_user_id, description)

            # Add creator as Super Admin member
            storage.add_member_record(team_id, creator_user_id, 'super_admin')

            # Generate invite code (expires in 30 days)
            invite_code = self.generate_invite_code(team_id, expires_days=30)

            # Get created team details
            team_details = storage.get_team_by_id(team_id)
            if team_details:
                team_details['invite_code'] = invite_code
                return team_details

            raise Exception("Failed to retrieve created team")

        except Exception as e:
            logger.error(f"Failed to create team: {e}")
            raise

    async def get_team(self, team_id: str) -> Optional[Dict]:
        """Get team details by ID"""
        return await asyncio.to_thread(storage.get_team_by_id, team_id)

    async def get_team_members(self, team_id: str) -> List[Dict]:
        """Get all members of a team"""
        return await asyncio.to_thread(members_mod.get_team_members, team_id)

    async def get_user_teams(self, user_id: str) -> List[Dict]:
        """Get all teams a user is a member of"""
        return await asyncio.to_thread(members_mod.get_user_teams, user_id)

    # ========================================================================
    # INVITE CODE MANAGEMENT
    # ========================================================================

    async def get_active_invite_code(self, team_id: str) -> Optional[str]:
        """Get active (non-expired, unused) invite code for team"""
        return await asyncio.to_thread(invitations_mod.get_active_invite_code, team_id)

    async def regenerate_invite_code(self, team_id: str, expires_days: int = 30) -> str:
        """Generate a new invite code for team (invalidates old ones)"""
        return await asyncio.to_thread(invitations_mod.regenerate_invite_code, team_id, expires_days)

    async def record_invite_attempt(self, invite_code: str, ip_address: str, success: bool) -> None:
        """Record an invite code validation attempt (HIGH-05)"""
        await asyncio.to_thread(invitations_mod.record_invite_attempt, invite_code, ip_address, success)

    async def check_brute_force_lockout(self, invite_code: str, ip_address: str) -> bool:
        """
        Check if invite code is locked due to too many failed attempts (HIGH-05)

        Returns:
            True if locked (too many failures), False if attempts are allowed
        """
        return await asyncio.to_thread(invitations_mod.check_brute_force_lockout, invite_code, ip_address)

    async def validate_invite_code(self, invite_code: str, ip_address: Optional[str] = None) -> Optional[str]:
        """
        Validate invite code and return team_id if valid

        Args:
            invite_code: The invite code to validate
            ip_address: IP address of requester (for brute-force protection)

        Returns:
            team_id if code is valid and not expired/used, None otherwise
        """
        return await asyncio.to_thread(invitations_mod.validate_invite_code, invite_code, ip_address)

    async def join_team(self, team_id: str, user_id: str, role: str = 'member') -> bool:
        """
        Add user to team

        Args:
            team_id: Team to join
            user_id: User joining
            role: Role to assign (default: member)

        Returns:
            True if successful, False otherwise
        """
        return await asyncio.to_thread(members_mod.join_team(team_id, user_id, role))

    # ========================================================================
    # ROLE MANAGEMENT & PROMOTIONS
    # ========================================================================

    @staticmethod
    def get_max_super_admins(team_size: int) -> int:
        """Calculate maximum allowed Super Admins based on team size"""
        return roles_mod.get_max_super_admins(team_size)

    async def count_role(self, team_id: str, role: str) -> int:
        """
        Count members with a specific role in a team

        Args:
            team_id: Team ID
            role: Role to count (e.g., 'super_admin', 'admin', 'member')

        Returns:
            Number of members with that role
        """
        return await asyncio.to_thread(members_mod.count_role(team_id, role))

    async def count_super_admins(self, team_id: str) -> int:
        """Count current Super Admins in team"""
        return await asyncio.to_thread(members_mod.count_super_admins(team_id))

    async def get_team_size(self, team_id: str) -> int:
        """Get total number of members in team"""
        return await asyncio.to_thread(members_mod.get_team_size(team_id))

    async def can_promote_to_super_admin(self, team_id: str, requesting_user_role: str = None) -> tuple[bool, str]:
        """Check if team can have another Super Admin"""
        return await asyncio.to_thread(roles_mod.can_promote_to_super_admin(self, team_id, requesting_user_role))

    async def update_member_role(self, team_id: str, user_id: str, new_role: str, requesting_user_role: str = None, requesting_user_id: str = None) -> tuple[bool, str]:
        """
        Update a team member's role with validation

        Args:
            team_id: Team ID
            user_id: User whose role to update
            new_role: New role to assign
            requesting_user_role: Role of user making the request (for Founder Rights check)
            requesting_user_id: ID of user making the request (for Founder Rights protection)

        Returns:
            Tuple of (success: bool, message: str)
        """
        return await asyncio.to_thread(members_mod.update_member_role_impl(self, team_id, user_id, new_role, requesting_user_role, requesting_user_id))

    # ========================================================================
    # GUEST AUTO-PROMOTION & DELAYED PROMOTIONS
    # ========================================================================

    async def get_days_since_joined(self, team_id: str, user_id: str) -> Optional[int]:
        """
        Calculate days since user joined the team

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            Number of days since joining, or None if user not found
        """
        return await asyncio.to_thread(members_mod.get_days_since_joined(team_id, user_id))

    async def check_auto_promotion_eligibility(self, team_id: str, user_id: str, required_days: int = 7) -> tuple[bool, str, int]:
        """Check if a guest is eligible for auto-promotion to member"""
        return await asyncio.to_thread(roles_mod.check_auto_promotion_eligibility(self, team_id, user_id, required_days))

    async def auto_promote_guests(self, team_id: str, required_days: int = 7) -> List[Dict]:
        """Auto-promote all eligible guests in a team to members"""
        return await asyncio.to_thread(roles_mod.auto_promote_guests(self, team_id, required_days))
    async def instant_promote_guest(self, team_id: str, user_id: str, approved_by_user_id: str, auth_type: str = 'real_password') -> tuple[bool, str]:
        """Instantly promote a guest to member (Phase 4.2)"""
        return await asyncio.to_thread(roles_mod.instant_promote_guest(self, team_id, user_id, approved_by_user_id, auth_type))
    async def schedule_delayed_promotion(self, team_id: str, user_id: str, delay_days: int = 21, approved_by_user_id: str = None, reason: str = "Decoy password delay") -> tuple[bool, str]:
        """Schedule a delayed promotion (Phase 4.3)"""
        return await asyncio.to_thread(roles_mod.schedule_delayed_promotion(team_id, user_id, delay_days, approved_by_user_id, reason))
    async def execute_delayed_promotions(self, team_id: str = None) -> List[Dict]:
        """Execute all pending delayed promotions (cron job)"""
        return await asyncio.to_thread(roles_mod.execute_delayed_promotions(self, team_id))
    async def update_last_seen(self, team_id: str, user_id: str) -> tuple[bool, str]:
        """
        Update last_seen timestamp for a team member (Phase 3.3)

        Should be called on every user activity to track online status

        Args:
            team_id: Team ID
            user_id: User ID to update

        Returns:
            Tuple of (success: bool, message: str)
        """
        return await asyncio.to_thread(members_mod.update_last_seen(team_id, user_id))

    async def check_super_admin_offline(self, team_id: str, offline_threshold_minutes: int = 5) -> List[Dict]:
        """
        Check for offline Super Admins (Phase 3.3)

        A Super Admin is considered offline if last_seen > threshold minutes

        Args:
            team_id: Team ID
            offline_threshold_minutes: Minutes before considering offline (default: 5)

        Returns:
            List of offline super admins with details
        """
        try:
            from datetime import datetime, timedelta
            cursor = self.conn.cursor()

            threshold_time = datetime.now() - timedelta(minutes=offline_threshold_minutes)

            cursor.execute("""
                SELECT user_id, role, last_seen, joined_at
                FROM team_members
                WHERE team_id = ? AND role = 'super_admin' AND last_seen < ?
            """, (team_id, threshold_time))

            offline_admins = []
            for row in cursor.fetchall():
                last_seen = datetime.fromisoformat(row['last_seen'])
                minutes_offline = (datetime.now() - last_seen).total_seconds() / 60

                offline_admins.append({
                    'user_id': row['user_id'],
                    'role': row['role'],
                    'last_seen': row['last_seen'],
                    'minutes_offline': int(minutes_offline)
                })

            return offline_admins

        except Exception as e:
            logger.error(f"Failed to check super admin offline: {e}")
            return []

    async def promote_admin_temporarily(self, team_id: str, offline_super_admin_id: str, requesting_user_role: str = None) -> tuple[bool, str]:
        """Temporarily promote admin to super_admin (offline failsafe)"""
        return await asyncio.to_thread(roles_mod.promote_admin_temporarily(self, team_id, offline_super_admin_id, requesting_user_role))
    async def get_pending_temp_promotions(self, team_id: str) -> List[Dict]:
        """Get all pending temporary promotions for a team"""
        return await asyncio.to_thread(roles_mod.get_pending_temp_promotions(team_id))
    async def approve_temp_promotion(self, team_id: str, temp_promotion_id: int, approved_by: str) -> tuple[bool, str]:
        """Approve a temporary promotion (make permanent)"""
        return await asyncio.to_thread(roles_mod.approve_temp_promotion(temp_promotion_id, approved_by))
    async def revert_temp_promotion(self, team_id: str, temp_promotion_id: int, reverted_by: str) -> tuple[bool, str]:
        """Revert a temporary promotion (demote back to admin)"""
        return await asyncio.to_thread(roles_mod.revert_temp_promotion(self, temp_promotion_id, reverted_by))
    async def update_job_role(self, team_id: str, user_id: str, job_role: str) -> tuple[bool, str]:
        """
        Update a team member's job role (Phase 5.1)

        Job roles are used for workflow permissions and queue access control.
        Valid roles: doctor, pastor, nurse, admin_staff, volunteer, custom, unassigned

        Args:
            team_id: Team ID
            user_id: User ID to update
            job_role: New job role

        Returns:
            Tuple of (success: bool, message: str)
        """
        return await asyncio.to_thread(members_mod.update_job_role(team_id, user_id, job_role))

    async def get_member_job_role(self, team_id: str, user_id: str) -> Optional[str]:
        """
        Get a team member's job role (Phase 5.1)

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            Job role string or None if not found
        """
        return await asyncio.to_thread(members_mod.get_member_job_role(team_id, user_id))

    # ========================================================================
    # WORKFLOW PERMISSIONS (Phase 5.2) - Delegated to workflows module
    # ========================================================================

    async def add_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
        """Add a workflow permission grant - delegates to workflows module"""
        return await asyncio.to_thread(
            workflows_mod.add_workflow_permission,
            workflow_id, team_id, permission_type, grant_type, grant_value, created_by
        )

    async def remove_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
        """Remove a workflow permission grant - delegates to workflows module"""
        return await asyncio.to_thread(
            workflows_mod.remove_workflow_permission,
            workflow_id, team_id, permission_type, grant_type, grant_value
        )

    async def check_workflow_permission(self, workflow_id: str, team_id: str, user_id: str, permission_type: str) -> tuple[bool, str]:
        """Check if a user has a specific workflow permission - delegates to workflows module"""
        return await asyncio.to_thread(
            workflows_mod.check_workflow_permission,
            workflow_id, team_id, user_id, permission_type
        )

    async def get_workflow_permissions(self, workflow_id: str, team_id: str) -> List[Dict]:
        """Get all permission grants for a workflow - delegates to workflows module"""
        return await asyncio.to_thread(
            workflows_mod.get_workflow_permissions,
            workflow_id, team_id
        )

    # ========================================================================
    # QUEUE ACCESS CONTROL METHODS (Phase 5.3) - Delegated to queues module
    # ========================================================================

    async def create_queue(self, team_id: str, queue_name: str, queue_type: str, description: str, created_by: str) -> tuple[bool, str, str]:
        """Create a new queue - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.create_queue,
            team_id, queue_name, queue_type, description, created_by
        )

    async def add_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
        """Add queue access permission - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.add_queue_permission,
            queue_id, team_id, access_type, grant_type, grant_value, created_by
        )

    async def remove_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
        """Remove queue access permission - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.remove_queue_permission,
            queue_id, team_id, access_type, grant_type, grant_value
        )

    async def check_queue_access(self, queue_id: str, team_id: str, user_id: str, access_type: str) -> tuple[bool, str]:
        """Check if a user has access to a queue - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.check_queue_access,
            queue_id, team_id, user_id, access_type
        )

    async def get_accessible_queues(self, team_id: str, user_id: str, access_type: str = 'view') -> List[Dict]:
        """Get all queues a user can access - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.get_accessible_queues,
            team_id, user_id, access_type
        )

    async def get_queue_permissions(self, queue_id: str, team_id: str) -> List[Dict]:
        """Get all permission grants for a queue - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.get_queue_permissions,
            queue_id, team_id
        )

    async def get_queue(self, queue_id: str, team_id: str) -> Optional[Dict]:
        """Get queue details - delegates to queues module"""
        return await asyncio.to_thread(
            queues_mod.get_queue,
            queue_id, team_id
        )

    # ========================================================================
    # GOD RIGHTS AUTHORIZATION METHODS (Phase 6.1)
    # ========================================================================

    async def grant_god_rights(self, user_id: str, delegated_by: str = None, auth_key: str = None, notes: str = None) -> tuple[bool, str]:
        """Grant Founder Rights to a user"""
        return await asyncio.to_thread(founder_mod.grant_god_rights(self, user_id, delegated_by, auth_key, notes))
    async def revoke_god_rights(self, user_id: str, revoked_by: str) -> tuple[bool, str]:
        """Revoke Founder Rights from a user"""
        return await asyncio.to_thread(founder_mod.revoke_god_rights(self, user_id, revoked_by))
    async def check_god_rights(self, user_id: str) -> tuple[bool, str]:
        """Check if a user has active Founder Rights"""
        return await asyncio.to_thread(founder_mod.check_god_rights(user_id))
    async def get_god_rights_users(self) -> List[Dict]:
        """Get all users with active Founder Rights"""
        return await asyncio.to_thread(founder_mod.get_god_rights_users())
    async def get_revoked_god_rights(self) -> List[Dict]:
        """Get all users with revoked Founder Rights"""
        return await asyncio.to_thread(founder_mod.get_revoked_god_rights())
    # ========================================================================
    # TEAM VAULT OPERATIONS (Phase 6.2) - Delegated to vault module
    # ========================================================================

    def create_vault_item(self, team_id: str, item_name: str, item_type: str, content: str, created_by: str, mime_type: str = None, metadata: str = None) -> tuple[bool, str, str]:
        """Create a new encrypted vault item - delegates to vault module"""
        return vault_mod.create_vault_item(team_id, item_name, item_type, content, created_by, mime_type, metadata)

    def update_vault_item(self, item_id: str, team_id: str, content: str, updated_by: str) -> tuple[bool, str]:
        """Update vault item content - delegates to vault module"""
        return vault_mod.update_vault_item(item_id, team_id, content, updated_by)

    def delete_vault_item(self, item_id: str, team_id: str, deleted_by: str) -> tuple[bool, str]:
        """Soft delete vault item - delegates to vault module"""
        return vault_mod.delete_vault_item(item_id, team_id, deleted_by)

    def get_vault_item(self, item_id: str, team_id: str, decrypt: bool = True) -> Optional[Dict]:
        """Get vault item and optionally decrypt - delegates to vault module"""
        return vault_mod.get_vault_item(item_id, team_id, decrypt)

    def list_vault_items(self, team_id: str, user_id: str, item_type: str = None, include_deleted: bool = False) -> List[Dict]:
        """List vault items accessible to user - delegates to vault module"""
        return vault_mod.list_vault_items(team_id, user_id, item_type, include_deleted)

    def check_vault_permission(self, item_id: str, team_id: str, user_id: str, permission_type: str) -> tuple[bool, str]:
        """Check if user has vault item permission - delegates to vault module"""
        return vault_mod.check_vault_permission(item_id, team_id, user_id, permission_type)

    def add_vault_permission(self, item_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
        """Add vault item permission - delegates to vault module"""
        return vault_mod.add_vault_permission(item_id, team_id, permission_type, grant_type, grant_value, created_by)

    def remove_vault_permission(self, item_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
        """Remove vault item permission - delegates to vault module"""
        return vault_mod.remove_vault_permission(item_id, team_id, permission_type, grant_type, grant_value)

    def get_vault_permissions(self, item_id: str, team_id: str) -> List[Dict]:
        """Get all permissions for a vault item - delegates to vault module"""
        return vault_mod.get_vault_permissions(item_id, team_id)

    async def close(self) -> None:
        """Close database connection"""
        if self.conn:
            await asyncio.to_thread(self.conn.close)
