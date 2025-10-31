#!/usr/bin/env python3
"""
Team Management Service for ElohimOS
Handles team creation, member management, and invite codes

Copyright (c) 2025 MagnetarAI, LLC
"""

import sqlite3
import logging
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Database path for team data
TEAM_DB = Path(".neutron_data/teams.db")
TEAM_DB.parent.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


# Pydantic models for API
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


class TeamManager:
    """
    Manages team creation, member management, and invite codes
    """

    def __init__(self):
        self.conn = sqlite3.connect(str(TEAM_DB), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

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

        self.conn.commit()
        logger.info("Team database initialized")

    def generate_team_id(self, team_name: str) -> str:
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
        cursor = self.conn.cursor()
        cursor.execute("SELECT team_id FROM teams WHERE team_id = ?", (team_id,))
        if cursor.fetchone():
            # Collision, try again with different suffix
            return self.generate_team_id(team_name)

        return team_id

    def generate_invite_code(self, team_id: str, expires_days: Optional[int] = None) -> str:
        """
        Generate a shareable invite code
        Format: XXXXX-XXXXX-XXXXX (e.g., A7B3C-D9E2F-G1H4I)
        """
        # Generate 3 groups of 5 characters
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
            parts.append(part)

        code = '-'.join(parts)

        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO invite_codes (code, team_id, expires_at)
                VALUES (?, ?, ?)
            """, (code, team_id, expires_at))
            self.conn.commit()
            return code
        except sqlite3.IntegrityError:
            # Code collision, try again
            return self.generate_invite_code(team_id, expires_days)

    def create_team(self, name: str, creator_user_id: str, description: Optional[str] = None) -> Dict:
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
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO teams (team_id, name, description, created_by)
                VALUES (?, ?, ?, ?)
            """, (team_id, name, description, creator_user_id))

            # Add creator as Super Admin member
            cursor.execute("""
                INSERT INTO team_members (team_id, user_id, role)
                VALUES (?, ?, ?)
            """, (team_id, creator_user_id, 'super_admin'))

            self.conn.commit()

            # Generate invite code (expires in 30 days)
            invite_code = self.generate_invite_code(team_id, expires_days=30)

            # Get created team details
            cursor.execute("""
                SELECT team_id, name, description, created_at, created_by
                FROM teams
                WHERE team_id = ?
            """, (team_id,))

            team_row = cursor.fetchone()

            return {
                'team_id': team_row['team_id'],
                'name': team_row['name'],
                'description': team_row['description'],
                'created_at': team_row['created_at'],
                'created_by': team_row['created_by'],
                'invite_code': invite_code
            }

        except Exception as e:
            logger.error(f"Failed to create team: {e}")
            raise

    def get_team(self, team_id: str) -> Optional[Dict]:
        """Get team details by ID"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT team_id, name, description, created_at, created_by
                FROM teams
                WHERE team_id = ?
            """, (team_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'team_id': row['team_id'],
                'name': row['name'],
                'description': row['description'],
                'created_at': row['created_at'],
                'created_by': row['created_by']
            }

        except Exception as e:
            logger.error(f"Failed to get team: {e}")
            return None

    def get_team_members(self, team_id: str) -> List[Dict]:
        """Get all members of a team"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT user_id, role, joined_at
                FROM team_members
                WHERE team_id = ?
                ORDER BY joined_at ASC
            """, (team_id,))

            members = []
            for row in cursor.fetchall():
                members.append({
                    'user_id': row['user_id'],
                    'role': row['role'],
                    'joined_at': row['joined_at']
                })

            return members

        except Exception as e:
            logger.error(f"Failed to get team members: {e}")
            return []

    def get_user_teams(self, user_id: str) -> List[Dict]:
        """Get all teams a user is a member of"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT t.team_id, t.name, t.description, t.created_at, tm.role
                FROM teams t
                JOIN team_members tm ON t.team_id = tm.team_id
                WHERE tm.user_id = ?
                ORDER BY tm.joined_at DESC
            """, (user_id,))

            teams = []
            for row in cursor.fetchall():
                teams.append({
                    'team_id': row['team_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'created_at': row['created_at'],
                    'user_role': row['role']
                })

            return teams

        except Exception as e:
            logger.error(f"Failed to get user teams: {e}")
            return []

    def get_active_invite_code(self, team_id: str) -> Optional[str]:
        """Get active (non-expired, unused) invite code for team"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT code, expires_at
                FROM invite_codes
                WHERE team_id = ?
                  AND used = FALSE
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC
                LIMIT 1
            """, (team_id,))

            row = cursor.fetchone()
            return row['code'] if row else None

        except Exception as e:
            logger.error(f"Failed to get invite code: {e}")
            return None

    def regenerate_invite_code(self, team_id: str, expires_days: int = 30) -> str:
        """Generate a new invite code for team (invalidates old ones)"""
        try:
            # Mark existing codes as used
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE invite_codes
                SET used = TRUE
                WHERE team_id = ? AND used = FALSE
            """, (team_id,))
            self.conn.commit()

            # Generate new code
            return self.generate_invite_code(team_id, expires_days)

        except Exception as e:
            logger.error(f"Failed to regenerate invite code: {e}")
            raise

    def validate_invite_code(self, invite_code: str) -> Optional[str]:
        """
        Validate invite code and return team_id if valid

        Returns:
            team_id if code is valid and not expired/used, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT team_id, expires_at, used
                FROM invite_codes
                WHERE code = ?
            """, (invite_code,))

            row = cursor.fetchone()

            if not row:
                logger.warning(f"Invite code not found: {invite_code}")
                return None

            # Check if already used
            if row['used']:
                logger.warning(f"Invite code already used: {invite_code}")
                return None

            # Check if expired
            if row['expires_at']:
                from datetime import datetime
                expires_at = datetime.fromisoformat(row['expires_at'])
                if datetime.now() > expires_at:
                    logger.warning(f"Invite code expired: {invite_code}")
                    return None

            return row['team_id']

        except Exception as e:
            logger.error(f"Failed to validate invite code: {e}")
            return None

    def join_team(self, team_id: str, user_id: str, role: str = 'member') -> bool:
        """
        Add user to team

        Args:
            team_id: Team to join
            user_id: User joining
            role: Role to assign (default: member)

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check if user is already a member
            cursor.execute("""
                SELECT id FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            if cursor.fetchone():
                logger.warning(f"User {user_id} already member of team {team_id}")
                return False

            # Add user as member
            cursor.execute("""
                INSERT INTO team_members (team_id, user_id, role)
                VALUES (?, ?, ?)
            """, (team_id, user_id, role))

            self.conn.commit()
            logger.info(f"User {user_id} joined team {team_id} as {role}")
            return True

        except Exception as e:
            logger.error(f"Failed to join team: {e}")
            return False

    @staticmethod
    def get_max_super_admins(team_size: int) -> int:
        """
        Calculate maximum allowed Super Admins based on team size

        Args:
            team_size: Total number of team members

        Returns:
            Maximum number of Super Admins allowed
        """
        if team_size <= 5:
            return 1
        elif team_size <= 15:
            return 2
        elif team_size <= 30:
            return 3
        elif team_size <= 50:
            return 4
        else:
            return 5

    def count_role(self, team_id: str, role: str) -> int:
        """
        Count members with a specific role in a team

        Args:
            team_id: Team ID
            role: Role to count (e.g., 'super_admin', 'admin', 'member')

        Returns:
            Number of members with that role
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM team_members
                WHERE team_id = ? AND role = ?
            """, (team_id, role))

            row = cursor.fetchone()
            return row['count'] if row else 0

        except Exception as e:
            logger.error(f"Failed to count role {role}: {e}")
            return 0

    def count_super_admins(self, team_id: str) -> int:
        """Count current Super Admins in team"""
        return self.count_role(team_id, 'super_admin')

    def get_team_size(self, team_id: str) -> int:
        """Get total number of members in team"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM team_members
                WHERE team_id = ?
            """, (team_id,))

            row = cursor.fetchone()
            return row['count'] if row else 0

        except Exception as e:
            logger.error(f"Failed to get team size: {e}")
            return 0

    def can_promote_to_super_admin(self, team_id: str, requesting_user_role: str = None) -> tuple[bool, str]:
        """
        Check if team can have another Super Admin

        Args:
            team_id: Team to check
            requesting_user_role: Role of user making the request (optional)

        Returns:
            Tuple of (can_promote: bool, reason: str)
        """
        try:
            # God Rights can always override
            if requesting_user_role == 'god_rights':
                return True, "God Rights override"

            team_size = self.get_team_size(team_id)
            current_super_admins = self.count_super_admins(team_id)
            max_super_admins = self.get_max_super_admins(team_size)

            if current_super_admins >= max_super_admins:
                return False, f"Team size {team_size} allows max {max_super_admins} Super Admin(s), currently have {current_super_admins}"

            return True, "Promotion allowed"

        except Exception as e:
            logger.error(f"Failed to check Super Admin limit: {e}")
            return False, str(e)

    def update_member_role(self, team_id: str, user_id: str, new_role: str, requesting_user_role: str = None) -> tuple[bool, str]:
        """
        Update a team member's role with validation

        Args:
            team_id: Team ID
            user_id: User whose role to update
            new_role: New role to assign
            requesting_user_role: Role of user making the request (for God Rights check)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user is member
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if not row:
                return False, f"User {user_id} is not a member of team {team_id}"

            current_role = row['role']

            # If promoting to Super Admin, check limits
            if new_role == 'super_admin' and current_role != 'super_admin':
                can_promote, reason = self.can_promote_to_super_admin(team_id, requesting_user_role)
                if not can_promote:
                    return False, reason

            # If demoting a Super Admin, check if they're the last one
            if current_role == 'super_admin' and new_role != 'super_admin':
                # God Rights can override
                if requesting_user_role != 'god_rights':
                    current_super_admins = self.count_super_admins(team_id)
                    if current_super_admins <= 1:
                        return False, "You're the last Super Admin. Promote an Admin first."

            # Update role
            cursor.execute("""
                UPDATE team_members
                SET role = ?
                WHERE team_id = ? AND user_id = ?
            """, (new_role, team_id, user_id))

            self.conn.commit()
            logger.info(f"Updated {user_id} role from {current_role} to {new_role} in team {team_id}")
            return True, f"Role updated to {new_role}"

        except Exception as e:
            logger.error(f"Failed to update member role: {e}")
            return False, str(e)

    def get_days_since_joined(self, team_id: str, user_id: str) -> Optional[int]:
        """
        Calculate days since user joined the team

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            Number of days since joining, or None if user not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT joined_at FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if not row:
                return None

            from datetime import datetime
            joined_at = datetime.fromisoformat(row['joined_at'])
            days_elapsed = (datetime.now() - joined_at).days

            return days_elapsed

        except Exception as e:
            logger.error(f"Failed to calculate days since joined: {e}")
            return None

    def check_auto_promotion_eligibility(self, team_id: str, user_id: str, required_days: int = 7) -> tuple[bool, str, int]:
        """
        Check if a guest is eligible for auto-promotion to member

        Args:
            team_id: Team ID
            user_id: User ID
            required_days: Days required for auto-promotion (default: 7)

        Returns:
            Tuple of (is_eligible: bool, reason: str, days_elapsed: int)
        """
        try:
            # Check current role
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT role, joined_at FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if not row:
                return False, "User not found in team", 0

            current_role = row['role']

            # Only guests are eligible for auto-promotion
            if current_role != 'guest':
                return False, f"User is already {current_role}, not a guest", 0

            # Calculate days
            days_elapsed = self.get_days_since_joined(team_id, user_id)
            if days_elapsed is None:
                return False, "Failed to calculate days elapsed", 0

            if days_elapsed >= required_days:
                return True, f"Eligible after {days_elapsed} days (required: {required_days})", days_elapsed
            else:
                return False, f"Not eligible yet: {days_elapsed} days (required: {required_days})", days_elapsed

        except Exception as e:
            logger.error(f"Failed to check auto-promotion eligibility: {e}")
            return False, str(e), 0

    def auto_promote_guests(self, team_id: str, required_days: int = 7) -> List[Dict]:
        """
        Auto-promote all eligible guests in a team to members

        Args:
            team_id: Team ID
            required_days: Days required for auto-promotion (default: 7)

        Returns:
            List of dictionaries with promotion results
        """
        try:
            # Find all guests in team
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT user_id, joined_at FROM team_members
                WHERE team_id = ? AND role = 'guest'
            """, (team_id,))

            guests = cursor.fetchall()
            results = []

            from datetime import datetime
            for guest in guests:
                user_id = guest['user_id']
                joined_at = datetime.fromisoformat(guest['joined_at'])
                days_elapsed = (datetime.now() - joined_at).days

                if days_elapsed >= required_days:
                    # Auto-promote to member
                    success, message = self.update_member_role(team_id, user_id, 'member')
                    results.append({
                        'user_id': user_id,
                        'days_elapsed': days_elapsed,
                        'promoted': success,
                        'message': message if success else f"Failed: {message}"
                    })
                    logger.info(f"Auto-promoted {user_id} to member after {days_elapsed} days")

            return results

        except Exception as e:
            logger.error(f"Failed to auto-promote guests: {e}")
            return []

    def instant_promote_guest(self, team_id: str, user_id: str, approved_by_user_id: str, auth_type: str = 'real_password') -> tuple[bool, str]:
        """
        Instantly promote a guest to member (Phase 4.2)

        Bypasses 7-day wait when Super Admin approves with real password + biometric
        Access granted: Vault, Chat, Automation from now forward

        Args:
            team_id: Team ID
            user_id: Guest user to promote
            approved_by_user_id: Super Admin who approved
            auth_type: 'real_password' or 'decoy_password' (for audit)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Verify guest exists
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if not row:
                return False, f"User {user_id} not found in team"

            if row['role'] != 'guest':
                return False, f"User is already {row['role']}, not a guest"

            # Promote immediately
            success, message = self.update_member_role(team_id, user_id, 'member')

            if success:
                logger.info(f"Instant-promoted {user_id} to member (approved by {approved_by_user_id}, auth: {auth_type})")
                return True, f"Instantly promoted to member. Access granted from now forward."

            return False, message

        except Exception as e:
            logger.error(f"Failed instant promotion: {e}")
            return False, str(e)

    def schedule_delayed_promotion(self, team_id: str, user_id: str, delay_days: int = 21, approved_by_user_id: str = None, reason: str = "Decoy password delay") -> tuple[bool, str]:
        """
        Schedule a delayed promotion (Phase 4.3)

        Used when Super Admin approves with decoy password + biometric
        Promotion delayed by X days (default 21) as safety mechanism
        Access: Chat & Automation from now, Vault delayed

        Args:
            team_id: Team ID
            user_id: Guest user to promote
            delay_days: Days to delay promotion (default: 21)
            approved_by_user_id: Super Admin who approved
            reason: Reason for delay

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Verify guest exists
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if not row:
                return False, f"User {user_id} not found in team"

            if row['role'] != 'guest':
                return False, f"User is already {row['role']}, not a guest"

            # Check if already has pending delayed promotion
            cursor.execute("""
                SELECT id FROM delayed_promotions
                WHERE team_id = ? AND user_id = ? AND executed = FALSE
            """, (team_id, user_id))

            if cursor.fetchone():
                return False, f"User already has a pending delayed promotion"

            # Schedule delayed promotion
            from datetime import datetime, timedelta
            execute_at = datetime.now() + timedelta(days=delay_days)

            cursor.execute("""
                INSERT INTO delayed_promotions (team_id, user_id, from_role, to_role, execute_at, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (team_id, user_id, 'guest', 'member', execute_at, reason))

            self.conn.commit()
            logger.info(f"Scheduled delayed promotion for {user_id} (execute at {execute_at}, approved by {approved_by_user_id})")

            return True, f"Promotion scheduled for {execute_at.strftime('%Y-%m-%d')} ({delay_days} days). Chat & Automation access granted now. Vault access on promotion date."

        except Exception as e:
            logger.error(f"Failed to schedule delayed promotion: {e}")
            return False, str(e)

    def execute_delayed_promotions(self, team_id: str = None) -> List[Dict]:
        """
        Execute all pending delayed promotions that are due

        Can be called by cron job or manually

        Args:
            team_id: Optional team ID to limit execution to specific team

        Returns:
            List of execution results
        """
        try:
            from datetime import datetime
            cursor = self.conn.cursor()

            # Find all pending promotions that are due
            if team_id:
                cursor.execute("""
                    SELECT id, team_id, user_id, from_role, to_role, execute_at
                    FROM delayed_promotions
                    WHERE team_id = ? AND executed = FALSE AND execute_at <= ?
                """, (team_id, datetime.now()))
            else:
                cursor.execute("""
                    SELECT id, team_id, user_id, from_role, to_role, execute_at
                    FROM delayed_promotions
                    WHERE executed = FALSE AND execute_at <= ?
                """, (datetime.now(),))

            pending = cursor.fetchall()
            results = []

            for promo in pending:
                # Execute promotion
                success, message = self.update_member_role(
                    promo['team_id'],
                    promo['user_id'],
                    promo['to_role']
                )

                if success:
                    # Mark as executed
                    cursor.execute("""
                        UPDATE delayed_promotions
                        SET executed = TRUE, executed_at = ?
                        WHERE id = ?
                    """, (datetime.now(), promo['id']))
                    self.conn.commit()

                results.append({
                    'user_id': promo['user_id'],
                    'team_id': promo['team_id'],
                    'from_role': promo['from_role'],
                    'to_role': promo['to_role'],
                    'executed': success,
                    'message': message
                })

                logger.info(f"Executed delayed promotion: {promo['user_id']} -> {promo['to_role']}")

            return results

        except Exception as e:
            logger.error(f"Failed to execute delayed promotions: {e}")
            return []

    def update_last_seen(self, team_id: str, user_id: str) -> tuple[bool, str]:
        """
        Update last_seen timestamp for a team member (Phase 3.3)

        Should be called on every user activity to track online status

        Args:
            team_id: Team ID
            user_id: User ID to update

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime
            cursor = self.conn.cursor()

            cursor.execute("""
                UPDATE team_members
                SET last_seen = ?
                WHERE team_id = ? AND user_id = ?
            """, (datetime.now(), team_id, user_id))

            self.conn.commit()

            if cursor.rowcount == 0:
                return False, "User not found in team"

            return True, "Last seen updated"

        except Exception as e:
            logger.error(f"Failed to update last_seen: {e}")
            return False, str(e)

    def check_super_admin_offline(self, team_id: str, offline_threshold_minutes: int = 5) -> List[Dict]:
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

    def promote_admin_temporarily(self, team_id: str, offline_super_admin_id: str, requesting_user_role: str = None) -> tuple[bool, str]:
        """
        Temporarily promote an admin to super_admin when original is offline (Phase 3.3)

        Finds the most senior admin (earliest joined_at) and promotes them temporarily
        Logs the promotion in temp_promotions table for later approval/revert

        Args:
            team_id: Team ID
            offline_super_admin_id: The super_admin who went offline
            requesting_user_role: Role of requester (for God Rights override)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime
            cursor = self.conn.cursor()

            # Find most senior admin (earliest joined_at)
            cursor.execute("""
                SELECT user_id, joined_at FROM team_members
                WHERE team_id = ? AND role = 'admin'
                ORDER BY joined_at ASC
                LIMIT 1
            """, (team_id,))

            admin = cursor.fetchone()
            if not admin:
                return False, "No admins available for temporary promotion"

            promoted_admin_id = admin['user_id']

            # Check if this admin already has an active temp promotion
            cursor.execute("""
                SELECT id FROM temp_promotions
                WHERE team_id = ? AND promoted_admin_id = ? AND status = 'active'
            """, (team_id, promoted_admin_id))

            if cursor.fetchone():
                return False, f"Admin {promoted_admin_id} already has active temp promotion"

            # Promote admin to super_admin
            success, message = self.update_member_role(team_id, promoted_admin_id, 'super_admin', requesting_user_role)

            if not success:
                return False, f"Failed to promote: {message}"

            # Log in temp_promotions table
            cursor.execute("""
                INSERT INTO temp_promotions (team_id, original_super_admin_id, promoted_admin_id, reason, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (team_id, offline_super_admin_id, promoted_admin_id, "Super Admin offline failsafe"))

            self.conn.commit()

            logger.info(f"Temporarily promoted {promoted_admin_id} to super_admin (original: {offline_super_admin_id})")

            return True, f"Temporarily promoted {promoted_admin_id} to Super Admin"

        except Exception as e:
            logger.error(f"Failed temporary promotion: {e}")
            return False, str(e)

    def get_pending_temp_promotions(self, team_id: str) -> List[Dict]:
        """
        Get all pending temporary promotions for a team (Phase 3.3)

        Args:
            team_id: Team ID

        Returns:
            List of active temp promotions awaiting approval
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT id, original_super_admin_id, promoted_admin_id, promoted_at, reason, status
                FROM temp_promotions
                WHERE team_id = ? AND status = 'active'
            """, (team_id,))

            promotions = []
            for row in cursor.fetchall():
                promotions.append({
                    'id': row['id'],
                    'original_super_admin_id': row['original_super_admin_id'],
                    'promoted_admin_id': row['promoted_admin_id'],
                    'promoted_at': row['promoted_at'],
                    'reason': row['reason'],
                    'status': row['status']
                })

            return promotions

        except Exception as e:
            logger.error(f"Failed to get temp promotions: {e}")
            return []

    def approve_temp_promotion(self, team_id: str, temp_promotion_id: int, approved_by: str) -> tuple[bool, str]:
        """
        Approve a temporary promotion, making it permanent (Phase 3.3)

        Args:
            team_id: Team ID
            temp_promotion_id: ID from temp_promotions table
            approved_by: User ID who approved (typically the returning super admin)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime
            cursor = self.conn.cursor()

            # Get promotion details
            cursor.execute("""
                SELECT promoted_admin_id, original_super_admin_id, status
                FROM temp_promotions
                WHERE id = ? AND team_id = ?
            """, (temp_promotion_id, team_id))

            promo = cursor.fetchone()
            if not promo:
                return False, "Temporary promotion not found"

            if promo['status'] != 'active':
                return False, f"Promotion already {promo['status']}"

            # Mark as approved
            cursor.execute("""
                UPDATE temp_promotions
                SET status = 'approved', approved_by = ?
                WHERE id = ?
            """, (approved_by, temp_promotion_id))

            self.conn.commit()

            logger.info(f"Approved temp promotion for {promo['promoted_admin_id']} (approved by {approved_by})")

            return True, f"Temporary promotion approved. {promo['promoted_admin_id']} remains Super Admin."

        except Exception as e:
            logger.error(f"Failed to approve temp promotion: {e}")
            return False, str(e)

    def revert_temp_promotion(self, team_id: str, temp_promotion_id: int, reverted_by: str) -> tuple[bool, str]:
        """
        Revert a temporary promotion, demoting admin back to admin (Phase 3.3)

        Args:
            team_id: Team ID
            temp_promotion_id: ID from temp_promotions table
            reverted_by: User ID who reverted (typically the returning super admin)

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            from datetime import datetime
            cursor = self.conn.cursor()

            # Get promotion details
            cursor.execute("""
                SELECT promoted_admin_id, original_super_admin_id, status
                FROM temp_promotions
                WHERE id = ? AND team_id = ?
            """, (temp_promotion_id, team_id))

            promo = cursor.fetchone()
            if not promo:
                return False, "Temporary promotion not found"

            if promo['status'] != 'active':
                return False, f"Promotion already {promo['status']}"

            # Demote back to admin
            success, message = self.update_member_role(team_id, promo['promoted_admin_id'], 'admin')

            if not success:
                return False, f"Failed to demote: {message}"

            # Mark as reverted
            cursor.execute("""
                UPDATE temp_promotions
                SET status = 'reverted', reverted_at = ?, approved_by = ?
                WHERE id = ?
            """, (datetime.now(), reverted_by, temp_promotion_id))

            self.conn.commit()

            logger.info(f"Reverted temp promotion for {promo['promoted_admin_id']} (reverted by {reverted_by})")

            return True, f"Temporary promotion reverted. {promo['promoted_admin_id']} demoted back to Admin."

        except Exception as e:
            logger.error(f"Failed to revert temp promotion: {e}")
            return False, str(e)

    def update_job_role(self, team_id: str, user_id: str, job_role: str) -> tuple[bool, str]:
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
        valid_job_roles = ['doctor', 'pastor', 'nurse', 'admin_staff', 'volunteer', 'unassigned']

        # Allow custom job roles (anything not in the predefined list that's not 'unassigned')
        if job_role not in valid_job_roles and job_role != 'unassigned':
            # Treat as custom role, validate it's reasonable
            if len(job_role) > 50:
                return False, "Custom job role must be 50 characters or less"
            if not job_role.strip():
                return False, "Job role cannot be empty"

        try:
            cursor = self.conn.cursor()

            # Verify user exists in team
            cursor.execute("""
                SELECT role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            if not cursor.fetchone():
                return False, f"User {user_id} not found in team"

            # Update job role
            cursor.execute("""
                UPDATE team_members
                SET job_role = ?
                WHERE team_id = ? AND user_id = ?
            """, (job_role, team_id, user_id))

            self.conn.commit()

            logger.info(f"Updated job role for {user_id} in team {team_id} to {job_role}")

            return True, f"Job role updated to {job_role}"

        except Exception as e:
            logger.error(f"Failed to update job role: {e}")
            return False, str(e)

    def get_member_job_role(self, team_id: str, user_id: str) -> Optional[str]:
        """
        Get a team member's job role (Phase 5.1)

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            Job role string or None if not found
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT job_role FROM team_members
                WHERE team_id = ? AND user_id = ?
            """, (team_id, user_id))

            row = cursor.fetchone()
            if row:
                return row['job_role']

            return None

        except Exception as e:
            logger.error(f"Failed to get job role: {e}")
            return None

    def add_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
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

    def remove_workflow_permission(self, workflow_id: str, team_id: str, permission_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
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

    def check_workflow_permission(self, workflow_id: str, team_id: str, user_id: str, permission_type: str) -> tuple[bool, str]:
        """
        Check if a user has a specific workflow permission (Phase 5.2)

        Checks in order:
        1. God Rights always have all permissions
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

            # God Rights always have all permissions
            if user_role == 'god_rights':
                return True, "God Rights override"

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

    def get_workflow_permissions(self, workflow_id: str, team_id: str) -> List[Dict]:
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

    def create_queue(self, team_id: str, queue_name: str, queue_type: str, description: str, created_by: str) -> tuple[bool, str, str]:
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

    def add_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str, created_by: str) -> tuple[bool, str]:
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

    def remove_queue_permission(self, queue_id: str, team_id: str, access_type: str, grant_type: str, grant_value: str) -> tuple[bool, str]:
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

    def check_queue_access(self, queue_id: str, team_id: str, user_id: str, access_type: str) -> tuple[bool, str]:
        """
        Check if a user has access to a queue (Phase 5.3)

        Checks in order:
        1. God Rights always have all access
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

            # God Rights always have all access
            if user_role == 'god_rights':
                return True, "God Rights override"

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

    def get_accessible_queues(self, team_id: str, user_id: str, access_type: str = 'view') -> List[Dict]:
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

    def get_queue_permissions(self, queue_id: str, team_id: str) -> List[Dict]:
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

    def get_queue(self, queue_id: str, team_id: str) -> Optional[Dict]:
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

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Global team manager instance
_team_manager = TeamManager()


def get_team_manager() -> TeamManager:
    """Get the global team manager instance"""
    return _team_manager


# API Routes

@router.post("/create", response_model=TeamResponse)
async def create_team(request: CreateTeamRequest):
    """
    Create a new team

    The creator is automatically added as Super Admin
    """
    try:
        team_manager = get_team_manager()
        team = team_manager.create_team(
            name=request.name,
            creator_user_id=request.creator_user_id,
            description=request.description
        )
        return TeamResponse(**team)

    except Exception as e:
        logger.error(f"Failed to create team: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}")
async def get_team(team_id: str):
    """Get team details"""
    team_manager = get_team_manager()
    team = team_manager.get_team(team_id)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team


@router.get("/{team_id}/members")
async def get_team_members(team_id: str):
    """Get all members of a team"""
    team_manager = get_team_manager()

    # Verify team exists
    team = team_manager.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = team_manager.get_team_members(team_id)
    return {"team_id": team_id, "members": members}


@router.get("/user/{user_id}/teams")
async def get_user_teams(user_id: str):
    """Get all teams a user is a member of"""
    team_manager = get_team_manager()
    teams = team_manager.get_user_teams(user_id)
    return {"user_id": user_id, "teams": teams}


@router.get("/{team_id}/invite-code", response_model=InviteCodeResponse)
async def get_invite_code(team_id: str):
    """Get active invite code for team"""
    team_manager = get_team_manager()

    # Verify team exists
    team = team_manager.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    code = team_manager.get_active_invite_code(team_id)

    if not code:
        raise HTTPException(status_code=404, detail="No active invite code found")

    return InviteCodeResponse(code=code, team_id=team_id, expires_at=None)


@router.post("/{team_id}/invite-code/regenerate", response_model=InviteCodeResponse)
async def regenerate_invite_code(team_id: str):
    """Generate a new invite code (invalidates old ones)"""
    team_manager = get_team_manager()

    # Verify team exists
    team = team_manager.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    try:
        code = team_manager.regenerate_invite_code(team_id)
        return InviteCodeResponse(code=code, team_id=team_id, expires_at=None)

    except Exception as e:
        logger.error(f"Failed to regenerate invite code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class JoinTeamRequest(BaseModel):
    invite_code: str
    user_id: str


class JoinTeamResponse(BaseModel):
    success: bool
    team_id: str
    team_name: str
    user_role: str


@router.post("/join", response_model=JoinTeamResponse)
async def join_team(request: JoinTeamRequest):
    """
    Join a team using an invite code

    Validates invite code and adds user as member
    """
    team_manager = get_team_manager()

    try:
        # Validate invite code
        team_id = team_manager.validate_invite_code(request.invite_code)

        if not team_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid, expired, or already used invite code"
            )

        # Get team details
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Join team as member
        success = team_manager.join_team(team_id, request.user_id, role='member')

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to join team. You may already be a member."
            )

        return JoinTeamResponse(
            success=True,
            team_id=team_id,
            team_name=team['name'],
            user_role='member'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to join team: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateRoleRequest(BaseModel):
    new_role: str
    requesting_user_role: Optional[str] = None  # For God Rights override


class UpdateRoleResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    team_id: str
    new_role: str


@router.post("/{team_id}/members/{user_id}/role", response_model=UpdateRoleResponse)
async def update_member_role(team_id: str, user_id: str, request: UpdateRoleRequest):
    """
    Update a team member's role

    Enforces Super Admin limits (team size determines max Super Admins).
    God Rights can override limits.

    Valid roles: god_rights, super_admin, admin, member, guest
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Validate role
        valid_roles = ['god_rights', 'super_admin', 'admin', 'member', 'guest']
        if request.new_role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

        # Update role with validation
        success, message = team_manager.update_member_role(
            team_id=team_id,
            user_id=user_id,
            new_role=request.new_role,
            requesting_user_role=request.requesting_user_role
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UpdateRoleResponse(
            success=True,
            message=message,
            user_id=user_id,
            team_id=team_id,
            new_role=request.new_role
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AutoPromoteResponse(BaseModel):
    promoted_users: List[Dict]
    total_promoted: int


@router.post("/{team_id}/members/auto-promote", response_model=AutoPromoteResponse)
async def auto_promote_guests(team_id: str, required_days: int = 7):
    """
    Auto-promote guests who have been members for X days (default: 7)

    Checks all guests in the team and promotes those who have been
    guests for the required number of days to member status.

    This endpoint can be called manually or by a background job/cron.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Auto-promote eligible guests
        results = team_manager.auto_promote_guests(team_id, required_days)

        promoted_count = sum(1 for r in results if r['promoted'])

        return AutoPromoteResponse(
            promoted_users=results,
            total_promoted=promoted_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-promote guests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class InstantPromoteRequest(BaseModel):
    approved_by_user_id: str
    auth_type: str = 'real_password'  # 'real_password' or 'decoy_password'


class InstantPromoteResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    new_role: str


@router.post("/{team_id}/members/{user_id}/instant-promote", response_model=InstantPromoteResponse)
async def instant_promote_guest(team_id: str, user_id: str, request: InstantPromoteRequest):
    """
    Instantly promote a guest to member (Phase 4.2)

    Bypasses 7-day auto-promotion wait when Super Admin approves
    with real password + biometric authentication.

    Access granted immediately:
    - Vault: From now forward
    - Chat: From now forward
    - Automation: From now forward

    This endpoint simulates the real password + Touch ID flow.
    Full biometric integration can be added later.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Instant promote
        success, message = team_manager.instant_promote_guest(
            team_id=team_id,
            user_id=user_id,
            approved_by_user_id=request.approved_by_user_id,
            auth_type=request.auth_type
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return InstantPromoteResponse(
            success=True,
            message=message,
            user_id=user_id,
            new_role='member'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed instant promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/{team_id}/members/{user_id}/delayed-promote", response_model=DelayedPromoteResponse)
async def schedule_delayed_promotion(team_id: str, user_id: str, request: DelayedPromoteRequest):
    """
    Schedule delayed promotion with 21-day wait (Phase 4.3)

    Used when Super Admin approves with decoy password + biometric
    as safety mechanism if "feels iffy" about the guest.

    Access:
    - Chat: From now forward
    - Automation: From now forward
    - Vault: Delayed for X days (default 21)

    This endpoint simulates the decoy password + Touch ID flow.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Schedule delayed promotion
        success, message = team_manager.schedule_delayed_promotion(
            team_id=team_id,
            user_id=user_id,
            delay_days=request.delay_days,
            approved_by_user_id=request.approved_by_user_id,
            reason=request.reason
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        from datetime import datetime, timedelta
        execute_date = datetime.now() + timedelta(days=request.delay_days)

        return DelayedPromoteResponse(
            success=True,
            message=message,
            user_id=user_id,
            execute_date=execute_date.strftime('%Y-%m-%d'),
            delay_days=request.delay_days
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule delayed promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExecuteDelayedResponse(BaseModel):
    executed_promotions: List[Dict]
    total_executed: int


@router.post("/delayed-promotions/execute", response_model=ExecuteDelayedResponse)
async def execute_delayed_promotions(team_id: Optional[str] = None):
    """
    Execute all pending delayed promotions that are due

    Can be called manually or by a cron job/background task.
    Checks delayed_promotions table for promotions where execute_at <= now.

    Optional query param: team_id to limit to specific team
    """
    team_manager = get_team_manager()

    try:
        # Execute pending promotions
        results = team_manager.execute_delayed_promotions(team_id)

        executed_count = sum(1 for r in results if r['executed'])

        return ExecuteDelayedResponse(
            executed_promotions=results,
            total_executed=executed_count
        )

    except Exception as e:
        logger.error(f"Failed to execute delayed promotions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Phase 3.3: Offline Super Admin Failsafe ============


class HeartbeatRequest(BaseModel):
    user_id: str


class HeartbeatResponse(BaseModel):
    success: bool
    message: str


@router.post("/{team_id}/members/heartbeat", response_model=HeartbeatResponse)
async def update_member_heartbeat(team_id: str, request: HeartbeatRequest):
    """
    Update last_seen timestamp for a team member (Phase 3.3)

    Should be called periodically (every 30-60 seconds) by the frontend
    to track member online status and detect offline Super Admins.
    """
    team_manager = get_team_manager()

    try:
        success, message = team_manager.update_last_seen(team_id, request.user_id)

        if not success:
            raise HTTPException(status_code=404, detail=message)

        return HeartbeatResponse(success=True, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OfflineSuperAdminsResponse(BaseModel):
    offline_admins: List[Dict]
    count: int
    threshold_minutes: int


@router.get("/{team_id}/super-admins/status", response_model=OfflineSuperAdminsResponse)
async def check_super_admin_status(team_id: str, offline_threshold_minutes: int = 5):
    """
    Check for offline Super Admins (Phase 3.3)

    Returns list of super admins who haven't been seen in X minutes.
    Default threshold: 5 minutes

    This endpoint can be polled by the frontend to detect when failsafe
    should be triggered.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        offline_admins = team_manager.check_super_admin_offline(team_id, offline_threshold_minutes)

        return OfflineSuperAdminsResponse(
            offline_admins=offline_admins,
            count=len(offline_admins),
            threshold_minutes=offline_threshold_minutes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check super admin status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PromoteTempAdminRequest(BaseModel):
    offline_super_admin_id: str
    requesting_user_role: Optional[str] = None


class PromoteTempAdminResponse(BaseModel):
    success: bool
    message: str
    promoted_admin_id: Optional[str] = None


@router.post("/{team_id}/promote-temp-admin", response_model=PromoteTempAdminResponse)
async def promote_temp_admin(team_id: str, request: PromoteTempAdminRequest):
    """
    Manually trigger temporary admin promotion (Phase 3.3)

    Promotes the most senior admin to super_admin when the original
    super_admin is offline.

    Typically called automatically when offline detection threshold is exceeded.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.promote_admin_temporarily(
            team_id=team_id,
            offline_super_admin_id=request.offline_super_admin_id,
            requesting_user_role=request.requesting_user_role
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Extract promoted admin ID from message
        import re
        match = re.search(r'promoted (\S+)', message)
        promoted_admin_id = match.group(1) if match else None

        return PromoteTempAdminResponse(
            success=True,
            message=message,
            promoted_admin_id=promoted_admin_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to promote temp admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TempPromotionsResponse(BaseModel):
    temp_promotions: List[Dict]
    count: int


@router.get("/{team_id}/temp-promotions", response_model=TempPromotionsResponse)
async def get_temp_promotions(team_id: str):
    """
    Get pending temporary promotions for a team (Phase 3.3)

    Returns active temp promotions awaiting approval from the
    returning super admin.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        promotions = team_manager.get_pending_temp_promotions(team_id)

        return TempPromotionsResponse(
            temp_promotions=promotions,
            count=len(promotions)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get temp promotions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ApproveTempPromotionRequest(BaseModel):
    approved_by: str


class ApproveTempPromotionResponse(BaseModel):
    success: bool
    message: str


@router.post("/{team_id}/temp-promotions/{temp_promotion_id}/approve", response_model=ApproveTempPromotionResponse)
async def approve_temp_promotion(team_id: str, temp_promotion_id: int, request: ApproveTempPromotionRequest):
    """
    Approve a temporary promotion, making it permanent (Phase 3.3)

    Called by the returning super admin to keep the temp promotion.
    The promoted admin remains as super_admin.
    """
    team_manager = get_team_manager()

    try:
        success, message = team_manager.approve_temp_promotion(
            team_id=team_id,
            temp_promotion_id=temp_promotion_id,
            approved_by=request.approved_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return ApproveTempPromotionResponse(success=True, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve temp promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RevertTempPromotionRequest(BaseModel):
    reverted_by: str


class RevertTempPromotionResponse(BaseModel):
    success: bool
    message: str


@router.post("/{team_id}/temp-promotions/{temp_promotion_id}/revert", response_model=RevertTempPromotionResponse)
async def revert_temp_promotion(team_id: str, temp_promotion_id: int, request: RevertTempPromotionRequest):
    """
    Revert a temporary promotion, demoting admin back to admin (Phase 3.3)

    Called by the returning super admin to undo the temp promotion.
    The promoted admin is demoted back to their original admin role.
    """
    team_manager = get_team_manager()

    try:
        success, message = team_manager.revert_temp_promotion(
            team_id=team_id,
            temp_promotion_id=temp_promotion_id,
            reverted_by=request.reverted_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return RevertTempPromotionResponse(success=True, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revert temp promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Phase 5.1: Job Roles ============


class UpdateJobRoleRequest(BaseModel):
    job_role: str


class UpdateJobRoleResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    job_role: str


@router.post("/{team_id}/members/{user_id}/job-role", response_model=UpdateJobRoleResponse)
async def update_member_job_role(team_id: str, user_id: str, request: UpdateJobRoleRequest):
    """
    Update a team member's job role (Phase 5.1)

    Job roles are used for workflow permissions and queue access control.

    Predefined job roles:
    - doctor: Medical professionals
    - pastor: Pastoral care staff
    - nurse: Nursing staff
    - admin_staff: Administrative staff
    - volunteer: Volunteers
    - unassigned: No job role assigned

    Custom job roles are also supported (any string up to 50 characters).
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.update_job_role(
            team_id=team_id,
            user_id=user_id,
            job_role=request.job_role
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UpdateJobRoleResponse(
            success=True,
            message=message,
            user_id=user_id,
            job_role=request.job_role
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class JobRoleResponse(BaseModel):
    user_id: str
    job_role: Optional[str]


@router.get("/{team_id}/members/{user_id}/job-role", response_model=JobRoleResponse)
async def get_member_job_role(team_id: str, user_id: str):
    """
    Get a team member's job role (Phase 5.1)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        job_role = team_manager.get_member_job_role(team_id, user_id)

        if job_role is None:
            raise HTTPException(status_code=404, detail="User not found in team")

        return JobRoleResponse(user_id=user_id, job_role=job_role)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WORKFLOW PERMISSIONS API (Phase 5.2)
# ============================================================================

class AddWorkflowPermissionRequest(BaseModel):
    permission_type: str  # view, edit, delete, assign
    grant_type: str  # role, job_role, user
    grant_value: str
    created_by: str


class AddWorkflowPermissionResponse(BaseModel):
    success: bool
    message: str
    workflow_id: str
    permission_type: str
    grant_type: str
    grant_value: str


@router.post("/{team_id}/workflows/{workflow_id}/permissions", response_model=AddWorkflowPermissionResponse)
async def add_workflow_permission(team_id: str, workflow_id: str, request: AddWorkflowPermissionRequest):
    """
    Add a workflow permission grant (Phase 5.2)

    Grants permission to a specific role, job_role, or user for a workflow.

    Permission types:
    - view: Can view the workflow
    - edit: Can modify the workflow
    - delete: Can delete the workflow
    - assign: Can assign work items from the workflow

    Grant types:
    - role: Grant to all users with a specific role (guest, member, admin, super_admin)
    - job_role: Grant to all users with a specific job role (doctor, pastor, nurse, etc.)
    - user: Grant to a specific user by user_id
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.add_workflow_permission(
            workflow_id=workflow_id,
            team_id=team_id,
            permission_type=request.permission_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value,
            created_by=request.created_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return AddWorkflowPermissionResponse(
            success=True,
            message=message,
            workflow_id=workflow_id,
            permission_type=request.permission_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add workflow permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RemoveWorkflowPermissionRequest(BaseModel):
    permission_type: str
    grant_type: str
    grant_value: str


class RemoveWorkflowPermissionResponse(BaseModel):
    success: bool
    message: str


@router.delete("/{team_id}/workflows/{workflow_id}/permissions", response_model=RemoveWorkflowPermissionResponse)
async def remove_workflow_permission(team_id: str, workflow_id: str, request: RemoveWorkflowPermissionRequest):
    """
    Remove a workflow permission grant (Phase 5.2)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.remove_workflow_permission(
            workflow_id=workflow_id,
            team_id=team_id,
            permission_type=request.permission_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return RemoveWorkflowPermissionResponse(success=True, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove workflow permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/{team_id}/workflows/{workflow_id}/permissions", response_model=GetWorkflowPermissionsResponse)
async def get_workflow_permissions(team_id: str, workflow_id: str):
    """
    Get all permission grants for a workflow (Phase 5.2)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        permissions = team_manager.get_workflow_permissions(workflow_id, team_id)

        return GetWorkflowPermissionsResponse(
            workflow_id=workflow_id,
            team_id=team_id,
            permissions=permissions,
            count=len(permissions)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CheckWorkflowPermissionRequest(BaseModel):
    user_id: str
    permission_type: str


class CheckWorkflowPermissionResponse(BaseModel):
    has_permission: bool
    message: str
    workflow_id: str
    user_id: str
    permission_type: str


@router.post("/{team_id}/workflows/{workflow_id}/check-permission", response_model=CheckWorkflowPermissionResponse)
async def check_workflow_permission(team_id: str, workflow_id: str, request: CheckWorkflowPermissionRequest):
    """
    Check if a user has a specific permission for a workflow (Phase 5.2)

    Checks in priority order:
    1. God Rights - always have all permissions
    2. User-specific grants
    3. Job role grants
    4. Role grants
    5. Default permissions (based on role)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        has_permission, message = team_manager.check_workflow_permission(
            workflow_id=workflow_id,
            team_id=team_id,
            user_id=request.user_id,
            permission_type=request.permission_type
        )

        return CheckWorkflowPermissionResponse(
            has_permission=has_permission,
            message=message,
            workflow_id=workflow_id,
            user_id=request.user_id,
            permission_type=request.permission_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check workflow permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QUEUE ACCESS CONTROL API (Phase 5.3)
# ============================================================================

class CreateQueueRequest(BaseModel):
    queue_name: str
    queue_type: str  # patient, medication, pharmacy, counseling, etc.
    description: str
    created_by: str


class CreateQueueResponse(BaseModel):
    success: bool
    message: str
    queue_id: str


@router.post("/{team_id}/queues", response_model=CreateQueueResponse)
async def create_queue(team_id: str, request: CreateQueueRequest):
    """
    Create a new queue (Phase 5.3)

    Queue types can be customized based on organization needs:
    - patient: Patient queue for medical facilities
    - medication: Medication/pharmacy queue
    - counseling: Counseling/pastoral care queue
    - emergency: Emergency/priority queue
    - custom: Any other custom queue type
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message, queue_id = team_manager.create_queue(
            team_id=team_id,
            queue_name=request.queue_name,
            queue_type=request.queue_type,
            description=request.description,
            created_by=request.created_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return CreateQueueResponse(
            success=True,
            message=message,
            queue_id=queue_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddQueuePermissionRequest(BaseModel):
    access_type: str  # view, manage, assign
    grant_type: str  # role, job_role, user
    grant_value: str
    created_by: str


class AddQueuePermissionResponse(BaseModel):
    success: bool
    message: str
    queue_id: str
    access_type: str
    grant_type: str
    grant_value: str


@router.post("/{team_id}/queues/{queue_id}/permissions", response_model=AddQueuePermissionResponse)
async def add_queue_permission(team_id: str, queue_id: str, request: AddQueuePermissionRequest):
    """
    Add queue access permission (Phase 5.3)

    Access types:
    - view: Can see the queue and its items
    - manage: Can modify queue settings and items
    - assign: Can assign items to users

    Grant types:
    - role: Grant to all users with a specific role (guest, member, admin, super_admin)
    - job_role: Grant to all users with a specific job role (doctor, pastor, nurse, etc.)
    - user: Grant to a specific user by user_id

    Example use cases:
    - Doctors can view patient queue: grant_type=job_role, grant_value=doctor, access_type=view
    - Pharmacy can view medication queue: grant_type=job_role, grant_value=pharmacy, access_type=view
    - Pastors can view counseling queue: grant_type=job_role, grant_value=pastor, access_type=view
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.add_queue_permission(
            queue_id=queue_id,
            team_id=team_id,
            access_type=request.access_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value,
            created_by=request.created_by
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return AddQueuePermissionResponse(
            success=True,
            message=message,
            queue_id=queue_id,
            access_type=request.access_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add queue permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RemoveQueuePermissionRequest(BaseModel):
    access_type: str
    grant_type: str
    grant_value: str


class RemoveQueuePermissionResponse(BaseModel):
    success: bool
    message: str


@router.delete("/{team_id}/queues/{queue_id}/permissions", response_model=RemoveQueuePermissionResponse)
async def remove_queue_permission(team_id: str, queue_id: str, request: RemoveQueuePermissionRequest):
    """
    Remove queue access permission (Phase 5.3)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        success, message = team_manager.remove_queue_permission(
            queue_id=queue_id,
            team_id=team_id,
            access_type=request.access_type,
            grant_type=request.grant_type,
            grant_value=request.grant_value
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return RemoveQueuePermissionResponse(success=True, message=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove queue permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/{team_id}/queues/{queue_id}/permissions", response_model=GetQueuePermissionsResponse)
async def get_queue_permissions(team_id: str, queue_id: str):
    """
    Get all permission grants for a queue (Phase 5.3)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        permissions = team_manager.get_queue_permissions(queue_id, team_id)

        return GetQueuePermissionsResponse(
            queue_id=queue_id,
            team_id=team_id,
            permissions=permissions,
            count=len(permissions)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get queue permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CheckQueueAccessRequest(BaseModel):
    user_id: str
    access_type: str


class CheckQueueAccessResponse(BaseModel):
    has_access: bool
    message: str
    queue_id: str
    user_id: str
    access_type: str


@router.post("/{team_id}/queues/{queue_id}/check-access", response_model=CheckQueueAccessResponse)
async def check_queue_access(team_id: str, queue_id: str, request: CheckQueueAccessRequest):
    """
    Check if a user has access to a queue (Phase 5.3)

    Checks in priority order:
    1. God Rights - always have all access
    2. User-specific grants
    3. Job role grants
    4. Role grants
    5. Default permissions (members+ can view, admins+ can manage/assign)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        has_access, message = team_manager.check_queue_access(
            queue_id=queue_id,
            team_id=team_id,
            user_id=request.user_id,
            access_type=request.access_type
        )

        return CheckQueueAccessResponse(
            has_access=has_access,
            message=message,
            queue_id=queue_id,
            user_id=request.user_id,
            access_type=request.access_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check queue access: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/{team_id}/queues/accessible/{user_id}", response_model=GetAccessibleQueuesResponse)
async def get_accessible_queues(team_id: str, user_id: str, access_type: str = 'view'):
    """
    Get all queues a user can access (Phase 5.3)

    Returns queues filtered by user's permissions based on:
    - Their role (guest, member, admin, super_admin, god_rights)
    - Their job role (doctor, pastor, nurse, pharmacy, etc.)
    - Explicit user grants

    This endpoint implements the core queue filtering:
    - Doctors see patient queue (if granted)
    - Pastors see counseling queue (if granted)
    - Pharmacy sees medication queue (if granted)
    - Etc.
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        queues = team_manager.get_accessible_queues(team_id, user_id, access_type)

        return GetAccessibleQueuesResponse(
            team_id=team_id,
            user_id=user_id,
            access_type=access_type,
            queues=queues,
            count=len(queues)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get accessible queues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class QueueDetails(BaseModel):
    queue_id: str
    queue_name: str
    queue_type: str
    description: str
    created_at: str
    created_by: str
    is_active: bool


@router.get("/{team_id}/queues/{queue_id}", response_model=QueueDetails)
async def get_queue(team_id: str, queue_id: str):
    """
    Get queue details (Phase 5.3)
    """
    team_manager = get_team_manager()

    try:
        # Verify team exists
        team = team_manager.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        queue = team_manager.get_queue(queue_id, team_id)

        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        return QueueDetails(**queue)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))
