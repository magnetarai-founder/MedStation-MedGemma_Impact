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

    def _init_database(self):
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

    async def record_invite_attempt(self, invite_code: str, ip_address: str, success: bool):
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
    # WORKFLOW PERMISSIONS (Phase 5.2)
    # ========================================================================

    async def add_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
        """
        Add a workflow permission grant (Phase 5.2)

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            permission_type: 'view', 'edit', 'delete', 'assign'
            grant_type: 'role', 'job_role', 'user'
            grant_value: Depends on grant_type (role name, job role, or user_id)
            created_by: User ID who created this permission

        Returns:
            Tuple of (success: bool, message: str)
        """
        valid_permission_types = ['view', 'edit', 'delete', 'assign']
        valid_grant_types = ['role', 'job_role', 'user']

        if permission_type not in valid_permission_types:
            return False, f"Invalid permission type. Must be one of: {', '.join(valid_permission_types)}"

        if grant_type not in valid_grant_types:
            return False, f"Invalid grant type. Must be one of: {', '.join(valid_grant_types)}"

        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO workflow_permissions (workflow_id, team_id, permission_type, grant_type, grant_value, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (workflow_id, team_id, permission_type, grant_type, grant_value, created_by))

            self.conn.commit()

            logger.info(f"Added {permission_type} permission for workflow {workflow_id}: {grant_type}={grant_value}")

            return True, f"Permission granted: {grant_type}={grant_value} can {permission_type}"

        except sqlite3.IntegrityError:
            return False, "Permission already exists"
        except Exception as e:
            logger.error(f"Failed to add workflow permission: {e}")
            return False, str(e)

    async def remove_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
        """
        Remove a workflow permission grant (Phase 5.2)

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            permission_type: 'view', 'edit', 'delete', 'assign'
            grant_type: 'role', 'job_role', 'user'
            grant_value: Depends on grant_type

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                DELETE FROM workflow_permissions
                WHERE workflow_id = ? AND team_id = ? AND permission_type = ? AND grant_type = ? AND grant_value = ?
            """, (workflow_id, team_id, permission_type, grant_type, grant_value))

            self.conn.commit()

            if cursor.rowcount == 0:
                return False, "Permission not found"

            logger.info(f"Removed {permission_type} permission for workflow {workflow_id}: {grant_type}={grant_value}")

            return True, f"Permission revoked: {grant_type}={grant_value} can no longer {permission_type}"

        except Exception as e:
            logger.error(f"Failed to remove workflow permission: {e}")
            return False, str(e)

    async def check_workflow_permission(self, workflow_id: str, team_id: str, user_id: str, permission_type: str) -> tuple[bool, str]:
        """
        Check if a user has a specific workflow permission (Phase 5.2)

        Checks in order:
        1. Founder Rights always have all permissions
        2. Explicit user grants
        3. Job role grants
        4. Role grants
        5. Default permissions (if no explicit permissions exist)

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            user_id: User ID to check
            permission_type: 'view', 'edit', 'delete', 'assign'

        Returns:
            Tuple of (has_permission: bool, reason: str)
        """
        try:
            cursor = self.conn.cursor()

            # Get user's role and job_role
            cursor.execute("""
                SELECT role, job_role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            member = cursor.fetchone()
            if not member:
                return False, "User not found in team"

            user_role = member['role']
            user_job_role = member['job_role'] or 'unassigned'

            # Founder Rights always have all permissions
            if user_role == 'god_rights':
                return True, "Founder Rights override"

            # Check if any explicit permissions exist for this workflow
            cursor.execute("""
                SELECT COUNT(*) as count FROM workflow_permissions
                WHERE workflow_id = ? AND team_id = ?
            """, (workflow_id, team_id))

            has_explicit_perms = cursor.fetchone()['count'] > 0

            if has_explicit_perms:
                # Check explicit permissions in order: user > job_role > role
                cursor.execute("""
                    SELECT grant_type, grant_value FROM workflow_permissions
                    WHERE workflow_id = ? AND team_id = ? AND permission_type = ?
                """, (workflow_id, team_id, permission_type))

                grants = cursor.fetchall()

                for grant in grants:
                    if grant['grant_type'] == 'user' and grant['grant_value'] == user_id:
                        return True, f"Explicit user grant"
                    if grant['grant_type'] == 'job_role' and grant['grant_value'] == user_job_role:
                        return True, f"Job role grant ({user_job_role})"
                    if grant['grant_type'] == 'role' and grant['grant_value'] == user_role:
                        return True, f"Role grant ({user_role})"

                return False, f"No matching permission grant found"

            else:
                # Use default permissions
                return self._check_default_permission(user_role, permission_type)

        except Exception as e:
            logger.error(f"Failed to check workflow permission: {e}")
            return False, str(e)

    def _check_default_permission(self, user_role: str, permission_type: str) -> tuple[bool, str]:
        """
        Check default permissions when no explicit grants exist (Phase 5.2)

        Default permissions:
        - VIEW: member and above
        - EDIT: admin and above
        - DELETE: super_admin and above
        - ASSIGN: admin and above

        Args:
            user_role: User's role
            permission_type: Permission to check

        Returns:
            Tuple of (has_permission: bool, reason: str)
        """
        role_hierarchy = {
            'guest': 0,
            'member': 1,
            'admin': 2,
            'super_admin': 3,
            'god_rights': 4
        }

        user_level = role_hierarchy.get(user_role, 0)

        if permission_type == 'view':
            required_level = role_hierarchy['member']
            if user_level >= required_level:
                return True, "Default: members can view"
            return False, "Default: only members and above can view"

        elif permission_type == 'edit':
            required_level = role_hierarchy['admin']
            if user_level >= required_level:
                return True, "Default: admins can edit"
            return False, "Default: only admins and above can edit"

        elif permission_type == 'delete':
            required_level = role_hierarchy['super_admin']
            if user_level >= required_level:
                return True, "Default: super admins can delete"
            return False, "Default: only super admins and above can delete"

        elif permission_type == 'assign':
            required_level = role_hierarchy['admin']
            if user_level >= required_level:
                return True, "Default: admins can assign"
            return False, "Default: only admins and above can assign"

        else:
            return False, f"Unknown permission type: {permission_type}"

    async def get_workflow_permissions(self, workflow_id: str, team_id: str) -> List[Dict]:
        """
        Get all permission grants for a workflow (Phase 5.2)

        Args:
            workflow_id: Workflow ID
            team_id: Team ID

        Returns:
            List of permission grants
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT permission_type, grant_type, grant_value, created_at, created_by
                FROM workflow_permissions
                WHERE workflow_id = ? AND team_id = ?
                ORDER BY permission_type, grant_type, grant_value
            """, (workflow_id, team_id))

            permissions = []
            for row in cursor.fetchall():
                permissions.append({
                    'permission_type': row['permission_type'],
                    'grant_type': row['grant_type'],
                    'grant_value': row['grant_value'],
                    'created_at': row['created_at'],
                    'created_by': row['created_by']
                })

            return permissions

        except Exception as e:
            logger.error(f"Failed to get workflow permissions: {e}")
            return []

    # ========================================================================
    # QUEUE ACCESS CONTROL METHODS (Phase 5.3)
    # ========================================================================

    async def create_queue(self, team_id: str, queue_name: str, queue_type: str, description: str, created_by: str) -> tuple[bool, str, str]:
        """
        Create a new queue (Phase 5.3)

        Args:
            team_id: Team ID
            queue_name: Display name for the queue
            queue_type: Type of queue (patient, medication, pharmacy, counseling, etc.)
            description: Description of the queue's purpose
            created_by: User ID who created the queue

        Returns:
            Tuple of (success: bool, message: str, queue_id: str)
        """
        try:
            # Generate unique queue ID
            import uuid
            queue_id = f"{queue_type.upper()}-{uuid.uuid4().hex[:8].upper()}"

            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO queues (queue_id, team_id, queue_name, queue_type, description, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (queue_id, team_id, queue_name, queue_type, description, created_by))

            self.conn.commit()

            logger.info(f"Created queue {queue_id} ({queue_name}) in team {team_id}")

            return True, f"Queue '{queue_name}' created successfully", queue_id

        except sqlite3.IntegrityError:
            return False, "Queue already exists", ""
        except Exception as e:
            logger.error(f"Failed to create queue: {e}")
            return False, str(e), ""

    async def add_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
        """
        Add queue access permission (Phase 5.3)

        Args:
            queue_id: Queue ID
            team_id: Team ID
            access_type: 'view', 'manage', 'assign'
            grant_type: 'role', 'job_role', 'user'
            grant_value: Depends on grant_type (role name, job role, or user_id)
            created_by: User ID who created this permission

        Returns:
            Tuple of (success: bool, message: str)
        """
        valid_access_types = ['view', 'manage', 'assign']
        valid_grant_types = ['role', 'job_role', 'user']

        if access_type not in valid_access_types:
            return False, f"Invalid access type. Must be one of: {', '.join(valid_access_types)}"

        if grant_type not in valid_grant_types:
            return False, f"Invalid grant type. Must be one of: {', '.join(valid_grant_types)}"

        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO queue_permissions (queue_id, team_id, access_type, grant_type, grant_value, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (queue_id, team_id, access_type, grant_type, grant_value, created_by))

            self.conn.commit()

            logger.info(f"Added {access_type} access for queue {queue_id}: {grant_type}={grant_value}")

            return True, f"Access granted: {grant_type}={grant_value} can {access_type}"

        except sqlite3.IntegrityError:
            return False, "Permission already exists"
        except Exception as e:
            logger.error(f"Failed to add queue permission: {e}")
            return False, str(e)

    async def remove_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
        """
        Remove queue access permission (Phase 5.3)

        Args:
            queue_id: Queue ID
            team_id: Team ID
            access_type: 'view', 'manage', 'assign'
            grant_type: 'role', 'job_role', 'user'
            grant_value: Depends on grant_type

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                DELETE FROM queue_permissions
                WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = ? AND grant_value = ?
            """, (queue_id, team_id, access_type, grant_type, grant_value))

            self.conn.commit()

            if cursor.rowcount == 0:
                return False, "Permission not found"

            logger.info(f"Removed {access_type} access for queue {queue_id}: {grant_type}={grant_value}")

            return True, f"Access revoked: {grant_type}={grant_value} can no longer {access_type}"

        except Exception as e:
            logger.error(f"Failed to remove queue permission: {e}")
            return False, str(e)

    async def check_queue_access(self, queue_id: str, team_id: str, user_id: str, access_type: str) -> tuple[bool, str]:
        """
        Check if a user has access to a queue (Phase 5.3)

        Checks in order:
        1. Founder Rights always have all access
        2. Explicit user grants
        3. Job role grants
        4. Role grants
        5. Default permissions (admins+ can manage, members+ can view)

        Args:
            queue_id: Queue ID
            team_id: Team ID
            user_id: User ID to check
            access_type: 'view', 'manage', 'assign'

        Returns:
            Tuple of (has_access: bool, reason: str)
        """
        try:
            cursor = self.conn.cursor()

            # Get user's role and job_role
            cursor.execute("""
                SELECT role, job_role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            member = cursor.fetchone()
            if not member:
                return False, "User not found in team"

            user_role = member['role']
            user_job_role = member['job_role'] or 'unassigned'

            # Founder Rights always have all access
            if user_role == 'god_rights':
                return True, "Founder Rights override"

            # Check for explicit user grant
            cursor.execute("""
                SELECT 1 FROM queue_permissions
                WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'user' AND grant_value = ?
            """, (queue_id, team_id, access_type, user_id))

            if cursor.fetchone():
                return True, f"User-specific {access_type} access"

            # Check for job role grant
            cursor.execute("""
                SELECT 1 FROM queue_permissions
                WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'job_role' AND grant_value = ?
            """, (queue_id, team_id, access_type, user_job_role))

            if cursor.fetchone():
                return True, f"Job role ({user_job_role}) {access_type} access"

            # Check for role grant
            cursor.execute("""
                SELECT 1 FROM queue_permissions
                WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'role' AND grant_value = ?
            """, (queue_id, team_id, access_type, user_role))

            if cursor.fetchone():
                return True, f"Role ({user_role}) {access_type} access"

            # Check if there are any explicit permissions defined for this queue
            cursor.execute("""
                SELECT COUNT(*) as count FROM queue_permissions
                WHERE queue_id = ? AND team_id = ? AND access_type = ?
            """, (queue_id, team_id, access_type))

            has_explicit_permissions = cursor.fetchone()['count'] > 0

            # If no explicit permissions, apply defaults
            if not has_explicit_permissions:
                return self._check_default_queue_access(user_role, access_type)

            # Explicit permissions exist but user doesn't match any
            return False, "No matching access grants"

        except Exception as e:
            logger.error(f"Failed to check queue access: {e}")
            return False, str(e)

    def _check_default_queue_access(self, user_role: str, access_type: str) -> tuple[bool, str]:
        """
        Default queue access permissions (Phase 5.3)

        Defaults when no explicit permissions are set:
        - VIEW: member and above
        - MANAGE: admin and above
        - ASSIGN: admin and above

        Args:
            user_role: User's role
            access_type: Access type to check

        Returns:
            Tuple of (has_access: bool, reason: str)
        """
        role_hierarchy = {
            'guest': 0,
            'member': 1,
            'admin': 2,
            'super_admin': 3,
            'god_rights': 4
        }

        role_level = role_hierarchy.get(user_role, 0)

        if access_type == 'view':
            # Members and above can view
            if role_level >= role_hierarchy['member']:
                return True, f"Default view access for {user_role}"
            return False, "Guests cannot view queues by default"

        elif access_type in ['manage', 'assign']:
            # Admins and above can manage/assign
            if role_level >= role_hierarchy['admin']:
                return True, f"Default {access_type} access for {user_role}"
            return False, f"Only admins and above can {access_type} by default"

        return False, f"Invalid access type: {access_type}"

    async def get_accessible_queues(self, team_id: str, user_id: str, access_type: str = 'view') -> List[Dict]:
        """
        Get all queues a user can access (Phase 5.3)

        Args:
            team_id: Team ID
            user_id: User ID
            access_type: 'view', 'manage', or 'assign' (default: 'view')

        Returns:
            List of accessible queues with details
        """
        try:
            cursor = self.conn.cursor()

            # Get all active queues for this team
            cursor.execute("""
                SELECT queue_id, queue_name, queue_type, description, created_at, created_by
                FROM queues
                WHERE team_id = ? AND is_active = 1
                ORDER BY queue_name
            """, (team_id,))

            accessible_queues = []
            for row in cursor.fetchall():
                queue_id = row['queue_id']

                # Check if user has access
                has_access, reason = self.check_queue_access(queue_id, team_id, user_id, access_type)

                if has_access:
                    accessible_queues.append({
                        'queue_id': queue_id,
                        'queue_name': row['queue_name'],
                        'queue_type': row['queue_type'],
                        'description': row['description'],
                        'created_at': row['created_at'],
                        'created_by': row['created_by'],
                        'access_reason': reason
                    })

            return accessible_queues

        except Exception as e:
            logger.error(f"Failed to get accessible queues: {e}")
            return []

    async def get_queue_permissions(self, queue_id: str, team_id: str) -> List[Dict]:
        """
        Get all permission grants for a queue (Phase 5.3)

        Args:
            queue_id: Queue ID
            team_id: Team ID

        Returns:
            List of permission grants
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT id, access_type, grant_type, grant_value, created_at, created_by
                FROM queue_permissions
                WHERE queue_id = ? AND team_id = ?
                ORDER BY access_type, grant_type, grant_value
            """, (queue_id, team_id))

            permissions = []
            for row in cursor.fetchall():
                permissions.append({
                    'id': row['id'],
                    'access_type': row['access_type'],
                    'grant_type': row['grant_type'],
                    'grant_value': row['grant_value'],
                    'created_at': row['created_at'],
                    'created_by': row['created_by']
                })

            return permissions

        except Exception as e:
            logger.error(f"Failed to get queue permissions: {e}")
            return []

    async def get_queue(self, queue_id: str, team_id: str) -> Optional[Dict]:
        """
        Get queue details (Phase 5.3)

        Args:
            queue_id: Queue ID
            team_id: Team ID

        Returns:
            Queue details or None if not found
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT queue_id, queue_name, queue_type, description, created_at, created_by, is_active
                FROM queues
                WHERE queue_id = ? AND team_id = ?
            """, (queue_id, team_id))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'queue_id': row['queue_id'],
                'queue_name': row['queue_name'],
                'queue_type': row['queue_type'],
                'description': row['description'],
                'created_at': row['created_at'],
                'created_by': row['created_by'],
                'is_active': bool(row['is_active'])
            }

        except Exception as e:
            logger.error(f"Failed to get queue: {e}")
            return None

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
    def _get_vault_encryption_key(self, team_id: str) -> bytes:
        """
        Get or generate encryption key for team vault (Phase 6.2)

        In production, this should use a proper key management system.
        For now, we derive a key from team_id.
        """
        import hashlib
        from cryptography.fernet import Fernet
        import base64

        # Derive a consistent key from team_id
        key_material = hashlib.sha256(f"elohimos_vault_{team_id}".encode()).digest()
        # Fernet requires 32 url-safe base64-encoded bytes
        key = base64.urlsafe_b64encode(key_material)
        return key

    def _encrypt_content(self, content: str, team_id: str) -> tuple[str, str]:
        """
        Encrypt vault content (Phase 6.2)

        Returns:
            Tuple of (encrypted_content, key_hash)
        """
        try:
            from cryptography.fernet import Fernet
            import hashlib

            key = self._get_vault_encryption_key(team_id)
            fernet = Fernet(key)

            # Encrypt content
            encrypted = fernet.encrypt(content.encode())
            encrypted_b64 = encrypted.decode()

            # Create key hash for verification
            key_hash = hashlib.sha256(key).hexdigest()

            return encrypted_b64, key_hash

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def _decrypt_content(self, encrypted_content: str, team_id: str) -> str:
        """
        Decrypt vault content (Phase 6.2)

        Returns:
            Decrypted content string
        """
        try:
            from cryptography.fernet import Fernet

            key = self._get_vault_encryption_key(team_id)
            fernet = Fernet(key)

            # Decrypt content
            decrypted = fernet.decrypt(encrypted_content.encode())
            return decrypted.decode()

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def create_vault_item(
        self,
        team_id: str,
        item_name: str,
        item_type: str,
        content: str,
        created_by: str,
        mime_type: str = None,
        metadata: str = None
    ) -> tuple[bool, str, str]:
        """
        Create a new vault item (Phase 6.2)

        Args:
            team_id: Team ID
            item_name: Name of the item
            item_type: Type (document, image, file, note, patient_record, etc.)
            content: Content to encrypt and store
            created_by: User ID creating the item
            mime_type: MIME type if applicable
            metadata: JSON metadata string

        Returns:
            Tuple of (success: bool, message: str, item_id: str)
        """
        try:
            import uuid

            cursor = self.conn.cursor()

            # Generate unique item ID
            item_id = str(uuid.uuid4()).upper()[:8]

            # Encrypt content
            encrypted_content, key_hash = self._encrypt_content(content, team_id)

            # Calculate file size
            file_size = len(content.encode())

            # Insert vault item
            cursor.execute("""
                INSERT INTO team_vault_items (
                    item_id, team_id, item_name, item_type,
                    encrypted_content, encryption_key_hash,
                    file_size, mime_type, created_by, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, team_id, item_name, item_type,
                encrypted_content, key_hash,
                file_size, mime_type, created_by, metadata
            ))

            self.conn.commit()

            logger.info(f"Created vault item {item_id} for team {team_id}")
            return True, f"Vault item created successfully", item_id

        except Exception as e:
            logger.error(f"Failed to create vault item: {e}")
            return False, str(e), ""

    def update_vault_item(
        self,
        item_id: str,
        team_id: str,
        content: str,
        updated_by: str
    ) -> tuple[bool, str]:
        """
        Update vault item content (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID
            content: New content
            updated_by: User ID updating

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime

            cursor = self.conn.cursor()

            # Check if item exists and not deleted
            cursor.execute("""
                SELECT id FROM team_vault_items
                WHERE item_id = ? AND team_id = ? AND is_deleted = 0
            """, (item_id, team_id))

            if not cursor.fetchone():
                return False, "Vault item not found or deleted"

            # Encrypt new content
            encrypted_content, key_hash = self._encrypt_content(content, team_id)

            # Calculate new file size
            file_size = len(content.encode())

            # Update item
            cursor.execute("""
                UPDATE team_vault_items
                SET encrypted_content = ?,
                    encryption_key_hash = ?,
                    file_size = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE item_id = ? AND team_id = ?
            """, (
                encrypted_content, key_hash, file_size,
                datetime.now().isoformat(), updated_by,
                item_id, team_id
            ))

            self.conn.commit()

            logger.info(f"Updated vault item {item_id}")
            return True, "Vault item updated successfully"

        except Exception as e:
            logger.error(f"Failed to update vault item: {e}")
            return False, str(e)

    def delete_vault_item(
        self,
        item_id: str,
        team_id: str,
        deleted_by: str
    ) -> tuple[bool, str]:
        """
        Soft delete vault item (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID
            deleted_by: User ID deleting

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime

            cursor = self.conn.cursor()

            # Soft delete
            cursor.execute("""
                UPDATE team_vault_items
                SET is_deleted = 1,
                    deleted_at = ?,
                    deleted_by = ?
                WHERE item_id = ? AND team_id = ? AND is_deleted = 0
            """, (datetime.now().isoformat(), deleted_by, item_id, team_id))

            if cursor.rowcount == 0:
                return False, "Vault item not found or already deleted"

            self.conn.commit()

            logger.info(f"Deleted vault item {item_id}")
            return True, "Vault item deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete vault item: {e}")
            return False, str(e)

    def get_vault_item(
        self,
        item_id: str,
        team_id: str,
        decrypt: bool = True
    ) -> Optional[Dict]:
        """
        Get vault item and optionally decrypt (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID
            decrypt: Whether to decrypt content

        Returns:
            Dict with item details or None
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT item_id, team_id, item_name, item_type,
                       encrypted_content, file_size, mime_type,
                       created_at, created_by, updated_at, updated_by,
                       metadata
                FROM team_vault_items
                WHERE item_id = ? AND team_id = ? AND is_deleted = 0
            """, (item_id, team_id))

            row = cursor.fetchone()
            if not row:
                return None

            item = dict(row)

            # Decrypt content if requested
            if decrypt and item['encrypted_content']:
                try:
                    item['content'] = self._decrypt_content(item['encrypted_content'], team_id)
                    del item['encrypted_content']
                except Exception as e:
                    logger.error(f"Failed to decrypt vault item {item_id}: {e}")
                    item['content'] = "[DECRYPTION ERROR]"
                    del item['encrypted_content']

            return item

        except Exception as e:
            logger.error(f"Failed to get vault item: {e}")
            return None

    def list_vault_items(
        self,
        team_id: str,
        user_id: str,
        item_type: str = None,
        include_deleted: bool = False
    ) -> List[Dict]:
        """
        List vault items accessible to user (Phase 6.2)

        Args:
            team_id: Team ID
            user_id: User ID requesting
            item_type: Filter by item type (optional)
            include_deleted: Include soft-deleted items

        Returns:
            List of vault items (without decrypted content)
        """
        try:
            cursor = self.conn.cursor()

            # Build query
            query = """
                SELECT item_id, item_name, item_type, file_size, mime_type,
                       created_at, created_by, updated_at, updated_by, metadata
                FROM team_vault_items
                WHERE team_id = ?
            """
            params = [team_id]

            if not include_deleted:
                query += " AND is_deleted = 0"

            if item_type:
                query += " AND item_type = ?"
                params.append(item_type)

            query += " ORDER BY created_at DESC"

            cursor.execute(query, params)

            items = []
            for row in cursor.fetchall():
                # Check if user has permission to view
                can_view, _ = self.check_vault_permission(
                    item_id=row['item_id'],
                    team_id=team_id,
                    user_id=user_id,
                    permission_type='read'
                )

                if can_view:
                    items.append(dict(row))

            return items

        except Exception as e:
            logger.error(f"Failed to list vault items: {e}")
            return []

    def check_vault_permission(
        self,
        item_id: str,
        team_id: str,
        user_id: str,
        permission_type: str
    ) -> tuple[bool, str]:
        """
        Check if user has vault item permission (Phase 6.2)

        Permission priority: Founder Rights > explicit user > job_role > role > defaults

        Args:
            item_id: Item ID
            team_id: Team ID
            user_id: User ID
            permission_type: Permission type (read, write, admin)

        Returns:
            Tuple of (has_permission: bool, reason: str)
        """
        try:
            cursor = self.conn.cursor()

            # Check Founder Rights
            has_god_rights, _ = self.check_god_rights(user_id)
            if has_god_rights:
                return True, "Founder Rights override"

            # Get user's role and job_role
            cursor.execute("""
                SELECT role, job_role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            member = cursor.fetchone()
            if not member:
                return False, "User not a member of team"

            user_role = member['role']
            user_job_role = member['job_role'] or 'unassigned'

            # Check explicit user permission
            cursor.execute("""
                SELECT permission_type FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ? AND grant_type = 'user' AND grant_value = ?
            """, (item_id, team_id, user_id))

            user_perms = [row['permission_type'] for row in cursor.fetchall()]
            if permission_type in user_perms:
                return True, f"Explicit user permission"

            # Check job_role permission
            cursor.execute("""
                SELECT permission_type FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ? AND grant_type = 'job_role' AND grant_value = ?
            """, (item_id, team_id, user_job_role))

            job_perms = [row['permission_type'] for row in cursor.fetchall()]
            if permission_type in job_perms:
                return True, f"Job role permission ({user_job_role})"

            # Check role permission
            cursor.execute("""
                SELECT permission_type FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ? AND grant_type = 'role' AND grant_value = ?
            """, (item_id, team_id, user_role))

            role_perms = [row['permission_type'] for row in cursor.fetchall()]
            if permission_type in role_perms:
                return True, f"Role permission ({user_role})"

            # Default permissions
            # READ: member+, WRITE/ADMIN: admin+
            if permission_type == 'read':
                if user_role in ['member', 'admin', 'super_admin']:
                    return True, f"Default read permission for {user_role}"
            elif permission_type in ['write', 'admin']:
                if user_role in ['admin', 'super_admin']:
                    return True, f"Default {permission_type} permission for {user_role}"

            return False, "No permission granted"

        except Exception as e:
            logger.error(f"Failed to check vault permission: {e}")
            return False, str(e)

    def add_vault_permission(
        self,
        item_id: str,
        team_id: str,
        permission_type: str,
        grant_type: str,
        grant_value: str,
        created_by: str
    ) -> tuple[bool, str]:
        """
        Add vault item permission (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID
            permission_type: Permission type (read, write, admin)
            grant_type: Grant type (role, job_role, user)
            grant_value: Grant value
            created_by: User ID creating permission

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cursor = self.conn.cursor()

            # Validate permission type
            if permission_type not in ['read', 'write', 'admin']:
                return False, "Invalid permission type. Must be: read, write, admin"

            # Validate grant type
            if grant_type not in ['role', 'job_role', 'user']:
                return False, "Invalid grant type. Must be: role, job_role, user"

            # Check if permission already exists
            cursor.execute("""
                SELECT id FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ? AND permission_type = ?
                  AND grant_type = ? AND grant_value = ?
            """, (item_id, team_id, permission_type, grant_type, grant_value))

            if cursor.fetchone():
                return False, "Permission already exists"

            # Add permission
            cursor.execute("""
                INSERT INTO team_vault_permissions (
                    item_id, team_id, permission_type,
                    grant_type, grant_value, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item_id, team_id, permission_type, grant_type, grant_value, created_by))

            self.conn.commit()

            logger.info(f"Added {permission_type} permission for {grant_type}:{grant_value} to item {item_id}")
            return True, "Permission added successfully"

        except Exception as e:
            logger.error(f"Failed to add vault permission: {e}")
            return False, str(e)

    def remove_vault_permission(
        self,
        item_id: str,
        team_id: str,
        permission_type: str,
        grant_type: str,
        grant_value: str
    ) -> tuple[bool, str]:
        """
        Remove vault item permission (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID
            permission_type: Permission type
            grant_type: Grant type
            grant_value: Grant value

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                DELETE FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ? AND permission_type = ?
                  AND grant_type = ? AND grant_value = ?
            """, (item_id, team_id, permission_type, grant_type, grant_value))

            if cursor.rowcount == 0:
                return False, "Permission not found"

            self.conn.commit()

            logger.info(f"Removed {permission_type} permission for {grant_type}:{grant_value} from item {item_id}")
            return True, "Permission removed successfully"

        except Exception as e:
            logger.error(f"Failed to remove vault permission: {e}")
            return False, str(e)

    def get_vault_permissions(
        self,
        item_id: str,
        team_id: str
    ) -> List[Dict]:
        """
        Get all permissions for a vault item (Phase 6.2)

        Args:
            item_id: Item ID
            team_id: Team ID

        Returns:
            List of permission grants
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT permission_type, grant_type, grant_value, created_at, created_by
                FROM team_vault_permissions
                WHERE item_id = ? AND team_id = ?
                ORDER BY created_at DESC
            """, (item_id, team_id))

            permissions = []
            for row in cursor.fetchall():
                permissions.append(dict(row))

            return permissions

        except Exception as e:
            logger.error(f"Failed to get vault permissions: {e}")
            return []

    async def close(self) -> None:
        """Close database connection"""
        if self.conn:
            await asyncio.to_thread(self.conn.close)
