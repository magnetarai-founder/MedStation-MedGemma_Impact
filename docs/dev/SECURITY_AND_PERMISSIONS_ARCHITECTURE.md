# Security and Permissions Architecture
## User Isolation, RBAC, and Multi-User System

**Status:** 🔴 IN PROGRESS - CRITICAL SECURITY IMPLEMENTATION
**Priority:** P0 - Foundation for production multi-user system
**Complexity:** VERY HIGH - Requires meticulous planning and implementation

---

## Table of Contents

### Part 1: User Isolation (Phase 1 - In Progress)
1. [Problem Statement](#problem-statement)
2. [User Roles & Permissions (Basic)](#user-roles--permissions-basic)
3. [Database Schema Changes (Phase 1)](#database-schema-changes-phase-1)
4. [Backend Implementation (Phase 1)](#backend-implementation-phase-1)
5. [Testing Checklist (Phase 1)](#testing-checklist-phase-1)
6. [Migration Plan (Phase 1)](#migration-plan-phase-1)

### Part 2: RBAC & Permissions System (Phase 2 - Roadmap)
7. [Salesforce-Inspired Architecture](#salesforce-inspired-architecture)
8. [Complete Role & Permission Model](#complete-role--permission-model)
9. [Permission Engine](#permission-engine)
10. [Database Schema (Phase 2)](#database-schema-phase-2)
11. [Backend Implementation (Phase 2)](#backend-implementation-phase-2)
12. [Frontend Implementation](#frontend-implementation)
13. [Testing Strategy (Phase 2)](#testing-strategy-phase-2)
14. [Timeline & Risks](#timeline--risks)

### Quick Reference
15. [God Rights Credentials](#god-rights-credentials)
16. [Service Implementation Status](#service-implementation-status)

### Part 12: Codebase Alignment & Quick Fixes
17. [Codebase Alignment Notes](#part-12-codebase-alignment--quick-fixes)
18. [Phase 0.5 Checklist](#-phase-05-checklist-complete-before-phase-1a)

---

# Part 1: User Isolation (Phase 1 - In Progress)

## Problem Statement

ElohimOS currently lacks proper user isolation. All data (chats, vaults, workflows, settings) is shared globally across all users on a device. This is a **critical security vulnerability** that must be fixed.

### Current Issues:
- ❌ User A can see User B's chat history
- ❌ User A can access User B's vault documents
- ❌ User A can see User B's workflows and automations
- ❌ User A can modify User B's settings
- ❌ No user switching/logout functionality
- ❌ No audit logging of who accessed what

---

## User Roles & Permissions (Basic)

### 1. **God Rights (Founder)**
- Hardcoded backdoor account for field support
- Username: `elohim_founder` (configurable via `ELOHIM_GOD_USERNAME`)
- Password: Set via `ELOHIM_GOD_PASSWORD` env var
- **Can see EVERYTHING on the device**
- **Can manage all users** (unlock, reset passwords, change roles)
- **Cannot be locked out** (bypasses all normal auth)
- Use cases:
  - Field support when users get locked out
  - Team setup and troubleshooting
  - Device-level administration
  - Emergency access

### 2. **Super Admin** (Device/Team Leader)
**Solo Mode (no team connected):**
- First user on device = `super_admin` automatically
- Additional users = `member` by default
- Super admin can:
  - Manage other users on the device (limited compared to God Rights)
  - Assign roles to other users
  - See team-level analytics (not individual user data)
  - Configure device-wide settings (memory allocation, models)

**Team Mode (connected to network):**
- Team creator = `super_admin`
- New members joining team = role assigned by super_admin
- Super admin can:
  - Manage team members
  - Assign roles (admin, member, viewer)
  - Configure team vault access
  - View team activity logs

### 3. **Admin** (Team Moderator)
- Can help users with common issues
- Can view team analytics
- **Cannot** change roles or access individual user data
- **Cannot** unlock accounts (must escalate to super_admin or God Rights)

### 4. **Member** (Standard User)
- Default role for new users
- Can only access their own data
- Can create/edit their own chats, vault, workflows
- Can join teams if invited

### 5. **Viewer** (Read-Only)
- Can view shared team resources
- Cannot create or edit anything
- Useful for training scenarios or restricted devices

---

## Database Schema Changes (Phase 1)

### All User-Specific Tables Need `user_id` Column

#### Chat & Conversations
```sql
-- chat_memory.db
ALTER TABLE chat_sessions ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';
ALTER TABLE messages ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';
ALTER TABLE conversation_summaries ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';

CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_summaries_user ON conversation_summaries(user_id);
```

#### Vault Documents
```sql
-- vault.db (already has user_id, but verify filtering)
-- Ensure all queries filter: WHERE user_id = ? OR role = 'god_rights'
```

#### Workflows & Automations
```sql
-- workflows.db
ALTER TABLE workflows ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';
ALTER TABLE workflow_executions ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';

CREATE INDEX idx_workflows_user ON workflows(user_id);
CREATE INDEX idx_executions_user ON workflow_executions(user_id);
```

#### Settings & Preferences
```sql
-- settings.db
ALTER TABLE user_settings ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';

-- Model configs should be per-user
ALTER TABLE model_configs ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';

CREATE INDEX idx_settings_user ON user_settings(user_id);
CREATE INDEX idx_model_configs_user ON model_configs(user_id);
```

#### Query History
```sql
-- sessions.db
ALTER TABLE query_history ADD COLUMN user_id TEXT NOT NULL DEFAULT 'migration_needed';

CREATE INDEX idx_query_history_user ON query_history(user_id);
```

---

## Backend Implementation (Phase 1)

### Phase 1: Database Migration (CRITICAL)
- [x] Create migration script: `migrate_add_user_id_columns.py`
- [x] Add `user_id` to all user-specific tables
- [x] Set default `user_id` for existing data (assign to first user)
- [x] Create indexes for performance
- [ ] Test rollback procedure

### Phase 2: Service-Level User Filtering

#### Core Services to Update:

**chat_service.py** ✅ COMPLETED
- [x] Add `user: Dict = Depends(get_current_user)` to all endpoints
- [x] Filter all chat queries: `WHERE user_id = ? OR role = 'god_rights'`
- [x] Ensure chat creation sets `user_id` from JWT token
- [x] Test: User A cannot see User B's chats

**vault_service.py** - TODO
- [ ] Add user filtering to all vault queries
- [ ] God Rights can see all vaults (support mode)
- [ ] Team mode: Check team permissions + user_id
- [ ] Test: User A cannot access User B's vault documents

**workflow_service.py** - TODO
- [ ] Filter workflows by user_id
- [ ] Filter executions by user_id
- [ ] Allow super_admin to see team workflows (if team mode)
- [ ] Test: User A cannot see/edit User B's workflows

**user_service.py** - TODO
- [ ] Current user can only edit their own profile
- [ ] God Rights can edit any profile
- [ ] Super admin can assign roles to other users
- [ ] Test: User A cannot change User B's profile

**team_service.py** - TODO
- [ ] Filter team data by current user's team
- [ ] Super admin can manage team members
- [ ] God Rights can see all teams on device
- [ ] Test: User A cannot access unrelated teams

**insights_service.py** - TODO
- [ ] Filter insights by user_id
- [ ] Team insights: aggregate team data (not individual user data)
- [ ] God Rights: device-wide insights
- [ ] Test: User A cannot see User B's personal insights

**docs_service.py** (if stores user docs) - TODO
- [ ] Filter documents by user_id
- [ ] Shared team docs: check team permissions
- [ ] Test: User A cannot access User B's documents

**backup_service.py** - TODO
- [ ] Backups include user_id metadata
- [ ] Restore only restores current user's data (unless God Rights)
- [ ] Test: Restore doesn't leak other users' data

**trash_service.py** - TODO
- [ ] Filter trash by user_id
- [ ] Test: User A cannot see User B's trash

**code_editor_service.py** (if stores saved code) - TODO
- [ ] Filter saved code by user_id
- [ ] Test: User A cannot access User B's code snippets

**undo_service.py** - TODO
- [ ] Filter undo history by user_id
- [ ] Test: User A cannot undo User B's actions

**p2p_chat_service.py** - TODO
- [ ] Already handles team permissions (verify)
- [ ] Test: User A cannot access unrelated P2P chats

**encrypted_db_service.py** - TODO
- [ ] Ensure encryption keys are user-specific
- [ ] God Rights cannot decrypt user vaults (unless master key implemented)
- [ ] Test: User A's encryption key doesn't work on User B's data

### Phase 3: Role Assignment Logic

**user_service.py - Role Assignment**
```python
def assign_role_on_registration(user_id: str) -> str:
    """
    Assign role to newly registered user

    Rules:
    - Solo Mode (no team): First user = super_admin, others = member
    - Team Mode: Assigned by team super_admin when joining
    - God Rights can override any role
    """
    # Check if this is first user on device
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 1:
        # First user = super_admin
        return "super_admin"

    # Check if connected to team
    team_status = get_team_status()

    if team_status["connected"]:
        # Team mode: role assigned by team leader (default to member)
        return "member"  # Will be updated by team admin
    else:
        # Solo mode: additional users = member
        return "member"
```

**team_service.py - Team Role Assignment**
```python
@router.post("/team/{team_id}/members/{user_id}/role")
async def assign_team_role(
    team_id: str,
    user_id: str,
    role: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Assign role to team member (super_admin or God Rights only)
    """
    # Check permissions
    if current_user["role"] not in ["super_admin", "god_rights"]:
        raise HTTPException(403, "Only super admins can assign roles")

    # Validate role
    valid_roles = ["super_admin", "admin", "member", "viewer"]
    if role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")

    # Assign role
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET role = ?, role_changed_at = ?, role_changed_by = ?
        WHERE user_id = ?
    """, (role, datetime.utcnow().isoformat(), current_user["user_id"], user_id))

    conn.commit()

    # Log action
    audit_log.log_action(
        user_id=current_user["user_id"],
        action="assign_role",
        target_user=user_id,
        details={"role": role}
    )

    return {"success": True, "user_id": user_id, "role": role}
```

### Phase 4: God Rights Support Dashboard

**Location:** Settings > Support (only visible to God Rights)

**Features:**
- [ ] List all users on device
  - Username, role, created_at, last_login
  - Status (active, locked, disabled)
- [ ] User details view
  - Profile info
  - Vault statistics (# documents, encrypted)
  - Chat statistics (# conversations, messages)
  - Workflow count
  - Last activity timestamp
- [ ] User management actions
  - Unlock account
  - Reset password
  - Change role
  - Disable/enable account
  - Delete account (with confirmation)
- [ ] Device overview
  - Total users
  - Active teams
  - Storage usage per user
  - AI model usage per user
- [ ] Audit logs
  - All God Rights actions
  - Role changes
  - Account unlocks
  - Password resets

**UI Location:** `apps/frontend/src/components/settings/SupportDashboard.tsx`

**Backend Endpoints:**
```python
# apps/backend/api/main.py

@app.get("/api/support/users")
async def get_all_users(current_user: Dict = Depends(get_current_user)):
    """Get all users on device (God Rights only)"""
    if current_user["role"] != "god_rights":
        raise HTTPException(403, "God Rights required")

    # Return all users with stats
    pass

@app.post("/api/support/users/{user_id}/unlock")
async def unlock_user(user_id: str, current_user: Dict = Depends(get_current_user)):
    """Unlock user account (God Rights only)"""
    if current_user["role"] != "god_rights":
        raise HTTPException(403, "God Rights required")

    # Unlock account
    # Log action
    pass

@app.post("/api/support/users/{user_id}/reset-password")
async def reset_password(user_id: str, new_password: str, current_user: Dict = Depends(get_current_user)):
    """Reset user password (God Rights only)"""
    if current_user["role"] != "god_rights":
        raise HTTPException(403, "God Rights required")

    # Reset password
    # Log action
    pass
```

### Phase 5: User Switching & Logout

**Frontend:**
- [ ] Add "Switch User" button to user profile menu
- [ ] Add "Logout" button to user profile menu
- [ ] Clear localStorage on logout
- [ ] Redirect to login screen

**Backend:**
```python
@app.post("/api/auth/logout")
async def logout(current_user: Dict = Depends(get_current_user)):
    """Logout current user"""
    # Remove session from database
    auth_service.logout(request.headers["Authorization"].replace("Bearer ", ""))
    return {"success": True}
```

### Phase 6: Audit Logging

**Create:** `apps/backend/api/audit_logger.py`

```python
class AuditLogger:
    """Log all sensitive actions for compliance and security"""

    def log_action(self, user_id: str, action: str, target_user: str = None, details: Dict = None):
        """
        Log user action

        Actions to log:
        - God Rights login
        - God Rights support actions (unlock, reset, role change)
        - Super admin role assignments
        - Vault access (decoy mode, vault switching)
        - Account creation/deletion
        - Password changes
        - Team joins/leaves
        """
        pass
```

**Storage:** `audit_logs.db`

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    target_user_id TEXT,
    target_username TEXT,
    details TEXT,  -- JSON
    ip_address TEXT,
    device_fingerprint TEXT
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

---

## Testing Checklist (Phase 1)

### Unit Tests
- [ ] Test user filtering in all services
- [ ] Test God Rights bypasses filtering
- [ ] Test role assignment logic
- [ ] Test audit logging

### Integration Tests
- [ ] Create User A and User B
- [ ] Verify User A cannot see User B's chats
- [ ] Verify User A cannot access User B's vault
- [ ] Verify User A cannot edit User B's workflows
- [ ] Verify God Rights can see all users
- [ ] Verify super_admin can assign roles
- [ ] Verify member cannot assign roles

### Security Tests
- [ ] SQL injection attempts on user filtering
- [ ] JWT token manipulation (try to access other user's data)
- [ ] Role elevation attempts (member trying to become admin)
- [ ] God Rights password brute force protection
- [ ] Audit log tampering detection

---

## Migration Plan (Phase 1)

### Step 1: Backup Everything
```bash
# Backup all databases before migration
cp -r apps/backend/.neutron_data apps/backend/.neutron_data.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 2: Run Migration Script
```bash
# Apply user_id columns to all tables
python apps/backend/api/migrate_add_user_id_columns.py
```

### Step 3: Assign Existing Data
```python
# Assign all existing data to first user (God Rights or super_admin)
first_user = get_first_user()

for table in ["chat_sessions", "messages", "workflows", "vault_documents"]:
    cursor.execute(f"""
        UPDATE {table}
        SET user_id = ?
        WHERE user_id = 'migration_needed'
    """, (first_user.user_id,))
```

### Step 4: Deploy Backend Changes
- Deploy service updates with user filtering
- Test thoroughly on dev instance

### Step 5: Deploy Frontend Changes
- Deploy user role UI updates
- Deploy Support Dashboard (God Rights only)

### Step 6: Verify
- Test multi-user isolation
- Test God Rights access
- Verify audit logs are working

---

## Timeline Estimate (Phase 1)

**Phase 1 (Database Migration):** 1-2 days
**Phase 2 (Service Filtering):** 3-5 days (18 services to update)
**Phase 3 (Role Assignment):** 1 day
**Phase 4 (Support Dashboard):** 2-3 days
**Phase 5 (User Switching/Logout):** 1 day
**Phase 6 (Audit Logging):** 1-2 days
**Testing & QA:** 2-3 days

**Total Phase 1:** ~2-3 weeks of focused development

---

## Risks & Mitigations (Phase 1)

### Risk 1: Data Loss During Migration
**Mitigation:**
- Full backup before migration
- Test migration on copy of production data
- Rollback script ready

### Risk 2: Performance Impact (user_id filtering on every query)
**Mitigation:**
- Add indexes on all `user_id` columns
- Use connection pooling
- Cache user permissions in memory

### Risk 3: Breaking Existing Deployments
**Mitigation:**
- Gradual rollout (database migration first, then services)
- Feature flag for multi-user mode
- Backward compatibility for single-user setups

### Risk 4: God Rights Password Leak
**Mitigation:**
- Require strong password in production
- Rate limit login attempts
- Alert on failed God Rights login attempts
- Audit log all God Rights actions

---

# Part 2: RBAC & Permissions System (Phase 2 - Roadmap)

## Salesforce-Inspired Architecture

### Design Philosophy (Salesforce-Inspired)

ElohimOS follows the Salesforce model for permissions and access control:

1. **Multi-Tenancy**: Separate team workspaces (like Salesforce orgs)
2. **Customizable Permissions**: Each team defines their own permission structure
3. **Profile + Permission Sets**: Base permissions + granular add-ons
4. **Solo vs Team Mode**: Full freedom solo, sandboxed in teams
5. **Hierarchical Roles**: Clear role hierarchy with inheritance

### Operating Modes

#### **Solo Mode** (No Team)
- User has **zero restrictions**
- Full access to all features
- No sandboxing, no permission checks
- Data is 100% private to them
- First user on device = Super Admin (can add other users to device)

#### **Team Mode** (Connected to Team Workspace)
- User is **sandboxed** based on role + custom permissions
- Access to shared resources controlled by permissions
- Personal data remains private (unless explicitly shared)
- Team admins define permission structure

---

## Complete Role & Permission Model

### System Roles (5 Levels)

#### **1. Founder Admin** (god_rights)
- **Job Role:** "Founder & Staff" (HARDCODED - always displays this)
- **System Permission Level:** Highest - can do EVERYTHING
- **Capabilities:**
  - See ALL data across entire system (all users, all teams)
  - Manage all users on device (unlock, reset, delete)
  - Cannot be locked out (bypasses all auth)
  - Create multiple personal Founder Admin accounts for themselves
  - Assign any role to anyone
  - Define and modify all permission structures
  - Emergency field support access
  - Full audit log access
- **Use Cases:**
  - Field support when users locked out
  - Team setup and troubleshooting
  - Device-level administration
  - Emergency access to any data
- **Login:** `elohim_founder` / `ElohimOS_2024_Founder` (configurable)

#### **2. Super Admin**
- **Job Role:** "Super Administrator" (HARDCODED - always displays this)
- **System Permission Level:** Full admin within team scope
- **Capabilities:**
  - Manage team members (but not other Founders)
  - Assign Admin, Member, Guest roles
  - Create and modify permission templates
  - Define team-level permission structures
  - Elevate guests to full team members
  - View team-wide analytics (aggregate, not individual user data)
  - Configure team workspace settings
  - Set job roles for all team members
- **Restrictions:**
  - Cannot assign Founder Admin or Super Admin roles (only Founders can)
  - Cannot access other teams' data
  - Cannot bypass encryption on user vaults
- **Assignment:**
  - First user on device = Super Admin automatically (Solo Mode)
  - Team creator = Super Admin (Team Mode)
  - Can be assigned by Founder Admin

#### **3. Admin**
- **Job Role:** USER-DEFINED (e.g., "Engineering Lead", "Sales Manager", "HR Admin")
- **System Permission Level:** Limited admin - configurable per team
- **Capabilities (Base - Customizable via Permissions):**
  - Assign Member role only (cannot assign Admin or higher)
  - Create guest accounts
  - Set job roles for members and guests
  - Manage resources they're given permission to manage
  - View analytics they're permitted to see
  - Customize settings within their permission scope
- **Restrictions:**
  - Cannot elevate guests to team members (only Super Admin/Founder)
  - Cannot assign Admin or higher roles
  - Cannot modify team-level permission structures
  - Access controlled by permission sets
- **Permission Examples:**
  - "Engineering Admin" might have: manage code repos, view eng analytics
  - "Sales Admin" might have: manage CRM data, view sales pipeline
  - "HR Admin" might have: manage user profiles, view team roster

#### **4. Member**
- **Job Role:** USER-DEFINED (e.g., "Software Engineer", "Sales Rep", "Designer", "Analyst")
- **System Permission Level:** Standard user - configurable per team
- **Capabilities (Base - Customizable via Permissions):**
  - Full access to own personal workspace (chats, docs, vault)
  - Access to shared team resources based on permission sets
  - Collaborate on documents they're given access to
  - Use all app features (AI, workflows, data engine) in personal space
  - Participate in teams based on assigned permissions
- **Restrictions:**
  - Cannot assign roles or manage users
  - Cannot access other users' private data
  - Team resource access based on permission sets
  - Cannot create guest accounts
- **Permission Examples:**
  - "Engineer" might have: write access to code repos, read-only to prod data
  - "Sales Rep" might have: full CRM access, read-only to analytics
  - "Designer" might have: full creative assets access, comment-only on docs

#### **5. Guest**
- **Job Role:** USER-DEFINED (e.g., "External Consultant", "Contractor", "Auditor")
- **System Permission Level:** Temporary access - highly configurable
- **Capabilities:**
  - **Full personal workspace access** (own chats, AI, personal docs)
  - **Limited team workspace access** (only what explicitly granted)
  - Can use all app features in personal space
  - Can collaborate on specific documents/projects they're invited to
  - Cannot see team roster or team-wide data by default
- **Restrictions:**
  - Very limited shared resource access (permission-based)
  - Cannot create other users or guests
  - Cannot be elevated to Member by Admins (only Super Admin/Founder)
  - May have time-limited access (expiration date)
- **Use Cases:**
  - External consultant working on specific project
  - Contractor with temporary access
  - Auditor reviewing specific data sets
  - Client given limited collaboration access

---

## Job Roles vs System Roles

### **System Role** (Permission Level)
- Controls what user **CAN DO** in the system
- Options: Founder Admin, Super Admin, Admin, Member, Guest
- Determines permission boundaries
- Hierarchical: Founder > Super Admin > Admin > Member > Guest

### **Job Role** (Description/Label)
- Describes what user **DOES** in organization
- Fully customizable text field
- Examples: "Senior Engineer", "Marketing Manager", "External Auditor"
- Used for display, reporting, and context
- No technical permission implications (permissions come from System Role + Permission Sets)

### **Hardcoded Job Roles** (Only 2):
1. **Founder Admin** → Always displays "Founder & Staff"
2. **Super Admin** → Always displays "Super Administrator"

### **User-Defined Job Roles** (All Others):
- Admins, Members, Guests can have any job role text
- Set by Founder, Super Admin, or Admin (based on permission hierarchy)
- Can be changed at any time by authorized users

### **Profile Display:**
```
User: John Doe
System Role: Admin
Job Role: Engineering Manager
Permissions: Engineering Admin Profile + Project Lead Permission Set
```

---

## Permission Model (Salesforce-Style)

### Permission Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TEAM WORKSPACE                       │
│  (Like a Salesforce Org - Fully Customizable)          │
└─────────────────────────────────────────────────────────┘
                          │
                          ├─── Permission Templates
                          │    └─ Defined by Founder/Super Admin
                          │
                          ├─── Profiles (Base Permission Sets)
                          │    ├─ Admin Profile
                          │    ├─ Member Profile
                          │    └─ Guest Profile
                          │
                          ├─── Permission Sets (Add-ons)
                          │    ├─ Project Manager Access
                          │    ├─ Data Engineer Access
                          │    ├─ Financial Data View
                          │    └─ Code Repository Write
                          │
                          └─── Applied to Users
                               User = Profile + Permission Sets
```

### Permission Scopes

#### **App-Level Permissions** (Feature Access)
- Chat & AI Assistant
- Vault & Document Management
- Workflows & Automations
- Data Engine & Analytics
- Insights Lab
- Code Editor
- Team Collaboration
- P2P Mesh Networking
- Panic Mode & Emergency Features

#### **Resource-Level Permissions** (CRUD Operations)
- **Create**: Can create new resources
- **Read**: Can view resources
- **Update**: Can edit resources
- **Delete**: Can delete resources
- **Share**: Can share with others
- **Export**: Can export data
- **Manage**: Can control permissions

#### **Team Workspace Permissions**
- View team roster
- View team analytics
- Access shared documents
- Edit collaborative docs
- Create team workflows
- Manage team vault
- Invite guests
- Remove guests

#### **Data Permissions** (Salesforce-style Field-Level)
- View sensitive fields
- Edit sensitive fields
- Bulk export data
- Delete records
- Modify permissions
- Access audit logs

---

## Permission Engine

### Permission Engine Core

Create: `apps/backend/api/permission_engine.py`

```python
"""
Permission Engine - Salesforce-inspired RBAC system
Handles all permission checks across ElohimOS
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

class PermissionLevel(Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

class SystemRole(Enum):
    FOUNDER_ADMIN = "founder_admin"
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

@dataclass
class UserPermissionContext:
    """Complete permission context for a user"""
    user_id: str
    username: str
    role: SystemRole
    job_role: Optional[str]
    team_id: Optional[str]
    is_solo_mode: bool
    profile_permissions: Dict[str, any]  # From assigned profiles
    permission_set_permissions: Dict[str, any]  # From assigned permission sets
    effective_permissions: Dict[str, any]  # Merged + calculated

class PermissionEngine:
    """
    Core permission evaluation engine

    Permission Hierarchy (highest to lowest):
    1. Solo Mode: Full access (no restrictions)
    2. Founder Admin (god_rights): Full access (bypasses all checks)
    3. Super Admin: Full team access
    4. Admin/Member/Guest: Profile + Permission Sets
    """

    def __init__(self, db_connection):
        self.db = db_connection
        self._permission_cache = {}  # Cache user permissions

    def get_user_context(self, user_id: str) -> UserPermissionContext:
        """Get complete permission context for user"""
        # Implementation in full doc
        pass

    def has_permission(
        self,
        user_context: UserPermissionContext,
        permission_key: str,
        required_level: PermissionLevel = PermissionLevel.READ
    ) -> bool:
        """Check if user has specific permission"""
        # Solo Mode: Always allowed
        if user_context.is_solo_mode:
            return True

        # Founder Admin: Always allowed
        if user_context.role == SystemRole.FOUNDER_ADMIN:
            return True

        # Super Admin: Always allowed (within team scope)
        if user_context.role == SystemRole.SUPER_ADMIN:
            return True

        # Check effective permissions
        return self._check_permission_in_context(user_context, permission_key, required_level)

    def can_assign_role(
        self,
        user_context: UserPermissionContext,
        target_role: SystemRole
    ) -> bool:
        """Check if user can assign specific role to others"""
        if user_context.role == SystemRole.FOUNDER_ADMIN:
            return True  # Can assign any role

        if user_context.role == SystemRole.SUPER_ADMIN:
            return target_role in [
                SystemRole.ADMIN,
                SystemRole.MEMBER,
                SystemRole.GUEST
            ]

        if user_context.role == SystemRole.ADMIN:
            return target_role == SystemRole.MEMBER

        return False  # Member and Guest cannot assign roles

    def can_elevate_guest(
        self,
        user_context: UserPermissionContext
    ) -> bool:
        """Check if user can elevate guest to full team member"""
        return user_context.role in [
            SystemRole.FOUNDER_ADMIN,
            SystemRole.SUPER_ADMIN
        ]
```

---

## Database Schema (Phase 2)

### Core Tables

#### **1. Users Table (Enhanced)**
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    -- System Role (Permission Level)
    role TEXT NOT NULL DEFAULT 'member',  -- founder_admin, super_admin, admin, member, guest

    -- Job Role (Display Label)
    job_role TEXT,  -- NULL for Founder/Super Admin (hardcoded), user-defined for others

    -- User Profile
    full_name TEXT,
    email TEXT,
    device_name TEXT,

    -- Status
    is_active BOOLEAN DEFAULT 1,
    is_locked BOOLEAN DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,

    -- Team Association
    team_id TEXT,  -- NULL if solo mode
    team_joined_at TEXT,

    -- Guest-specific
    is_guest BOOLEAN DEFAULT 0,
    guest_expires_at TEXT,  -- NULL if not guest or no expiration
    invited_by TEXT,  -- user_id of inviter

    -- Timestamps
    created_at TEXT NOT NULL,
    last_login TEXT,
    role_changed_at TEXT,
    role_changed_by TEXT,  -- user_id who changed role

    -- Security
    password_reset_token TEXT,
    password_reset_expires TEXT,

    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (role_changed_by) REFERENCES users(user_id),
    FOREIGN KEY (invited_by) REFERENCES users(user_id)
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_team ON users(team_id);
CREATE INDEX idx_users_is_guest ON users(is_guest);
```

#### **2. Teams Table**
```sql
CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL,

    -- Team Ownership
    created_by TEXT NOT NULL,  -- user_id of creator (becomes first Super Admin)
    created_at TEXT NOT NULL,

    -- Team Settings
    allow_guests BOOLEAN DEFAULT 1,
    guest_default_expiration_days INTEGER,  -- NULL = no expiration

    -- Team Mode
    is_networked BOOLEAN DEFAULT 0,  -- TRUE if P2P team collaboration enabled
    network_discovery_enabled BOOLEAN DEFAULT 0,

    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE INDEX idx_teams_creator ON teams(created_by);
```

#### **3. Permission Profiles Table**
```sql
CREATE TABLE permission_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL,
    profile_description TEXT,

    -- Scope
    team_id TEXT,  -- NULL = system-wide (for Founder/Super Admin only)
    applies_to_role TEXT NOT NULL,  -- admin, member, guest

    -- Metadata
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    modified_at TEXT,
    is_active BOOLEAN DEFAULT 1,

    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE INDEX idx_profiles_team ON permission_profiles(team_id);
CREATE INDEX idx_profiles_role ON permission_profiles(applies_to_role);
```

#### **4. Permissions Table**
```sql
CREATE TABLE permissions (
    permission_id TEXT PRIMARY KEY,
    permission_key TEXT NOT NULL,  -- e.g., "vault.documents.create", "team.analytics.view"
    permission_name TEXT NOT NULL,  -- Display name
    permission_description TEXT,

    -- Categorization
    category TEXT NOT NULL,  -- "feature", "resource", "data", "team"
    subcategory TEXT,  -- e.g., "vault", "workflows", "chat"

    -- Permission Type
    permission_type TEXT NOT NULL,  -- "boolean", "level", "scope"

    -- Metadata
    is_system BOOLEAN DEFAULT 0,  -- System permissions cannot be deleted
    created_at TEXT NOT NULL
);

CREATE INDEX idx_permissions_key ON permissions(permission_key);
CREATE INDEX idx_permissions_category ON permissions(category);
```

#### **5. Profile Permissions Table** (Join Table)
```sql
CREATE TABLE profile_permissions (
    profile_id TEXT NOT NULL,
    permission_id TEXT NOT NULL,

    -- Permission Value
    is_granted BOOLEAN DEFAULT 1,  -- For boolean permissions
    permission_level TEXT,  -- For level permissions: "read", "write", "admin"
    permission_scope TEXT,  -- JSON array for scope permissions

    PRIMARY KEY (profile_id, permission_id),
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id),
    FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
);
```

#### **6. User Profiles Table** (User → Profile Assignment)
```sql
CREATE TABLE user_profiles (
    user_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,

    -- Assignment
    assigned_by TEXT NOT NULL,
    assigned_at TEXT NOT NULL,

    PRIMARY KEY (user_id, profile_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (profile_id) REFERENCES permission_profiles(profile_id),
    FOREIGN KEY (assigned_by) REFERENCES users(user_id)
);
```

#### **7. Permission Sets Table** (Additional Granular Permissions)
```sql
CREATE TABLE permission_sets (
    permission_set_id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,
    set_description TEXT,

    -- Scope
    team_id TEXT,  -- NULL = system-wide

    -- Metadata
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,

    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);
```

#### **8. User Permission Sets Table** (User → Permission Set Assignment)
```sql
CREATE TABLE user_permission_sets (
    user_id TEXT NOT NULL,
    permission_set_id TEXT NOT NULL,

    -- Assignment
    assigned_by TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    expires_at TEXT,  -- Optional expiration

    PRIMARY KEY (user_id, permission_set_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (permission_set_id) REFERENCES permission_sets(permission_set_id),
    FOREIGN KEY (assigned_by) REFERENCES users(user_id)
);
```

---

## Backend Implementation (Phase 2)

### Permission Middleware

Update: `apps/backend/api/auth_middleware.py`

```python
from api.permission_engine import get_permission_engine, UserPermissionContext

def get_current_user_with_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserPermissionContext:
    """
    Dependency to get current user WITH full permission context

    Use this instead of get_current_user() when you need permission checks
    """
    # Get user from JWT
    user_payload = get_current_user(credentials)

    # Load permission context
    permission_engine = get_permission_engine()
    user_context = permission_engine.get_user_context(user_payload["user_id"])

    return user_context
```

### Update All Service Endpoints

Pattern for updating services:

```python
# BEFORE (No permission check)
@router.get("/workflows")
async def list_workflows():
    workflows = get_all_workflows()
    return workflows

# AFTER (With permission check)
@router.get("/workflows")
async def list_workflows(
    user_context: UserPermissionContext = Depends(get_current_user_with_permissions)
):
    from api.permission_engine import get_permission_engine, PermissionLevel

    perm_engine = get_permission_engine()

    # Check permission
    if not perm_engine.has_permission(
        user_context,
        "workflows.list",
        PermissionLevel.READ
    ):
        raise HTTPException(403, "Access denied")

    # Filter by user (unless Founder/Super Admin)
    if user_context.is_solo_mode:
        workflows = get_workflows_by_user(user_context.user_id)
    elif user_context.role in ["founder_admin", "super_admin"]:
        workflows = get_workflows_by_team(user_context.team_id)
    else:
        workflows = get_workflows_by_user(user_context.user_id)

    return workflows
```

---

## Frontend Implementation

### User Context Hook

Create: `apps/frontend/src/hooks/useUserPermissions.ts`

```typescript
import { useUserStore } from '@/stores/userStore'
import { useMemo } from 'react'

export interface UserPermissions {
  // System Role Info
  role: 'founder_admin' | 'super_admin' | 'admin' | 'member' | 'guest'
  jobRole: string | null

  // Permission Checks
  isFounder: boolean
  isSuperAdmin: boolean
  isAdmin: boolean
  isMember: boolean
  isGuest: boolean

  // Mode
  isSoloMode: boolean
  isTeamMode: boolean

  // Permission Methods
  hasPermission: (permissionKey: string) => boolean
  canAssignRole: (targetRole: string) => boolean
  canSetJobRole: (targetUserRole: string) => boolean
  canElevateGuest: boolean
  canManageUsers: boolean
  canViewAuditLogs: boolean
}

export function useUserPermissions(): UserPermissions {
  const user = useUserStore(state => state.user)
  const permissions = useUserStore(state => state.permissions)

  return useMemo(() => {
    if (!user) return null

    const role = user.role
    const isSoloMode = !user.team_id

    return {
      role,
      jobRole: user.job_role,

      // Role Checks
      isFounder: role === 'founder_admin',
      isSuperAdmin: role === 'super_admin',
      isAdmin: role === 'admin',
      isMember: role === 'member',
      isGuest: role === 'guest',

      // Mode
      isSoloMode,
      isTeamMode: !isSoloMode,

      // Permission Methods
      hasPermission: (permissionKey: string) => {
        if (isSoloMode) return true
        if (role === 'founder_admin') return true
        return permissions?.[permissionKey] === true
      },

      canAssignRole: (targetRole: string) => {
        if (role === 'founder_admin') return true
        if (role === 'super_admin') {
          return ['admin', 'member', 'guest'].includes(targetRole)
        }
        if (role === 'admin') return targetRole === 'member'
        return false
      },

      canSetJobRole: (targetUserRole: string) => {
        if (role === 'founder_admin') return true
        if (role === 'super_admin') {
          return ['admin', 'member', 'guest'].includes(targetUserRole)
        }
        if (role === 'admin') {
          return ['member', 'guest'].includes(targetUserRole)
        }
        return false
      },

      canElevateGuest: ['founder_admin', 'super_admin'].includes(role),
      canManageUsers: ['founder_admin', 'super_admin', 'admin'].includes(role),
      canViewAuditLogs: ['founder_admin', 'super_admin'].includes(role)
    }
  }, [user, permissions])
}
```

### Protected Routes

Create: `apps/frontend/src/components/auth/ProtectedRoute.tsx`

```typescript
import { useUserPermissions } from '@/hooks/useUserPermissions'
import { Navigate } from 'react-router-dom'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredPermission?: string
  requiredRole?: string[]
  fallback?: React.ReactNode
}

export function ProtectedRoute({
  children,
  requiredPermission,
  requiredRole,
  fallback = <Navigate to="/dashboard" />
}: ProtectedRouteProps) {
  const perms = useUserPermissions()

  if (!perms) return <Navigate to="/login" />

  // Check role requirement
  if (requiredRole && !requiredRole.includes(perms.role)) {
    return fallback
  }

  // Check permission requirement
  if (requiredPermission && !perms.hasPermission(requiredPermission)) {
    return fallback
  }

  return <>{children}</>
}
```

---

## Testing Strategy (Phase 2)

### Unit Tests

Create: `apps/backend/tests/test_permission_engine.py`

```python
import pytest
from api.permission_engine import PermissionEngine, SystemRole, PermissionLevel

def test_solo_mode_full_access():
    """Solo mode users should have full access"""
    pass

def test_founder_admin_bypasses_all():
    """Founder admin should bypass all permission checks"""
    pass

def test_super_admin_team_scope():
    """Super admin should have access to all team resources"""
    pass

def test_admin_limited_role_assignment():
    """Admin should only be able to assign Member role"""
    pass

def test_guest_expiration():
    """Guest access should be denied after expiration"""
    pass

def test_permission_merging():
    """Permission sets should add to profile permissions"""
    pass
```

### Integration Tests

```python
def test_multi_user_isolation_with_roles():
    """
    Test complete user isolation with different roles

    Verify:
    - Each user only sees their own data
    - Founder sees ALL data
    - Super Admin sees all Team A data
    - Admin has limited Team A access
    - Guest has restricted Team A access
    - Team A users cannot see Team B data
    """
    pass
```

---

## Timeline & Risks

### Phase 2 Timeline Estimate

**Phase 1: Database & Schema (1 week)**
- Create new permission tables
- Add user_id to all existing tables
- Write migration scripts

**Phase 2: Permission Engine (1 week)**
- Implement PermissionEngine class
- Implement permission merging logic
- Write unit tests

**Phase 3: Backend Services (2-3 weeks)**
- Update auth_middleware with permission context
- Update 18 services with permission checks
- Test each service individually

**Phase 4: Frontend Implementation (1-2 weeks)**
- Create permission hooks
- Implement conditional rendering
- Build Support Dashboard

**Phase 5: Testing & QA (1 week)**
- Integration tests
- Security testing
- Performance testing

**Phase 6: Documentation (3-4 days)**
- User guide
- Admin guide
- Developer guide

**Total Phase 2: 6-8 weeks of focused development**

### Combined Timeline
**Phase 1 + Phase 2: 8-11 weeks total**

### Risks & Mitigations

#### Risk 1: Data Loss During Migration
**Impact:** HIGH
**Mitigation:**
- Full backup before any changes
- Test migrations on copy of production data
- Rollback scripts ready

#### Risk 2: Performance Impact
**Impact:** MEDIUM
**Mitigation:**
- Add indexes on all permission-related columns
- Cache user permission context in memory
- Use connection pooling

#### Risk 3: Breaking Existing Deployments
**Impact:** HIGH
**Mitigation:**
- Feature flag for new permission system
- Backward compatibility mode
- Gradual migration path

#### Risk 4: Permission Complexity
**Impact:** MEDIUM
**Mitigation:**
- Start with simple permission model
- Add complexity gradually
- Clear documentation and examples

---

# Quick Reference

## God Rights Credentials

### Development
**Username:** `elohim_founder`
**Password:** `ElohimOS_2024_Founder`

### Production Setup
Set these environment variables:

```bash
ELOHIM_GOD_USERNAME="elohim_founder"  # Optional, defaults to this
ELOHIM_GOD_PASSWORD="your-secure-password-here"  # REQUIRED
ELOHIM_ENV="production"  # Enforces password requirement
```

**IMPORTANT:** The default password only works when `ELOHIM_ENV=development`. Production REQUIRES setting `ELOHIM_GOD_PASSWORD`.

### How It Works

1. When user logs in with `elohim_founder` username, auth checks if it matches `GOD_RIGHTS_USERNAME`
2. Validates password against `GOD_RIGHTS_PASSWORD` (bypasses user database)
3. Creates JWT token with `role: "god_rights"` and `user_id: "god_rights"`
4. This account has full access to all system features

### Security Notes

- Account cannot be disabled through normal means
- Failed login attempts are logged
- Access restricted to trusted team members only
- Consider rotating password periodically
- Use strong, unique password in production

---

## Service Implementation Status

### Phase 1: User Isolation

| Service | Status | Notes |
|---------|--------|-------|
| chat_service.py | ✅ COMPLETED | User filtering implemented, God Rights bypass working |
| vault_service.py | ⚠️ TODO | Add user filtering to all vault queries |
| workflow_service.py | ⚠️ TODO | Filter workflows and executions by user_id |
| user_service.py | ⚠️ TODO | Restrict profile editing to owner/God Rights |
| team_service.py | ⚠️ TODO | Filter team data by user's team |
| insights_service.py | ⚠️ TODO | Filter insights by user_id |
| docs_service.py | ⚠️ TODO | Filter documents by user_id |
| backup_service.py | ⚠️ TODO | Include user_id in backups |
| trash_service.py | ⚠️ TODO | Filter trash by user_id |
| code_editor_service.py | ⚠️ TODO | Filter saved code by user_id |
| undo_service.py | ⚠️ TODO | Filter undo history by user_id |
| p2p_chat_service.py | ⚠️ TODO | Verify team permissions |
| encrypted_db_service.py | ⚠️ TODO | Ensure keys are user-specific |
| lan_discovery.py | ⚠️ TODO | Review isolation requirements |
| mesh_service.py | ⚠️ TODO | Review isolation requirements |
| panic_mode_service.py | ⚠️ TODO | Review isolation requirements |
| secure_enclave_service.py | ⚠️ TODO | Review isolation requirements |
| automation_service.py | ⚠️ TODO | Filter automations by user_id |

### Phase 2: RBAC System

| Component | Status | Notes |
|-----------|--------|-------|
| Database Schema | 📋 PLANNED | 10 new tables for permissions |
| Permission Engine | 📋 PLANNED | Core permission evaluation logic |
| Auth Middleware | 📋 PLANNED | Permission context injection |
| Service Updates | 📋 PLANNED | 18 services need permission checks |
| Frontend Hooks | 📋 PLANNED | Permission-aware UI components |
| Support Dashboard | 📋 PLANNED | God Rights admin interface |
| Migration Scripts | 📋 PLANNED | Database migration automation |
| Tests | 📋 PLANNED | Unit + integration + security tests |

---

## Summary

This document represents the complete security and permissions architecture for ElohimOS, combining:

1. **Phase 1: User Isolation** - Critical security foundation ensuring users cannot access each other's data
2. **Phase 2: RBAC System** - Comprehensive Salesforce-inspired permission system with full customizability

**Critical Success Factors:**
- Meticulous planning and design
- Thorough testing at every phase
- Clear documentation
- Gradual rollout with fallback options
- Performance optimization from the start

**Recommended Approach:**
1. Complete Phase 1 (user isolation) first - 2-3 weeks
2. Test thoroughly with multiple users
3. Begin Phase 2 (RBAC) once Phase 1 is stable - 6-8 weeks
4. Monitor closely after each deployment

This architecture will make ElohimOS production-ready for multi-user environments while maintaining the simplicity and power of solo mode for individual users.

---

**Copyright (c) 2025 MagnetarAI, LLC**
**Built with conviction for mission-critical field operations.**

---

# APOLLO-LEVEL SYSTEMS ENGINEERING ROADMAP
## ElohimOS / MagnetarAI Security, Permissions & Intelligence Platform

**Engineering Philosophy:** Separation of Concerns | Systems of Systems | Proven Interfaces | Incremental Validation  
**Mission:** Build indestructible core → Enable field partners to extend via SDK → Change the world

---

## Executive Summary

This roadmap applies **Apollo Program systems engineering principles** to ElohimOS development:
- ✅ **Separation of Concerns** - Each component has ONE job, clear interfaces, independent testing
- ✅ **Incremental Build & Test** - Validate each phase before proceeding (like Apollo missions 1-11 before moon landing)
- ✅ **Interface Specifications First** - Define APIs before implementation (like Excel in JSON pipeline)
- ✅ **Systems of Systems** - ElohimOS (Core) → MagnetarIntelligence (AI) → MagnetarSDK (Extensions)
- ✅ **Quick Wins First** - Mission success criteria, least complex → most complex

---

## PART 3: SYSTEMS OF SYSTEMS ARCHITECTURE

### System 1: ElohimOS Core Platform
**Purpose:** Offline-first foundation for mission-critical operations  
**Components:**
- Authentication & User Management
- Data Engine (with Big Query schema discovery)
- Vault & Document Management
- Chat & AI Orchestration
- Workflows & Automation
- P2P Mesh Networking

### System 2: MagnetarIntelligence (AI Code Assistant)
**Purpose:** Local AI-powered development and diagnostics (replaces Claude Code + ChatGPT)  
**Components:**
- Terminal Bridge (spawns preferred macOS terminal with context)
- Code Agent (multi-file operations using codex-main)
- Schema Discovery Agent (256-template brute-force engine from Big Query)
- Diagnostic Agent (ElohimOS health monitoring)
- Semantic Search Engine (code and data navigation)
- Recursive Prompt Engine (already in ElohimOS chat)

### System 3: MagnetarSDK (Extension Framework)
**Purpose:** Enable field partners to build offline-capable apps on ElohimOS  
**Components:**
- REST API Layer
- Offline Sync Framework
- Plugin Architecture
- Health Equipment Connectors
- Field Data Collection Tools
- Mission Coordination Interfaces

**Field Partner Examples:**
- **Doctors Without Borders:** Offline medical records + health equipment integration
- **International Mission Board:** Mission coordination + resource tracking
- **Engineering Teams:** Project management + infrastructure monitoring

---

## PART 4: COMPREHENSIVE SECURITY VALIDATION CHECKLIST

### 1. Multi-User Isolation
- [x] **Confirm each local user has unique encrypted credentials**
  - JWT tokens with user_id, username, role
  - PBKDF2 password hashing (600k iterations)
  - Per-user sessions in database
- [ ] **Test cross-account data leakage**
  - ✅ Chat isolation tests passing
  - ✅ Personal vault privacy confirmed
  - ⚠️ God Rights sees ALL chats (needs admin endpoint separation)
  - ⚠️ Need tests for: workflows, settings, teams
- [ ] **Validate role permissions**
  - ✅ Founder Admin (god_rights) can access everything
  - ⚠️ Super Admin capabilities not fully implemented
  - ⚠️ Admin/Member/Guest roles defined but not enforced
  - ⚠️ Job role assignment system pending

### 2. Role-Based Access Control
- [ ] **Verify role hierarchy**
  - ✅ Founder Admin > Super Admin > Admin > Member > Guest (defined)
  - ⚠️ Permission inheritance not implemented
  - ⚠️ Profile + Permission Set system pending (Phase 2)
- [ ] **Check resource-access matrix**
  - ✅ Personal vault: Owner only (God Rights CANNOT see)
  - ✅ Personal chats: Owner only (God Rights CAN see via bypass)
  - ⚠️ Team vault: Access control not implemented
  - ⚠️ Shared resources: Permission system pending
- [ ] **Confirm privilege escalation prevention**
  - ⚠️ Role assignment logic exists but not tested
  - ⚠️ No audit logging of role changes yet
  - ⚠️ No lateral role switching prevention (Phase 2)

### 3. Founder / Support Space
- [ ] **Support tools sandboxed from production data**
  - ⚠️ God Rights currently sees ALL data in regular endpoints (needs fixing)
  - ⚠️ Separate `/api/v1/admin/*` endpoints needed
  - ⚠️ Support Dashboard UI not yet built
- [ ] **Diagnostic logs anonymized and encrypted**
  - ⚠️ Logging exists but not anonymized
  - ⚠️ No log encryption yet
  - ⚠️ No PII scrubbing
- [ ] **Clear separation between "observe" and "control" capabilities**
  - ⚠️ God Rights can both observe AND control (correct)
  - ⚠️ Need read-only diagnostic mode for support staff
  - ⚠️ Action audit logging pending

### 4. Audit & Session Management
- [ ] **Add encrypted local audit trail**
  - ⚠️ Audit log schema defined but not implemented
  - ⚠️ No encryption of audit logs yet
  - ⚠️ Events to log: God Rights actions, role changes, password resets, vault access
- [ ] **Time-stamp and hash each log entry**
  - ⚠️ Timestamp exists but no integrity hashing
  - ⚠️ No tamper detection
- [ ] **Verify logs purge correctly when Panic Mode triggered**
  - ⚠️ Panic Mode exists but audit log integration pending
  - ⚠️ Need secure deletion verification

### 5. Data Protection
- [x] **All user data encrypted at rest**
  - ✅ Vault: Client-side encryption (AES-256)
  - ✅ Chat: Database encryption at rest
  - ⚠️ Settings: Not encrypted (consider encrypting sensitive fields)
- [x] **Verify dual-vault (real / decoy) functionality**
  - ✅ Vault supports `vault_type = 'real' | 'decoy'`
  - ✅ Separate encryption keys
  - ⚠️ Plausible deniability UI flow needs testing
- [ ] **Test Panic / Emergency modes for full data wipe**
  - ⚠️ Panic Mode exists but data wipe not verified
  - ⚠️ Need test: trigger panic → verify all user data removed
  - ⚠️ Need recovery test: restore from backup after panic

### 6. Networking / P2P Security
- [ ] **TLS / mutual-auth handshake for peer connections**
  - ⚠️ P2P mesh exists but TLS not verified
  - ⚠️ Certificate pinning needed
  - ⚠️ Mutual authentication pending
- [ ] **Rate-limit and authenticate file transfers**
  - ⚠️ File transfer exists but no rate limiting
  - ⚠️ No transfer size limits
  - ⚠️ No bandwidth throttling
- [ ] **Confirm mesh discovery doesn't expose device metadata**
  - ⚠️ LAN discovery uses device fingerprints
  - ⚠️ Need privacy audit of broadcast data
  - ⚠️ No anonymization of discovery packets

### 7. Code Integrity
- [ ] **Sign builds with distinct keys per release channel**
  - ⚠️ No code signing yet
  - ⚠️ Need separate keys for dev/staging/prod
  - ⚠️ No binary verification on startup
- [ ] **Run local checksum / signature verification on startup**
  - ⚠️ No integrity checks on boot
  - ⚠️ No tamper detection
  - ⚠️ No secure boot sequence
- [ ] **Confirm CI/CD pipeline isolated from user data paths**
  - ⚠️ No CI/CD yet
  - ⚠️ Need isolation architecture when implemented

### 8. Threat Modeling
- [ ] **Simulate device seizure → confirm Panic Mode clears traces**
  - ⚠️ Panic Mode exists but seizure scenario not tested
  - ⚠️ Need forensic analysis after panic trigger
  - ⚠️ Verify RAM clearing (if possible)
- [ ] **Simulate compromised account → verify role isolation holds**
  - ✅ User isolation tests confirm cross-user protection
  - ⚠️ Need test: compromised Member cannot escalate to Admin
  - ⚠️ Need test: stolen token cannot access other users' data
- [ ] **Run local red-team tests on vault + mesh subsystems**
  - ⚠️ No penetration testing yet
  - ⚠️ Need vault decryption attack tests
  - ⚠️ Need P2P mesh injection tests

### 9. Compliance Alignment
- [ ] **Map features to HIPAA / GDPR / SOC-2 equivalents**
  - ⚠️ No compliance mapping yet
  - ⚠️ Need data classification framework
  - ⚠️ Need right-to-delete implementation (GDPR Article 17)
- [ ] **Create security summary doc for pilot partners**
  - ⚠️ No security whitepaper yet
  - ⚠️ Need threat model documentation
  - ⚠️ Need data flow diagrams
- [ ] **Add consent + data-handling notice in onboarding**
  - ⚠️ No privacy policy in app
  - ⚠️ No consent flow
  - ⚠️ No data retention policy

**Goal:** One pass through this checklist = ready for closed-beta security validation

---

## PART 5: PHASED IMPLEMENTATION ROADMAP

### PHASE 0: Critical Security Fixes (IMMEDIATE - 1-2 Days)
**Priority:** P0 - Critical security vulnerabilities  
**Complexity:** LOW - Quick wins, high impact  
**Apollo Parallel:** Like fixing the Apollo 1 oxygen system before any launches

#### Tasks:
1. **Fix list_sessions God Rights leak** (2 hours)
   - Remove God Rights bypass in regular `/api/v1/chat/sessions` endpoint
   - God Rights should see only their own chats in regular UI
   - Create separate admin endpoint for support access

2. **Fix vault endpoint authentication** (COMPLETED ✅)
   - Added `Depends(get_current_user)` to get/update/delete endpoints
   - Verified user isolation working

3. **Add `role` column to database schema** (COMPLETED ✅)
   - Updated `users` table with `role TEXT DEFAULT 'member'`
   - Fixed authenticate() to fetch and return role
   - JWT tokens now include role

4. **Add persistent JWT_SECRET** (COMPLETED ✅)
   - Set `ELOHIM_JWT_SECRET` in start_web.sh
   - Tokens no longer invalidate on server restart

#### Validation:
- [ ] Run test_user_isolation.py → 100% pass
- [x] Run test_vault_privacy.py → Personal vault private ✅
- [ ] Run test_god_rights_admin.py → Admin endpoints work

---

### PHASE 1A: User Isolation Foundation (WEEK 1 - 5 Days)
**Priority:** P0 - Foundation for all security  
**Complexity:** MEDIUM - Clear requirements, systematic implementation  
**Apollo Parallel:** Command Module life support - must work before anything else

#### Interface Specification:
All services must implement this pattern:
```python
@router.get("/resource")
async def get_resource(current_user: Dict = Depends(get_current_user)):
    """Get resource filtered by user_id"""
    user_id = current_user["user_id"]
    role = current_user.get("role")

    # User isolation: filter by user_id
    # God Rights bypass: if role == "god_rights", skip filter (via admin endpoints only)
    resources = get_resources_by_user(user_id)
    return resources
```

#### Services to Update (18 total):
**Day 1-2: Core Services**
- [x] chat_service.py ✅
- [ ] vault_service.py (critical - partially done)
- [ ] workflow_service.py
- [ ] user_service.py

**Day 3: Settings & Preferences**
- [ ] settings_service.py (user settings isolation)
- [ ] model_config_service.py (per-user model preferences)

**Day 4: Collaboration Services**
- [ ] team_service.py
- [ ] docs_service.py
- [ ] p2p_chat_service.py

**Day 5: Utility Services**
- [ ] backup_service.py
- [ ] trash_service.py
- [ ] undo_service.py
- [ ] automation_service.py

#### Validation:
```bash
# Test suite for each service
python test_service_isolation.py --service=vault
python test_service_isolation.py --service=workflows
python test_service_isolation.py --service=teams
# ... etc for all 18 services
```

---

### PHASE 1B: Admin Endpoints & Support Dashboard (WEEK 2 - 5 Days)
**Priority:** P0 - Required for field support  
**Complexity:** MEDIUM - New endpoints + UI  
**Apollo Parallel:** Mission Control interface - observe & control capabilities

#### Interface Specification:
```python
# apps/backend/api/admin_endpoints.py

@router.get("/api/v1/admin/users")
async def list_all_users(current_user: Dict = Depends(get_current_user)):
    """List all users on device (Founder/Super Admin only)"""
    if current_user["role"] not in ["god_rights", "super_admin"]:
        raise HTTPException(403, "Admin access required")

    users = get_all_users()  # No filtering - admin sees all
    return {"users": users}

@router.get("/api/v1/admin/users/{user_id}/chats")
async def get_user_chats_admin(user_id: str, current_user: Dict = Depends(get_current_user)):
    """Get specific user's chats (God Rights only - for support)"""
    if current_user["role"] != "god_rights":
        raise HTTPException(403, "Founder access required")

    chats = get_chats_by_user(user_id)  # Explicit admin access
    return {"chats": chats, "user_id": user_id}

@router.post("/api/v1/admin/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, new_password: str, current_user: Dict = Depends(get_current_user)):
    """Reset user password (Founder/Super Admin)"""
    if current_user["role"] not in ["god_rights", "super_admin"]:
        raise HTTPException(403, "Admin access required")

    reset_password(user_id, new_password)
    audit_log.log_action(current_user["user_id"], "password_reset", user_id)
    return {"success": True}
```

#### Admin Endpoints to Create:
**User Management:**
- `GET /api/v1/admin/users` - List all users
- `GET /api/v1/admin/users/{user_id}` - Get user details + stats
- `POST /api/v1/admin/users/{user_id}/unlock` - Unlock account
- `POST /api/v1/admin/users/{user_id}/reset-password` - Reset password
- `PUT /api/v1/admin/users/{user_id}/role` - Change role
- `DELETE /api/v1/admin/users/{user_id}` - Delete user

**Support Access (God Rights only):**
- `GET /api/v1/admin/users/{user_id}/chats` - View user's chats
- `GET /api/v1/admin/users/{user_id}/vault-stats` - Vault statistics (NOT contents)
- `GET /api/v1/admin/users/{user_id}/workflows` - View user's workflows
- `GET /api/v1/admin/users/{user_id}/activity` - Recent activity log

**Device Overview:**
- `GET /api/v1/admin/device/overview` - Total users, teams, storage
- `GET /api/v1/admin/device/audit-logs` - System audit logs

#### Frontend: Support Dashboard
**Location:** `apps/frontend/src/components/admin/SupportDashboard.tsx`

**Features:**
- User list with search/filter
- User detail view with stats
- Account management actions (unlock, reset, delete)
- Device overview metrics
- Audit log viewer

**Access Control:**
- Only visible when `current_user.role === "god_rights"`
- Add `</>` icon in header for admin access (role-based)

---

### PHASE 1C: Audit Logging & Compliance (WEEK 3 - 3 Days)
**Priority:** P1 - Required for production  
**Complexity:** LOW - Well-defined requirements  
**Apollo Parallel:** Flight recorder - log everything for analysis

#### Implementation:
```python
# apps/backend/api/audit_logger.py

class AuditLogger:
    def log_action(
        self,
        user_id: str,
        action: str,
        target_user: str = None,
        target_resource: str = None,
        details: Dict = None,
        ip_address: str = None
    ):
        """Log security-sensitive action"""
        conn = get_audit_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_logs (
                timestamp, user_id, username, role, action,
                target_user_id, target_resource, details,
                ip_address, integrity_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_id,
            get_username(user_id),
            get_user_role(user_id),
            action,
            target_user,
            target_resource,
            json.dumps(details),
            ip_address,
            calculate_integrity_hash(...)  # SHA-256 of entry
        ))

        conn.commit()
```

#### Actions to Log:
- God Rights login/logout
- Admin password resets
- Role changes
- Account unlocks/disables
- Vault mode switches (real ↔ decoy)
- Failed login attempts (> 3)
- Data exports
- Panic Mode triggers

#### Validation:
- Test audit log integrity (tamper detection)
- Test log rotation (keep 90 days)
- Test Panic Mode log purge

---

### PHASE 2: RBAC Permission System (WEEKS 4-9 - 6 Weeks)
**Priority:** P1 - Required for team mode  
**Complexity:** HIGH - Complex permission merging logic  
**Apollo Parallel:** Lunar Module - complex subsystem with many moving parts

**Sub-Phases:**
1. **Database Schema** (Week 4) - Create 10 new permission tables
2. **Permission Engine** (Week 5) - Core permission evaluation logic
3. **Service Integration** (Weeks 6-7) - Update 18 services with permission checks
4. **Frontend UI** (Week 8) - Permission-aware components
5. **Testing & QA** (Week 9) - Comprehensive testing

**Detailed plan in Part 2 above** ✅

---

### PHASE 3: MagnetarIntelligence - AI Code Assistant (WEEKS 10-15 - 6 Weeks)
**Priority:** P2 - High value, builds on stable core  
**Complexity:** VERY HIGH - Integrating 4 major systems  
**Apollo Parallel:** Lunar surface operations - only possible after successful landing

#### Architecture:
```
User clicks </> icon in header (role-based access)
    ↓
ElohimOS spawns user's preferred terminal (iTerm2, Warp, Terminal.app)
    ↓
Terminal launched with ElohimOS context injected
    ↓
MagnetarIntelligence agents activate:
    - Terminal Bridge (bidirectional communication)
    - Code Agent (codex-main for file ops)
    - Schema Agent (Big Query 256-template engine)
    - Diagnostic Agent (ElohimOS health monitoring)
    - Semantic Search (code & data navigation from Jarvis)
    ↓
Recursive Prompt Loop (existing chat orchestration)
    - User: "Fix the authentication bug"
    - AI: Analyzes code → Suggests fix → Applies multi-file changes → Runs tests → Iterates
    - All while maintaining chat history + file context
    ↓
Result: Local, unified Claude Code + ChatGPT replacement
```

#### Sub-Phases:

**Week 10: Extract & Integrate Big Query Schema Engine**
- Extract 256-template brute-force schema discovery
- Integrate into ElohimOS data engine
- Test with ElohimOS databases

**Week 11: Extract & Integrate Jarvis Agent Engine**
- Extract agent orchestration framework
- Extract semantic search capabilities
- Integrate with ElohimOS chat orchestration

**Week 12: Integrate codex-main (Rust CLI)**
- Build Rust bridge to ElohimOS
- Integrate file operations (read, write, search)
- Test multi-file refactoring

**Week 13: Integrate continue-main (Code Intelligence)**
- Integrate code navigation
- Integrate test generation
- Integrate semantic code search

**Week 14: Build Terminal Bridge**
- macOS terminal detection (iTerm2, Warp, Terminal.app)
- Spawn terminal with context
- Bidirectional communication (terminal ↔ ElohimOS)
- Command execution & output capture

**Week 15: UI & Testing**
- Add `</>` icon in header (role-based visibility)
- Build MagnetarIntelligence chat interface
- Test full workflows (code editing, debugging, diagnostics)

#### Validation:
```
Test Case 1: Code Editing
- User: "Refactor auth_middleware.py to use async"
- Expected: Multi-file changes, tests pass, git commit

Test Case 2: Database Diagnostics
- User: "Why is my query slow?"
- Expected: Schema analysis, query plan, optimization suggestions

Test Case 3: Bug Fixing
- User: "Fix the 401 error in vault endpoints"
- Expected: Find bug, suggest fix, apply changes, verify with tests
```

---

### PHASE 4: MagnetarSDK - Extension Framework (WEEKS 16-21 - 6 Weeks)
**Priority:** P2 - Enables field partner ecosystem  
**Complexity:** HIGH - New architecture, must be stable  
**Apollo Parallel:** Lunar Module descent engine - enables landing, must be bulletproof

#### Architecture:
```
ElohimOS Core
    ↓
MagnetarSDK (REST API + Offline Sync + Plugin Framework)
    ↓
Field Partner Apps (built on SDK)
    - Doctors Without Borders: Medical Records + Equipment Integration
    - International Mission Board: Coordination Tools
    - Engineering Teams: Project Management
```

#### Sub-Phases:

**Week 16-17: SDK API Layer**
- RESTful API for all core features
- Authentication & authorization
- Rate limiting & quotas
- API documentation (OpenAPI/Swagger)

**Week 18: Offline Sync Framework**
- Conflict resolution (CRDTs or operational transforms)
- Delta sync (only changed data)
- Background sync queue
- Retry logic with exponential backoff

**Week 19: Plugin Architecture**
- Plugin manifest schema
- Sandboxed plugin execution
- Inter-plugin communication
- Plugin marketplace framework

**Week 20: Reference Implementations**
- Sample app: Health equipment connector
- Sample app: Field data collection
- Sample app: Mission coordination dashboard

**Week 21: Documentation & Testing**
- SDK documentation
- Developer guide
- API reference
- Integration tests

---

## PART 6: ROLE CAPABILITIES MATRIX

### What Each Role Needs To Do Their Job

#### Founder Admin (god_rights)
**Purpose:** Field support, emergency access, system-wide administration

**Account Management:**
- ✅ View all users on device (username, user_id, email, status)
- ✅ Reset any user's password
- ✅ Unlock any account
- ✅ Assign/change any role
- ✅ Delete any account
- ✅ Create multiple Founder accounts for trusted staff

**Support Access:**
- ✅ View any user's chats (for support - NOT in regular UI)
- ✅ View vault statistics (# documents, size - NOT decrypted contents)
- ✅ View any user's workflows
- ✅ Access team vault (organizational data)
- ❌ CANNOT decrypt personal vault (privacy protection)

**System Monitoring:**
- ✅ Device overview (total users, teams, storage, memory)
- ✅ Full audit log access
- ✅ System health diagnostics (Metal GPU, processes, performance)
- ✅ Database analytics

**MagnetarIntelligence Access:**
- ✅ Full terminal access with all diagnostic tools
- ✅ Database schema discovery
- ✅ Code editing for ElohimOS itself
- ✅ System-level command execution

#### Super Admin
**Purpose:** Team leadership, user management, team configuration

**User Management:**
- ✅ View all users in their team
- ✅ Assign Admin, Member, Guest roles (NOT Founder or other Super Admin)
- ✅ Set job roles for team members
- ✅ Create guest accounts with expiration
- ✅ Elevate guests to full members
- ✅ Reset team member passwords
- ✅ Unlock team member accounts

**Team Configuration:**
- ✅ Configure team workspace settings
- ✅ Define permission templates
- ✅ Create permission profiles
- ✅ Manage team vault access
- ✅ Set team-wide policies

**Analytics & Reporting:**
- ✅ View team-wide analytics (aggregate data)
- ❌ CANNOT see individual user's private data
- ✅ Team activity logs
- ✅ Resource usage by team

**MagnetarIntelligence Access:**
- ✅ Terminal access for team-related diagnostics
- ✅ Team database queries
- ⚠️ Limited code editing (team-specific features only)

#### Admin
**Purpose:** Team moderation, limited user help, resource management

**User Management:**
- ✅ Assign Member role only
- ✅ Create guest accounts
- ✅ Set job roles for Members and Guests
- ❌ CANNOT assign Admin or higher roles
- ❌ CANNOT elevate guests to members (escalate to Super Admin)

**Resource Management:**
- ✅ Manage resources they're given permission to manage
- ✅ View analytics they're permitted to see
- ✅ Moderate team discussions/documents

**MagnetarIntelligence Access:**
- ⚠️ Limited terminal access (based on permission sets)
- ⚠️ Read-only database queries
- ❌ No code editing

#### Member
**Purpose:** Standard user with full personal workspace

**Personal Workspace:**
- ✅ Full access to own chats, docs, vault
- ✅ Use all app features (AI, workflows, data engine)
- ✅ Personal vault (fully private - even from Founder)
- ✅ Personal settings & preferences

**Team Collaboration:**
- ✅ Access shared team resources (based on permissions)
- ✅ Collaborate on documents they're invited to
- ✅ Participate in team workflows
- ⚠️ Team resource access controlled by permission sets

**MagnetarIntelligence Access:**
- ✅ Terminal access for personal development
- ✅ Personal database queries
- ✅ Code editing for personal projects
- ❌ No system-level access

#### Guest
**Purpose:** Temporary/external access with restrictions

**Personal Workspace:**
- ✅ Full personal workspace access (own chats, AI, personal docs)
- ✅ Personal vault (private)
- ✅ Use app features in personal space

**Team Workspace:**
- ⚠️ LIMITED access to shared resources (permission-based)
- ⚠️ Can only see specific projects they're invited to
- ❌ Cannot see team roster by default
- ❌ Cannot see team-wide analytics

**Restrictions:**
- ❌ Cannot create other users or guests
- ❌ Cannot be elevated to Member by Admins (only Super Admin/Founder)
- ⚠️ May have time-limited access (expiration date)
- ❌ No MagnetarIntelligence access

---

## PART 7: INTERFACE SPECIFICATIONS (Apollo-Level)

### Core Interfaces That Must Remain Stable

#### 1. Authentication Interface
```python
# INTERFACE SPEC - DO NOT BREAK
def authenticate(username: str, password: str) -> Dict:
    """
    Returns:
    {
        "token": str,         # JWT token
        "user_id": str,       # User identifier
        "username": str,      # Username
        "role": str,          # System role
        "device_id": str      # Device identifier
    }
    """
```

#### 2. User Filtering Interface
```python
# INTERFACE SPEC - ALL SERVICES MUST IMPLEMENT
@router.get("/resource")
async def get_resource(current_user: Dict = Depends(get_current_user)):
    """
    current_user contains:
    - user_id: str
    - username: str
    - role: str
    - device_id: str
    """
```

#### 3. Permission Check Interface
```python
# INTERFACE SPEC - PHASE 2
def has_permission(
    user_context: UserPermissionContext,
    permission_key: str,
    required_level: PermissionLevel
) -> bool:
    """Universal permission check - DO NOT BREAK"""
```

#### 4. Admin Endpoint Interface
```python
# INTERFACE SPEC - ADMIN ENDPOINTS
# Pattern: /api/v1/admin/{resource}/{action}
# Auth: Founder or Super Admin only
# Response: Always includes audit log entry
```

#### 5. MagnetarSDK Interface (Phase 4)
```python
# INTERFACE SPEC - SDK API
# Base URL: /api/v1/sdk/
# Auth: API key + JWT token
# Versioning: /api/v1/sdk/ (v1), /api/v2/sdk/ (v2)
# Backward compatibility: MUST maintain for 2 major versions
```

---

## PART 8: TESTING STRATEGY (Systems Engineering Level)

### Unit Tests (Component Level)
Each function/class tested in isolation:
```bash
pytest apps/backend/tests/unit/test_auth.py
pytest apps/backend/tests/unit/test_permissions.py
pytest apps/backend/tests/unit/test_vault.py
```

### Integration Tests (System Level)
Multiple components working together:
```bash
pytest apps/backend/tests/integration/test_user_isolation.py
pytest apps/backend/tests/integration/test_rbac_system.py
pytest apps/backend/tests/integration/test_vault_privacy.py
```

### System Tests (End-to-End)
Full user workflows:
```bash
pytest apps/backend/tests/system/test_complete_user_journey.py
# Tests: Register → Login → Create chat → Use vault → Logout
```

### Security Tests (Red Team)
Adversarial testing:
```bash
pytest apps/backend/tests/security/test_privilege_escalation.py
pytest apps/backend/tests/security/test_data_leakage.py
pytest apps/backend/tests/security/test_token_manipulation.py
```

### Performance Tests (Load Testing)
```bash
locust -f apps/backend/tests/performance/load_test.py
# Test: 100 concurrent users, 1000 requests/sec
```

### Validation Criteria (Go/No-Go for Each Phase)
**Phase cannot proceed unless:**
- ✅ All unit tests passing (100%)
- ✅ All integration tests passing (100%)
- ✅ Code coverage > 80%
- ✅ Security tests passing (no critical vulnerabilities)
- ✅ Performance benchmarks met
- ✅ Manual QA sign-off

---

## PART 9: MIGRATION & ROLLBACK STRATEGY

### Migration Philosophy
**Never deploy a change without a rollback plan** (Apollo rule)

#### Pre-Migration Checklist:
1. Full database backup
2. Full codebase backup
3. Test migration on copy of production data
4. Rollback script tested and ready
5. Communication plan (notify users of downtime)

#### Migration Execution:
```bash
# 1. Backup
./scripts/backup_all_data.sh

# 2. Run migration
python apps/backend/api/migrate_phase_X.py

# 3. Verify
python apps/backend/api/verify_migration.py

# 4. If verification fails → ROLLBACK
python apps/backend/api/rollback_migration.py
```

#### Rollback Criteria:
Rollback if ANY of these occur:
- Data loss detected
- Critical functionality broken
- Performance degradation > 50%
- Security vulnerability introduced
- User complaints > threshold

---

## PART 10: SUCCESS METRICS

### Phase 0: Critical Fixes
- ✅ test_user_isolation.py: 100% pass
- ✅ test_vault_privacy.py: 100% pass
- ✅ No God Rights data leakage in regular endpoints

### Phase 1A: User Isolation
- ✅ All 18 services have user filtering
- ✅ Cross-user data access: 0 vulnerabilities
- ✅ Performance impact: < 10% query time increase

### Phase 1B: Admin Endpoints
- ✅ Support Dashboard functional
- ✅ All admin actions logged
- ✅ Founder can reset passwords, unlock accounts

### Phase 1C: Audit Logging
- ✅ 100% of sensitive actions logged
- ✅ Logs tamper-resistant (integrity hashes)
- ✅ Panic Mode purges logs successfully

### Phase 2: RBAC
- ✅ Permission engine: 100% test coverage
- ✅ 5 roles fully functional (Founder/Super/Admin/Member/Guest)
- ✅ Profile + Permission Set system working
- ✅ Solo mode: zero restrictions
- ✅ Team mode: permissions enforced

### Phase 3: MagnetarIntelligence
- ✅ Terminal bridge works with iTerm2, Warp, Terminal.app
- ✅ Code Agent: multi-file edits successful
- ✅ Schema Agent: 256-template discovery working
- ✅ Diagnostic Agent: ElohimOS health monitoring
- ✅ User satisfaction: "Better than Claude Code" feedback

### Phase 4: MagnetarSDK
- ✅ 3 reference implementations working
- ✅ SDK documentation complete
- ✅ 1 field partner pilot successful (Doctors Without Borders or IMB)

---

## PART 11: RISK REGISTER

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss during migration | CRITICAL | LOW | Full backups, tested rollback, gradual rollout |
| Performance degradation | HIGH | MEDIUM | Indexes, caching, connection pooling, load testing |
| Security vulnerability | CRITICAL | MEDIUM | Security tests, code review, penetration testing |
| Breaking existing deployments | HIGH | MEDIUM | Feature flags, backward compatibility, gradual migration |
| Permission system too complex | MEDIUM | HIGH | Start simple, add complexity gradually, clear docs |
| God Rights password leak | CRITICAL | LOW | Strong password requirement, rate limiting, audit logs |
| MagnetarIntelligence instability | MEDIUM | MEDIUM | Extensive testing, incremental integration, fallback mode |
| SDK adoption failure | MEDIUM | MEDIUM | Reference implementations, great docs, partner pilot |

---

## SUMMARY: APOLLO-LEVEL EXECUTION

This roadmap transforms ElohimOS from a single-user app to a **mission-critical, multi-user, AI-powered platform** with **field partner ecosystem**.

**Key Principles:**
1. **Separation of Concerns** - Each phase builds on stable foundation
2. **Incremental Validation** - Test before proceeding (like Apollo missions)
3. **Interface Stability** - Proven interfaces (like Excel in JSON pipeline)
4. **Quick Wins First** - Fix critical bugs immediately
5. **Systems of Systems** - Core → Intelligence → SDK

**Timeline:**
- **Phase 0:** 1-2 days (critical fixes)
- **Phase 1:** 3 weeks (user isolation + admin tools)
- **Phase 2:** 6 weeks (RBAC system)
- **Phase 3:** 6 weeks (MagnetarIntelligence)
- **Phase 4:** 6 weeks (MagnetarSDK)

**Total:** ~22 weeks (5.5 months) to production-ready platform with AI assistant and SDK

**Mission:** Build indestructible core → Enable field partners → Change the world

**Biblical Foundation:** *"Pressed but not crushed, perplexed but not in despair"* (2 Corinthians 4:8-9)

**Engineering Foundation:** Apollo Program rigor applied to modern AI platform

---

# Part 12: Codebase Alignment & Quick Fixes

## Status: Phase 0 Complete ✅ → Phase 0.5 Cleanup

**Last Validated:** 2025-11-01 (codex scan)

### ✅ Confirmed Aligned with Roadmap

1. **Roles/God Rights** - Fully implemented and consistent
   - Location: `apps/backend/api/auth_middleware.py`
   - Hardcoded founder account with env overrides
   - JWT tokens include role field
   - Documentation: `docs/dev/GOD_RIGHTS_LOGIN.md`

2. **Phase 1 User Isolation** - Chat routes complete with tests
   - Location: `apps/backend/api/chat_service.py:408`
   - Auth enforcement ✅
   - Per-user scoping ✅
   - Test coverage: `apps/backend/api/test_user_isolation.py`

3. **Saved Queries/Settings** - Already implemented
   - Backend: `apps/backend/api/main.py:1480`
   - Frontend: `apps/frontend/src/lib/settingsApi.ts`

4. **Audit Logging** - Exists and ready to wire
   - Location: `apps/backend/api/audit_logger.py`
   - Status: Implemented but not yet wired to all God Rights actions

### 🔧 Quick Fixes Needed (Phase 0.5 - 1 Day)

#### 1. API Prefix Inconsistency ⚠️
**Issue:** Duplicate auth endpoints with different prefixes
- `auth_routes.py` uses `/api/v1/auth/*` (correct, includes logout)
- `main.py` has duplicate endpoints at `/api/auth/*` (remove these)

**Fix:**
```python
# Remove from main.py (lines 567, 591, 634):
# @app.get("/api/auth/setup-needed")
# @app.post("/api/auth/register")
# @app.post("/api/auth/login")

# Keep only auth_routes.py endpoints at /api/v1/auth/*
```

**Files to update:**
- `apps/backend/api/main.py` - Remove duplicate endpoints
- `apps/frontend/src/lib/api.ts` - Update to use `/api/v1/auth/*`
- `apps/frontend/src/components/Login.tsx` - Update API calls

**Priority:** P1 (prevents API confusion)

#### 2. Wire Audit Logging to God Rights Actions 🔍
**Issue:** Audit logger exists but not connected to admin endpoints

**Fix:**
```python
# In admin_service.py, add:
from audit_logger import log_admin_action

@router.get("/users/{target_user_id}/chats")
async def get_user_chats(...):
    log_admin_action(
        admin_user=current_user["username"],
        action="view_user_chats",
        target_user=target_user_id,
        ip_address=request.client.host
    )
    # ... existing code
```

**Files to update:**
- `apps/backend/api/admin_service.py` - Add logging to all endpoints
- `apps/backend/api/auth_middleware.py` - Log God Rights logins

**Priority:** P1 (compliance requirement)

#### 3. Vault Query Consistency Audit 🔐
**Issue:** Ensure ALL vault DB queries filter by user_id

**Action:** Audit `apps/backend/api/vault_service.py:2739` and verify:
- ✅ All SELECT queries include `WHERE user_id = ?`
- ✅ All UPDATE queries include `WHERE user_id = ?`
- ✅ All DELETE queries include `WHERE user_id = ?`
- ✅ God Rights bypass only via explicit admin endpoints (not regular vault API)

**Priority:** P0 (security critical)

#### 4. Database Consolidation Documentation 📚
**Issue:** Doc references multiple DBs but code centralizes via `config_paths.py`

**Current Reality:**
- `apps/backend/api/config_paths.py` - Centralized path management
- `apps/backend/api/elohimos_memory.py` - Unified memory interface
- Actual DBs: `elohimos_app.db`, `chat_memory.db`, `workflows.db`, etc.

**Fix:** Update Part 7 "Interface Specifications" to reflect actual DB layout:
```
Database Layer:
├── elohimos_app.db (users, sessions, auth)
├── chat_memory.db (chat history, summaries)
├── workflows.db (workflow state)
├── vault/ (encrypted documents)
└── Managed via: config_paths.py + elohimos_memory.py
```

**Priority:** P2 (documentation accuracy)

### 🎯 Phase 0.5 Checklist (Complete before Phase 1A)

- [ ] Remove duplicate auth endpoints from main.py
- [ ] Update frontend to use /api/v1/auth/* consistently
- [ ] Wire audit logging to all admin_service.py endpoints
- [ ] Add audit log for God Rights login events
- [ ] Audit vault_service.py for consistent user_id filtering
- [ ] Update DB consolidation section in Part 7
- [ ] Test all auth flows with unified prefix
- [ ] Verify audit logs capture all God Rights actions

**Estimated Time:** 1 day
**Dependencies:** None (can run in parallel with other work)
**Go/No-Go:** All items must pass before Phase 1A begins

---

**Copyright (c) 2025 MagnetarAI, LLC**
**Built with conviction for mission-critical field operations.**
**"Like a magnetar - rare, powerful, indestructible."**

