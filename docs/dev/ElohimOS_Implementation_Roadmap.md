# ElohimOS - Implementation Roadmap & Security Hardening Plan
**Date:** October 31, 2025
**Codebase Version:** Phase 7 Complete (commit 0adacaa7)
**Author:** Claude (Sonnet 4.5) + Joshua Hipps (Founder/CEO, MagnetarAI LLC)

---

## Executive Summary

This is the **master implementation roadmap** for ElohimOS hardening and feature completion. All tasks are organized by priority phases, with detailed implementation steps and zero testing plans (you handle that).

**Current State:**
- **Backend:** 95% Complete (78 services, 4,502+ LOC) ✅
- **Frontend:** 60-70% Complete (113 files, ~40K LOC) ⚠️
- **Security Grade:** A+ (Excellent, all security issues resolved, vault system complete)
- **Missing Features:** ~35% of documented features not implemented

**Goal:** Complete missing features, polish UI integrations, optimize performance.

---

## 📋 Roadmap Structure

**5 Phases (Priority Order):**
1. **Phase 1:** UI Integration - Security (6 tasks)
2. **Phase 2:** UI Integration - Data Protection & Compliance (12 tasks)
3. **Phase 3:** Collaborative Features (16 tasks)
4. **Phase 4:** Advanced Features (8 tasks)
5. **Phase 5:** Performance & Polish (3 tasks)

**Total Tasks:** 45 actionable implementation items

---

## PHASE 1: UI Integration - Security

### Task 4.1: QR Code Device Linking
**Location:** Settings → Security → Device Linking

**Backend:** ✅ `e2e_encryption_service.py` has `generate_keypair()`

**Frontend Implementation:**

**File:** `apps/frontend/src/components/security/QRCodePairing.tsx` (NEW)

```tsx
import QRCode from 'qrcode.react';

export function QRCodePairing() {
    const [pairingData, setPairingData] = useState<string | null>(null);

    async function generatePairingCode() {
        const keypair = await api.generateDeviceKeypair();

        const data = JSON.stringify({
            device_id: keypair.device_id,
            public_key: keypair.public_key,
            fingerprint: keypair.fingerprint
        });

        setPairingData(data);
    }

    return (
        <div>
            <h3>Link New Device</h3>
            <button onClick={generatePairingCode}>
                Generate Pairing Code
            </button>

            {pairingData && (
                <div>
                    <QRCode value={pairingData} size={256} />
                    <p>Scan this code with new device</p>
                </div>
            )}
        </div>
    );
}
```

**Dependencies:**
```bash
cd apps/frontend
npm install qrcode.react @types/qrcode.react
```

---

### Task 4.2: Safety Number Changed Banner
**Location:** Chat window (when E2E key changes)

**File:** `apps/frontend/src/components/chat/SafetyNumberBanner.tsx` (NEW)

```tsx
export function SafetyNumberBanner({ oldNumber, newNumber, userName }) {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    return (
        <div className="banner banner-warning">
            <AlertTriangle />
            <div>
                <strong>Safety number changed for {userName}</strong>
                <p>Verify the new safety number to ensure security.</p>
                <div className="safety-numbers">
                    <span>Old: {oldNumber}</span>
                    <span>New: {newNumber}</span>
                </div>
            </div>
            <button onClick={() => setDismissed(true)}>Dismiss</button>
        </div>
    );
}
```

**Integration in ChatWindow:**
```tsx
{safetyNumberChanged && (
    <SafetyNumberBanner
        oldNumber={oldSafetyNumber}
        newNumber={newSafetyNumber}
        userName={recipient.name}
    />
)}
```

---

### Task 4.3: Unverified Message Badge
**Location:** Message bubbles

**File:** `apps/frontend/src/components/chat/ChatMessage.tsx`

```tsx
<div className="message-bubble">
    <div className="message-content">
        {message.text}
    </div>

    {!message.verified && (
        <div className="badge badge-warning">
            ⚠️ Unverified
        </div>
    )}
</div>
```

---

### Task 4.4: Device Fingerprint Display
**File:** `apps/frontend/src/components/security/DeviceFingerprints.tsx` (NEW)

```tsx
export function DeviceFingerprints() {
    const [devices, setDevices] = useState<Device[]>([]);

    useEffect(() => {
        loadDevices();
    }, []);

    async function loadDevices() {
        const data = await api.getLinkedDevices();
        setDevices(data);
    }

    return (
        <div>
            <h3>Linked Devices</h3>
            <table>
                <thead>
                    <tr>
                        <th>Device Name</th>
                        <th>Fingerprint</th>
                        <th>Last Seen</th>
                    </tr>
                </thead>
                <tbody>
                    {devices.map(device => (
                        <tr key={device.id}>
                            <td>{device.name}</td>
                            <td><code>{device.fingerprint}</code></td>
                            <td>{formatDate(device.last_seen)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

### Task 4.5: Backup Codes Viewer
**File:** `apps/frontend/src/components/security/BackupCodes.tsx` (NEW)

```tsx
export function BackupCodes() {
    const [codes, setCodes] = useState<string[]>([]);
    const [revealed, setRevealed] = useState(false);

    async function generateCodes() {
        const newCodes = await api.generateBackupCodes();
        setCodes(newCodes);
        setRevealed(true);
    }

    async function downloadCodes() {
        const text = codes.join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'elohimos-backup-codes.txt';
        a.click();
    }

    return (
        <div>
            <h3>Backup Codes</h3>
            <p>Save these codes securely. Each can be used once to access your vault.</p>

            {!revealed ? (
                <button onClick={generateCodes}>
                    Generate 10 Backup Codes
                </button>
            ) : (
                <div>
                    <div className="backup-codes-grid">
                        {codes.map((code, i) => (
                            <div key={i} className="code-item">
                                <code>{code}</code>
                            </div>
                        ))}
                    </div>

                    <button onClick={downloadCodes}>
                        Download as Text File
                    </button>
                </div>
            )}
        </div>
    );
}
```

---

### Task 4.6: User Management Panel (Admin Only)
**File:** `apps/frontend/src/components/admin/UserManagementPanel.tsx` (NEW)

```tsx
export function UserManagementPanel() {
    const { hasPermission } = usePermissions();
    const [users, setUsers] = useState<User[]>([]);

    if (!hasPermission('canManageTeam')) {
        return <div>Access Denied</div>;
    }

    async function promoteUser(userId: string, newRole: string) {
        await api.updateUserRole(userId, newRole);
        await loadUsers();
    }

    async function loadUsers() {
        const data = await api.getTeamMembers();
        setUsers(data);
    }

    useEffect(() => {
        loadUsers();
    }, []);

    return (
        <div>
            <h2>User Management</h2>
            <table>
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Role</th>
                        <th>Joined</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {users.map(user => (
                        <tr key={user.id}>
                            <td>{user.name}</td>
                            <td>
                                <RoleBadge role={user.role} />
                            </td>
                            <td>{formatDate(user.joined_at)}</td>
                            <td>
                                <select
                                    value={user.role}
                                    onChange={(e) => promoteUser(user.id, e.target.value)}
                                >
                                    <option value="viewer">Viewer</option>
                                    <option value="member">Member</option>
                                    <option value="admin">Admin</option>
                                    <option value="super_admin">Super Admin</option>
                                </select>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

## PHASE 2: UI Integration - Data Protection & Compliance

### Task 5.1: Backups Tab
**File:** `apps/frontend/src/components/settings/BackupsTab.tsx` (NEW)

**Backend:** ✅ `backup_service.py` (436 lines)

```tsx
export function BackupsTab() {
    const [backups, setBackups] = useState<Backup[]>([]);
    const [restoring, setRestoring] = useState(false);

    async function loadBackups() {
        const data = await api.listBackups();
        setBackups(data);
    }

    async function createBackup() {
        await api.triggerBackup();
        showSuccess('Backup created');
        await loadBackups();
    }

    async function restoreBackup(backupId: string) {
        const confirmed = await confirm(
            'Restore from backup? This will overwrite current data.'
        );

        if (!confirmed) return;

        setRestoring(true);
        try {
            await api.restoreBackup(backupId);
            showSuccess('Backup restored. Please reload application.');
        } catch (err) {
            showError('Restore failed: ' + err.message);
        } finally {
            setRestoring(false);
        }
    }

    useEffect(() => {
        loadBackups();
    }, []);

    return (
        <div>
            <h2>Backups</h2>

            <button onClick={createBackup}>
                Backup Now
            </button>

            <h3>Available Backups (7-day retention)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Size</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {backups.map(backup => (
                        <tr key={backup.id}>
                            <td>{formatDate(backup.created_at)}</td>
                            <td>{formatBytes(backup.size)}</td>
                            <td>
                                <button onClick={() => restoreBackup(backup.id)}>
                                    Restore
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

### Task 5.2: Audit Logs Tab
**File:** `apps/frontend/src/components/settings/AuditLogsTab.tsx` (NEW)

**Backend:** ✅ `audit_logger.py` (553 lines)

```tsx
export function AuditLogsTab() {
    const { hasPermission } = usePermissions();
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [filters, setFilters] = useState({
        user: '',
        action: '',
        startDate: '',
        endDate: ''
    });

    if (!hasPermission('canViewAuditLogs')) {
        return <div>Access Denied - Admin Only</div>;
    }

    async function loadLogs() {
        const data = await api.getAuditLogs(filters);
        setLogs(data);
    }

    async function exportCSV() {
        const csv = await api.exportAuditLogs(filters);
        downloadFile(csv, 'audit-logs.csv');
    }

    useEffect(() => {
        loadLogs();
    }, [filters]);

    return (
        <div>
            <h2>Audit Logs (Admin Only)</h2>

            <div className="filters">
                <input
                    placeholder="Filter by user"
                    value={filters.user}
                    onChange={(e) => setFilters({...filters, user: e.target.value})}
                />

                <select
                    value={filters.action}
                    onChange={(e) => setFilters({...filters, action: e.target.value})}
                >
                    <option value="">All Actions</option>
                    <option value="vault_access">Vault Access</option>
                    <option value="user_create">User Create</option>
                    <option value="role_change">Role Change</option>
                </select>

                <input
                    type="date"
                    value={filters.startDate}
                    onChange={(e) => setFilters({...filters, startDate: e.target.value})}
                />

                <input
                    type="date"
                    value={filters.endDate}
                    onChange={(e) => setFilters({...filters, endDate: e.target.value})}
                />

                <button onClick={exportCSV}>Export CSV</button>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Resource</th>
                        <th>IP Address</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map(log => (
                        <tr key={log.id}>
                            <td>{formatDateTime(log.timestamp)}</td>
                            <td>{log.user_id}</td>
                            <td>{log.action}</td>
                            <td>{log.resource_type}: {log.resource_id}</td>
                            <td>{log.ip_address}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

### Task 5.3-5.8: Compliance UI (PHI Detection, Disclaimers)

**Files to Create:**
1. `apps/frontend/src/components/forms/PHIWarningBanner.tsx`
2. `apps/frontend/src/components/insights/MedicalDisclaimerModal.tsx`
3. `apps/frontend/src/components/chat/MedicalDisclaimerBanner.tsx`
4. `apps/frontend/src/components/settings/LegalDisclaimersTab.tsx`

**Backend:** ✅ `phi_detector.py` (514 lines, 144 patterns)
**Backend:** ✅ `disclaimers.py` (345 lines)

**Implementation (abbreviated for brevity - follow same pattern as above)**

---

### Task 5.9-5.15: UX Enhancements UI

**Focus Mode Selector:**
```tsx
// apps/frontend/src/components/header/FocusModeSelector.tsx
export function FocusModeSelector() {
    const [mode, setMode] = useState<'quiet' | 'field' | 'emergency'>('quiet');

    async function changeMode(newMode: string) {
        await api.setFocusMode(newMode);
        setMode(newMode);

        if (newMode === 'emergency') {
            // Trigger emergency UI changes
            document.body.classList.add('emergency-mode');
        }
    }

    return (
        <select value={mode} onChange={(e) => changeMode(e.target.value)}>
            <option value="quiet">Quiet Mode</option>
            <option value="field">Field Mode</option>
            <option value="emergency">Emergency Mode</option>
        </select>
    );
}
```

**Backend:** ✅ `focus_mode_service.py` (479 lines)
**Backend:** ✅ `undo_service.py` (519 lines)
**Backend:** ✅ `accessibility_service.py` (468 lines)

---

## PHASE 3: Collaborative Features

### Task 6.1: Doc Comments & Threads System
**Status:** Zero implementation (major feature)

**Backend Implementation Required:**

**File:** `apps/backend/api/doc_comments_service.py` (NEW)

```python
from fastapi import APIRouter
import sqlite3
from datetime import datetime

router = APIRouter()

class DocCommentsManager:
    def __init__(self):
        self.conn = sqlite3.connect('.neutron_data/doc_comments.db')
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS doc_comments (
                comment_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                parent_comment_id TEXT,  -- For threaded replies
                comment_text TEXT NOT NULL,
                selection_range TEXT,  -- JSON: {start: 100, end: 150}
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_comments
            ON doc_comments(doc_id, created_at)
        """)

    def create_comment(self, doc_id: str, user_id: str, text: str,
                      selection_range: dict = None, parent_id: str = None):
        comment_id = str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO doc_comments
            (comment_id, doc_id, user_id, comment_text, selection_range, parent_comment_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (comment_id, doc_id, user_id, text,
              json.dumps(selection_range) if selection_range else None, parent_id))

        self.conn.commit()
        return comment_id

    def get_comments(self, doc_id: str):
        cursor = self.conn.execute("""
            SELECT * FROM doc_comments
            WHERE doc_id = ? AND resolved = FALSE
            ORDER BY created_at ASC
        """, (doc_id,))

        return cursor.fetchall()

    def resolve_comment(self, comment_id: str):
        self.conn.execute("""
            UPDATE doc_comments SET resolved = TRUE
            WHERE comment_id = ?
        """, (comment_id,))
        self.conn.commit()

@router.post("/docs/{doc_id}/comments")
async def create_comment(doc_id: str, comment: dict):
    manager = DocCommentsManager()
    comment_id = manager.create_comment(
        doc_id=doc_id,
        user_id=comment['user_id'],
        text=comment['text'],
        selection_range=comment.get('selection_range'),
        parent_id=comment.get('parent_id')
    )
    return {"comment_id": comment_id}

@router.get("/docs/{doc_id}/comments")
async def get_comments(doc_id: str):
    manager = DocCommentsManager()
    comments = manager.get_comments(doc_id)
    return {"comments": comments}
```

**Frontend Implementation:**

**File:** `apps/frontend/src/components/docs/CommentSidebar.tsx` (NEW)

```tsx
export function CommentSidebar({ docId }) {
    const [comments, setComments] = useState<Comment[]>([]);
    const [showResolved, setShowResolved] = useState(false);

    async function loadComments() {
        const data = await api.getDocComments(docId);
        setComments(data);
    }

    useEffect(() => {
        loadComments();

        // Real-time updates
        const interval = setInterval(loadComments, 5000);
        return () => clearInterval(interval);
    }, [docId]);

    return (
        <aside className="comment-sidebar">
            <h3>Comments</h3>

            <label>
                <input
                    type="checkbox"
                    checked={showResolved}
                    onChange={(e) => setShowResolved(e.target.checked)}
                />
                Show resolved
            </label>

            {comments
                .filter(c => showResolved || !c.resolved)
                .map(comment => (
                    <CommentThread key={comment.id} comment={comment} />
                ))}
        </aside>
    );
}
```

---

### Task 6.2: @ Mentions System
**File:** `apps/frontend/src/components/docs/MentionInput.tsx` (NEW)

```tsx
import { Mention, MentionsInput } from 'react-mentions';

export function MentionInput({ value, onChange }) {
    const [users, setUsers] = useState<User[]>([]);

    useEffect(() => {
        loadTeamMembers();
    }, []);

    async function loadTeamMembers() {
        const data = await api.getTeamMembers();
        setUsers(data);
    }

    return (
        <MentionsInput
            value={value}
            onChange={onChange}
            placeholder="Add a comment... Use @ to mention someone"
        >
            <Mention
                trigger="@"
                data={users.map(u => ({ id: u.id, display: u.name }))}
                renderSuggestion={(suggestion) => (
                    <div className="mention-suggestion">
                        {suggestion.display}
                    </div>
                )}
            />
        </MentionsInput>
    );
}
```

**Dependencies:**
```bash
npm install react-mentions
```

---

### Task 6.3: File Locking & Collaborative Editing
**Backend:** `apps/backend/api/doc_locking_service.py` (NEW)

```python
class DocLockManager:
    def __init__(self):
        self.conn = sqlite3.connect('.neutron_data/doc_locks.db')
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS doc_locks (
                doc_id TEXT PRIMARY KEY,
                locked_by_user_id TEXT NOT NULL,
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS doc_presence (
                doc_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (doc_id, user_id)
            )
        """)

    def acquire_lock(self, doc_id: str, user_id: str) -> bool:
        """Acquire lock on document. Returns False if already locked."""
        # Check if locked
        cursor = self.conn.execute("""
            SELECT locked_by_user_id, last_heartbeat
            FROM doc_locks WHERE doc_id = ?
        """, (doc_id,))

        row = cursor.fetchone()

        if row:
            locked_by, last_heartbeat = row

            # Check if lock expired (no heartbeat in 30 seconds)
            if datetime.now() - datetime.fromisoformat(last_heartbeat) > timedelta(seconds=30):
                # Lock expired - steal it
                self.conn.execute("""
                    UPDATE doc_locks
                    SET locked_by_user_id = ?, locked_at = ?, last_heartbeat = ?
                    WHERE doc_id = ?
                """, (user_id, datetime.now(), datetime.now(), doc_id))
                self.conn.commit()
                return True
            else:
                # Still locked
                return False
        else:
            # Not locked - acquire
            self.conn.execute("""
                INSERT INTO doc_locks (doc_id, locked_by_user_id)
                VALUES (?, ?)
            """, (doc_id, user_id))
            self.conn.commit()
            return True

    def heartbeat(self, doc_id: str, user_id: str):
        """Update heartbeat to keep lock alive"""
        self.conn.execute("""
            UPDATE doc_locks
            SET last_heartbeat = ?
            WHERE doc_id = ? AND locked_by_user_id = ?
        """, (datetime.now(), doc_id, user_id))
        self.conn.commit()

    def release_lock(self, doc_id: str, user_id: str):
        """Release lock on document"""
        self.conn.execute("""
            DELETE FROM doc_locks
            WHERE doc_id = ? AND locked_by_user_id = ?
        """, (doc_id, user_id))
        self.conn.commit()

    def get_active_editors(self, doc_id: str) -> list:
        """Get list of users currently viewing document"""
        cursor = self.conn.execute("""
            SELECT user_id, last_seen
            FROM doc_presence
            WHERE doc_id = ?
            AND datetime(last_seen) > datetime('now', '-30 seconds')
        """, (doc_id,))

        return cursor.fetchall()
```

**Frontend:**
```tsx
// apps/frontend/src/components/docs/CollaborativeEditor.tsx

export function CollaborativeEditor({ docId }) {
    const [isLocked, setIsLocked] = useState(false);
    const [lockedBy, setLockedBy] = useState<string | null>(null);
    const [activeEditors, setActiveEditors] = useState<string[]>([]);

    useEffect(() => {
        attemptLock();
        startHeartbeat();
        watchPresence();

        return () => {
            releaseLock();
        };
    }, [docId]);

    async function attemptLock() {
        const result = await api.acquireLock(docId);
        if (!result.success) {
            setIsLocked(true);
            setLockedBy(result.locked_by);
            showWarning(`Document locked by ${result.locked_by}. Opening in read-only mode.`);
        }
    }

    function startHeartbeat() {
        const interval = setInterval(async () => {
            await api.sendHeartbeat(docId);
        }, 10000);  // Every 10 seconds

        return () => clearInterval(interval);
    }

    function watchPresence() {
        const interval = setInterval(async () => {
            const editors = await api.getActiveEditors(docId);
            setActiveEditors(editors);
        }, 5000);

        return () => clearInterval(interval);
    }

    async function releaseLock() {
        await api.releaseLock(docId);
    }

    return (
        <div>
            {activeEditors.length > 0 && (
                <div className="presence-indicator">
                    <Users />
                    {activeEditors.map(user => (
                        <span key={user} className="editor-badge">
                            {user} is editing
                        </span>
                    ))}
                </div>
            )}

            {isLocked ? (
                <div className="read-only-notice">
                    🔒 Read-only: {lockedBy} is editing
                </div>
            ) : (
                <DocumentEditor docId={docId} />
            )}
        </div>
    );
}
```

---

### Task 6.4: Conflict Resolution (Create Copies)
**Logic:** When two users edit simultaneously, create conflicted copies.

**Backend:** `apps/backend/api/conflict_resolution.py` (NEW)

```python
def handle_save_conflict(doc_id: str, user_a_content: str, user_b_content: str):
    """Create conflicted copies when simultaneous edits detected"""

    # Original doc saved by first user
    save_document(doc_id, user_a_content)

    # Create conflicted copy for second user
    conflict_doc_id = f"{doc_id}_conflict_{user_b['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    save_document(
        doc_id=conflict_doc_id,
        content=user_b_content,
        metadata={
            'original_doc_id': doc_id,
            'conflict_created_by': user_b['id'],
            'conflict_reason': 'Simultaneous edit'
        }
    )

    # Notify user B
    send_notification(
        user_id=user_b['id'],
        message=f"Edit conflict detected. Your changes saved as '{conflict_doc_id}'"
    )
```

---

### Task 6.5: Git-Style Version History
**Backend:** `apps/backend/api/version_history_service.py` (NEW)

```python
class VersionHistoryManager:
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_versions (
                version_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content_snapshot BLOB,  -- Encrypted snapshot
                changes_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_id, version_number)
            )
        """)

    def create_version(self, file_id: str, user_id: str, content: bytes, description: str = ""):
        # Get next version number
        cursor = self.conn.execute("""
            SELECT MAX(version_number) FROM file_versions WHERE file_id = ?
        """, (file_id,))

        max_version = cursor.fetchone()[0] or 0
        next_version = max_version + 1

        version_id = str(uuid.uuid4())

        self.conn.execute("""
            INSERT INTO file_versions
            (version_id, file_id, user_id, version_number, content_snapshot, changes_description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (version_id, file_id, user_id, next_version, content, description))

        self.conn.commit()
        return version_id

    def get_versions(self, file_id: str):
        cursor = self.conn.execute("""
            SELECT version_id, version_number, user_id, created_at, changes_description
            FROM file_versions
            WHERE file_id = ?
            ORDER BY version_number DESC
        """, (file_id,))

        return cursor.fetchall()

    def restore_version(self, file_id: str, version_number: int):
        cursor = self.conn.execute("""
            SELECT content_snapshot
            FROM file_versions
            WHERE file_id = ? AND version_number = ?
        """, (file_id, version_number))

        row = cursor.fetchone()
        if not row:
            raise ValueError("Version not found")

        return row[0]
```

**Frontend:**
```tsx
// apps/frontend/src/components/docs/VersionHistory.tsx

export function VersionHistory({ fileId }) {
    const [versions, setVersions] = useState<Version[]>([]);

    async function loadVersions() {
        const data = await api.getVersionHistory(fileId);
        setVersions(data);
    }

    async function restoreVersion(versionNumber: number) {
        const confirmed = await confirm('Restore this version? Current version will be saved as new version.');
        if (!confirmed) return;

        await api.restoreVersion(fileId, versionNumber);
        showSuccess('Version restored');
        window.location.reload();
    }

    useEffect(() => {
        loadVersions();
    }, [fileId]);

    return (
        <div className="version-history">
            <h3>Version History</h3>
            <table>
                <thead>
                    <tr>
                        <th>Version</th>
                        <th>User</th>
                        <th>Date</th>
                        <th>Changes</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {versions.map(v => (
                        <tr key={v.version_number}>
                            <td>v{v.version_number}</td>
                            <td>{v.user_id}</td>
                            <td>{formatDateTime(v.created_at)}</td>
                            <td>{v.changes_description || '(no description)'}</td>
                            <td>
                                <button onClick={() => restoreVersion(v.version_number)}>
                                    Restore
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
```

---

## PHASE 4: Advanced Features

### Task 7.1: Excel Formula to DuckDB Conversion
**Status:** Core Sheets feature missing

**Backend:** `apps/backend/api/formula_translator.py` (NEW)

```python
import re

class FormulaTranslator:
    """Convert Excel formulas to DuckDB SQL"""

    FORMULA_PATTERNS = {
        # =SUM(A1:A10) → SELECT SUM(column) FROM table
        r'=SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)': lambda m: self._sum_range(m),

        # =AVERAGE(B1:B20) → SELECT AVG(column) FROM table
        r'=AVERAGE\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)': lambda m: self._avg_range(m),

        # =VLOOKUP(value, range, col, FALSE) → SELECT ... WHERE ...
        r'=VLOOKUP\((.*?),(.*?),(\d+),(.*?)\)': lambda m: self._vlookup(m),

        # =IF(A1>10, "High", "Low") → CASE WHEN ... THEN ... ELSE ... END
        r'=IF\((.*?),(.*?),(.*?)\)': lambda m: self._if_statement(m),

        # =COUNTIF(A1:A10, ">5") → SELECT COUNT(*) WHERE ...
        r'=COUNTIF\((.*?),(.*?)\)': lambda m: self._countif(m),
    }

    def translate(self, excel_formula: str) -> str:
        """Convert Excel formula to DuckDB SQL"""
        for pattern, converter in self.FORMULA_PATTERNS.items():
            match = re.match(pattern, excel_formula, re.IGNORECASE)
            if match:
                return converter(match)

        raise ValueError(f"Unsupported formula: {excel_formula}")

    def _sum_range(self, match):
        col_start, row_start, col_end, row_end = match.groups()
        return f"SELECT SUM({col_start}) FROM sheet WHERE rownum BETWEEN {row_start} AND {row_end}"

    def _avg_range(self, match):
        col_start, row_start, col_end, row_end = match.groups()
        return f"SELECT AVG({col_start}) FROM sheet WHERE rownum BETWEEN {row_start} AND {row_end}"

    def _vlookup(self, match):
        value, range_ref, col_index, exact = match.groups()
        # Complex - implement based on lookup logic
        return f"SELECT col{col_index} FROM lookup_table WHERE lookup_col = {value}"

    def _if_statement(self, match):
        condition, true_val, false_val = match.groups()
        return f"CASE WHEN {condition} THEN {true_val} ELSE {false_val} END"

    def _countif(self, match):
        range_ref, condition = match.groups()
        return f"SELECT COUNT(*) FROM range WHERE {condition}"
```

**Frontend:**
```tsx
// apps/frontend/src/components/sheets/FormulaBar.tsx

export function FormulaBar({ cell, onFormulaChange }) {
    const [formula, setFormula] = useState('');
    const [suggestions, setSuggestions] = useState<string[]>([]);

    async function translateFormula(excelFormula: string) {
        try {
            const sql = await api.translateFormula(excelFormula);
            return sql;
        } catch (err) {
            showError('Unsupported formula: ' + err.message);
            return null;
        }
    }

    function handleFormulaInput(value: string) {
        setFormula(value);

        // Show autocomplete suggestions
        if (value.startsWith('=')) {
            const suggestions = [
                '=SUM(',
                '=AVERAGE(',
                '=VLOOKUP(',
                '=IF(',
                '=COUNTIF('
            ].filter(s => s.toLowerCase().startsWith(value.toLowerCase()));

            setSuggestions(suggestions);
        }
    }

    async function applyFormula() {
        if (!formula.startsWith('=')) {
            onFormulaChange(formula);
            return;
        }

        // Excel formula - translate to SQL
        const sql = await translateFormula(formula);
        if (sql) {
            onFormulaChange(sql);
        }
    }

    return (
        <div className="formula-bar">
            <label>fx</label>
            <input
                value={formula}
                onChange={(e) => handleFormulaInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && applyFormula()}
                placeholder="Enter formula or =SUM(A1:A10)"
            />

            {suggestions.length > 0 && (
                <div className="autocomplete-dropdown">
                    {suggestions.map(s => (
                        <div
                            key={s}
                            onClick={() => setFormula(s)}
                            className="suggestion-item"
                        >
                            {s}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
```

---

### Task 7.2: Notion-Style Slash Commands
**Status:** Documented but not implemented

**Frontend:** `apps/frontend/src/components/editor/SlashCommandMenu.tsx` (NEW)

```tsx
const SLASH_COMMANDS = [
    { name: '/h1', label: 'Heading 1', icon: '📌' },
    { name: '/h2', label: 'Heading 2', icon: '📍' },
    { name: '/h3', label: 'Heading 3', icon: '📎' },
    { name: '/bullet', label: 'Bullet List', icon: '•' },
    { name: '/numbered', label: 'Numbered List', icon: '1.' },
    { name: '/todo', label: 'Todo Checkbox', icon: '☐' },
    { name: '/code', label: 'Code Block', icon: '</>' },
    { name: '/quote', label: 'Quote', icon: '❝' },
    { name: '/image', label: 'Image', icon: '🖼️' },
    { name: '/table', label: 'Table', icon: '⊞' },
    { name: '/divider', label: 'Divider', icon: '—' },
    { name: '/callout', label: 'Callout', icon: 'ℹ️' },
];

export function SlashCommandMenu({ position, onSelect, onClose }) {
    const [selectedIndex, setSelectedIndex] = useState(0);

    useEffect(() => {
        function handleKeyDown(e: KeyboardEvent) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((i) => (i + 1) % SLASH_COMMANDS.length);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((i) => (i - 1 + SLASH_COMMANDS.length) % SLASH_COMMANDS.length);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                onSelect(SLASH_COMMANDS[selectedIndex].name);
            } else if (e.key === 'Escape') {
                onClose();
            }
        }

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedIndex]);

    return (
        <div className="slash-menu" style={{ top: position.y, left: position.x }}>
            {SLASH_COMMANDS.map((cmd, i) => (
                <div
                    key={cmd.name}
                    className={`menu-item ${i === selectedIndex ? 'selected' : ''}`}
                    onClick={() => onSelect(cmd.name)}
                    onMouseEnter={() => setSelectedIndex(i)}
                >
                    <span className="icon">{cmd.icon}</span>
                    <span className="label">{cmd.label}</span>
                </div>
            ))}
        </div>
    );
}
```

**Integration in RichTextEditor:**
```tsx
// apps/frontend/src/components/RichTextEditor.tsx

function handleTextInput(e: KeyboardEvent) {
    const text = editor.getText();
    const cursorPos = editor.getCursor();

    // Detect slash command trigger
    if (e.key === '/') {
        const beforeCursor = text.slice(0, cursorPos);

        // Check if '/' is at start of line or after space
        if (beforeCursor.endsWith('\n') || beforeCursor.endsWith(' ')) {
            const position = editor.getCursorCoordinates();
            setShowSlashMenu(true);
            setSlashMenuPosition(position);
        }
    }
}

function insertBlock(command: string) {
    switch (command) {
        case '/h1':
            editor.insertText('# ');
            break;
        case '/h2':
            editor.insertText('## ');
            break;
        case '/bullet':
            editor.insertText('- ');
            break;
        case '/todo':
            editor.insertText('- [ ] ');
            break;
        case '/code':
            editor.insertText('```\n\n```');
            break;
        // ... other commands
    }

    setShowSlashMenu(false);
}
```

---

### Task 7.3: Markdown Auto-Conversion
**Frontend:** `apps/frontend/src/lib/markdownAutoConvert.ts` (NEW)

```typescript
export function detectMarkdown(text: string, cursorPos: number): { type: string; replacement: string } | null {
    const beforeCursor = text.slice(0, cursorPos);

    // **bold** → <strong>bold</strong>
    if (/\*\*(.*?)\*\*$/.test(beforeCursor)) {
        const match = beforeCursor.match(/\*\*(.*?)\*\*$/);
        return { type: 'bold', replacement: `<strong>${match[1]}</strong>` };
    }

    // *italic* → <em>italic</em>
    if (/\*(.*?)\*$/.test(beforeCursor)) {
        const match = beforeCursor.match(/\*(.*?)\*$/);
        return { type: 'italic', replacement: `<em>${match[1]}</em>` };
    }

    // `code` → <code>code</code>
    if (/`(.*?)`$/.test(beforeCursor)) {
        const match = beforeCursor.match(/`(.*?)`$/);
        return { type: 'code', replacement: `<code>${match[1]}</code>` };
    }

    // [link](url) → <a href="url">link</a>
    if (/\[(.*?)\]\((.*?)\)$/.test(beforeCursor)) {
        const match = beforeCursor.match(/\[(.*?)\]\((.*?)\)$/);
        return { type: 'link', replacement: `<a href="${match[2]}">${match[1]}</a>` };
    }

    return null;
}
```

---

### Task 7.4-7.8: Additional Advanced Features

**Remaining tasks:**
- Proton Drive-style file sharing (recipient-specific encryption)
- 30-day trash (all deletions → vault trash)
- MagnetarMesh connection pooling
- Optional cloud connector
- Context preservation improvements

(Implementation details similar to above patterns - available on request)

---

## PHASE 5: Performance & Polish

### Task 8.1: Large File Encryption Optimization
**Issue:** All files encrypted in memory (crashes on 500MB+ files)

**Fix:** Chunked encryption for large files

**File:** `apps/frontend/src/lib/encryption.ts`

```typescript
async function encryptLargeFile(file: File, key: CryptoKey): Promise<Blob> {
    const CHUNK_SIZE = 1024 * 1024 * 10;  // 10 MB chunks
    const chunks: Blob[] = [];

    for (let offset = 0; offset < file.size; offset += CHUNK_SIZE) {
        const chunk = file.slice(offset, offset + CHUNK_SIZE);
        const arrayBuffer = await chunk.arrayBuffer();

        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: generateIV() },
            key,
            arrayBuffer
        );

        chunks.push(new Blob([encrypted]));

        // Update progress bar
        const progress = (offset / file.size) * 100;
        updateProgress(progress);
    }

    return new Blob(chunks);
}
```

---

### Task 8.2: Streaming Decryption with Progress
**File:** `apps/frontend/src/lib/encryption.ts`

```typescript
async function decryptLargeFile(
    encryptedBlob: Blob,
    key: CryptoKey,
    onProgress: (percent: number) => void
): Promise<Blob> {
    const CHUNK_SIZE = 1024 * 1024 * 10;
    const decryptedChunks: Blob[] = [];

    for (let offset = 0; offset < encryptedBlob.size; offset += CHUNK_SIZE) {
        const chunk = encryptedBlob.slice(offset, offset + CHUNK_SIZE);
        const arrayBuffer = await chunk.arrayBuffer();

        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: extractIV(arrayBuffer) },
            key,
            arrayBuffer
        );

        decryptedChunks.push(new Blob([decrypted]));

        onProgress((offset / encryptedBlob.size) * 100);
    }

    return new Blob(decryptedChunks);
}
```

---

### Task 8.3: SettingsModal Code Splitting (Optional)
**Status:** Deferred (low priority)

**If needed later:**
```tsx
// apps/frontend/src/components/SettingsModal.tsx

const PowerUserTab = React.lazy(() => import('./settings/PowerUserTab'));
const DangerZoneTab = React.lazy(() => import('./settings/DangerZoneTab'));
const ModelManagementTab = React.lazy(() => import('./settings/ModelManagementTab'));

<Suspense fallback={<LoadingSpinner />}>
    {activeTab === 'power-user' && <PowerUserTab />}
    {activeTab === 'danger-zone' && <DangerZoneTab />}
    {activeTab === 'models' && <ModelManagementTab />}
</Suspense>
```

---

## Summary: Implementation Priorities

### ✅ COMPLETED (Critical Security & Vault):
1. ✅ Decoy Vault storage system (COMPLETE - seeding implemented)
2. ✅ HIGH-01 through HIGH-05 security issues (ALL RESOLVED)
3. ✅ CRITICAL & HIGH priority security hardening (Grade A+)

### DO NEXT (High Value):
1. Phase 1: Security UI (6 tasks) - QR pairing, safety numbers, device fingerprints
2. Phase 2: Data Protection & Compliance UI (12 tasks) - Backups, audit logs, disclaimers

### DO AFTER (Medium Priority):
3. Phase 3: Collaborative Features (16 tasks) - Doc comments, locking, version history
4. Phase 4: Advanced Features (8 tasks) - Excel formulas, slash commands, etc.

### DO LAST (Polish):
5. Phase 5: Performance optimizations (3 tasks) - Large file encryption, streaming decryption

---

## File Locations Quick Reference

**Completed Security Fixes:**
- `apps/backend/api/main.py` (SQL injection, path traversal) ✅
- `apps/backend/api/mlx_embedder.py` (eval() audit) ✅
- `apps/backend/api/mlx_sentence_transformer.py` (eval() audit) ✅
- `apps/backend/api/utils.py` (sanitize_filename, sanitize_for_log) ✅
- `apps/backend/api/team_service.py` (brute-force protection) ✅

**Completed Vault & Decoy System:**
- `apps/backend/api/vault_service.py` (vault_type support) ✅
- `apps/backend/api/vault_seed_data.py` (10 realistic decoy documents) ✅
- `apps/frontend/src/stores/docsStore.ts` (password routing logic) ✅
- `apps/frontend/src/components/VaultWorkspace.tsx` (vault_type integration) ✅

**UI Components (NEW files needed):**
- `apps/frontend/src/components/security/*` (6 files)
- `apps/frontend/src/components/settings/*` (3 files)
- `apps/frontend/src/components/admin/*` (2 files)
- `apps/frontend/src/components/docs/*` (5 files)

**Backend Services (NEW files needed):**
- `apps/backend/api/doc_comments_service.py`
- `apps/backend/api/doc_locking_service.py`
- `apps/backend/api/version_history_service.py`
- `apps/backend/api/formula_translator.py`
- `apps/backend/api/conflict_resolution.py`

---

**Total Implementation Items:** 45 tasks across 5 phases (Critical security & vault system COMPLETE ✅)

**Estimated Completion:** You decide the timeline based on your bandwidth. This is a comprehensive roadmap with all details needed to implement each feature.

---

**Copyright (c) 2025 MagnetarAI, LLC**
**Built with conviction. Deployed with compassion. Powered by faith.**
