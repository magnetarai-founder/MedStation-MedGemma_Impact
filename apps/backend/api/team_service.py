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
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
