"""
Team Service Type Definitions

Shared types, constants, and enums used across the team service modules.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Team roles (in order of privilege)
TEAM_ROLES = ["guest", "member", "admin", "super_admin"]

# Permission types for workflows
WORKFLOW_PERMISSION_TYPES = ["view", "edit", "execute", "manage"]

# Permission types for queues
QUEUE_ACCESS_TYPES = ["view", "add", "remove", "manage"]

# Vault permission types
VAULT_PERMISSION_TYPES = ["view", "edit", "delete", "manage"]

# Grant types (how permissions are assigned)
GRANT_TYPES = ["user", "role", "job_role"]

# Queue types
QUEUE_TYPES = ["workflow", "task", "approval", "custom"]

# Vault item types
VAULT_ITEM_TYPES = ["file", "text", "credential", "note"]

# Status constants
TEMP_PROMOTION_STATUS = ["active", "approved", "reverted"]

# Auto-promotion constants
AUTO_PROMOTION_DAYS = 7
DELAYED_PROMOTION_DAYS = 21
SUPER_ADMIN_OFFLINE_THRESHOLD_MINUTES = 5

# Brute force protection constants
MAX_INVITE_ATTEMPTS = 5
INVITE_LOCKOUT_WINDOW_MINUTES = 15

# Type aliases for common return types
SuccessResult = Tuple[bool, str]
SuccessResultWithId = Tuple[bool, str, str]
