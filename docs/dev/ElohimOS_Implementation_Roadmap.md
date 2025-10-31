# ElohimOS - Implementation Roadmap & Security Hardening Plan
**Date:** October 31, 2025
**Codebase Version:** Phase 4 In Progress (commit 83482b78)
**Author:** Claude (Sonnet 4.5) + Joshua Hipps (Founder/CEO, MagnetarAI LLC)

---

## Executive Summary

This is the **master implementation roadmap** for ElohimOS hardening and feature completion. All tasks are organized by priority phases, with detailed implementation steps for remaining work.

**Current State:**
- **Backend:** 95% Complete (78 services, 4,502+ LOC) ✅
- **Frontend:** 85-90% Complete (142 files, ~48K LOC) ✅
- **Security Grade:** A+ (Excellent, all security issues resolved, vault system complete)
- **Phases 1-3 Complete:** Security UI, Data Protection, Collaborative Features ✅
- **Phase 4 In Progress:** 5/8 tasks complete (advanced features)

**Goal:** Complete remaining advanced features and critical performance optimizations.

---

## 📋 Roadmap Structure

**Remaining Work:**
- **Phase 4:** Advanced Features (3/8 tasks remaining) ⏳ **IN PROGRESS**
- **Phase 5:** Performance & Polish (3/3 tasks remaining) ⏳ **TODO**

**Total Tasks Remaining:** 6 actionable implementation items
**Overall Progress:** 33/39 tasks (85%) complete

---

## ⏳ REMAINING WORK

## PHASE 4: Advanced Features (Remaining Tasks)

### Task 4.6: MagnetarMesh Connection Pooling
**Status:** Not implemented
**Priority:** Low (Performance optimization)

**Description:** Implement connection pooling for MagnetarMesh P2P network to improve performance and reduce connection overhead.

**Backend:** `apps/backend/api/magnetar_mesh.py` (MODIFY)

**Implementation:**
```python
import asyncio
from typing import Dict, Optional
from collections import deque

class MagnetarMeshConnectionPool:
    """
    Connection pool for MagnetarMesh P2P connections

    Features:
    - Reuse idle connections
    - Maximum pool size limits
    - Connection health checks
    - Automatic cleanup of stale connections
    """

    def __init__(self, max_size: int = 50, idle_timeout: int = 300):
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self._pool: Dict[str, deque] = {}  # peer_id -> connection queue
        self._active: Dict[str, int] = {}  # peer_id -> active count

    async def acquire(self, peer_id: str) -> 'MeshConnection':
        """Get connection from pool or create new one"""
        if peer_id in self._pool and self._pool[peer_id]:
            conn = self._pool[peer_id].popleft()
            if await self._is_healthy(conn):
                self._active[peer_id] = self._active.get(peer_id, 0) + 1
                return conn

        # Create new connection
        conn = await self._create_connection(peer_id)
        self._active[peer_id] = self._active.get(peer_id, 0) + 1
        return conn

    async def release(self, peer_id: str, conn: 'MeshConnection'):
        """Return connection to pool"""
        self._active[peer_id] = max(0, self._active.get(peer_id, 1) - 1)

        if len(self._pool.get(peer_id, [])) < self.max_size:
            if peer_id not in self._pool:
                self._pool[peer_id] = deque()
            self._pool[peer_id].append(conn)
        else:
            await conn.close()

    async def _is_healthy(self, conn: 'MeshConnection') -> bool:
        """Check if connection is still healthy"""
        try:
            await asyncio.wait_for(conn.ping(), timeout=2.0)
            return True
        except:
            return False

    async def _create_connection(self, peer_id: str) -> 'MeshConnection':
        """Create new connection to peer"""
        # TODO: Implement actual connection logic
        pass
```

---

### Task 4.7: Optional Cloud Connector
**Status:** Not implemented
**Priority:** Low (Optional feature)

**Description:** Cloud sync capability for backup/sync across devices. Optional integration with cloud storage providers.

**Backend:** `apps/backend/api/cloud_connector.py` (NEW)

**Implementation:**
```python
from enum import Enum
from typing import Optional
import aiohttp

class CloudProvider(Enum):
    """Supported cloud providers"""
    NONE = "none"
    S3 = "s3"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"

class CloudConnector:
    """
    Optional cloud storage connector

    Features:
    - Multi-provider support
    - Encrypted backups only
    - Manual sync (no automatic upload)
    - User controls all data
    """

    def __init__(self, provider: CloudProvider = CloudProvider.NONE):
        self.provider = provider
        self.enabled = provider != CloudProvider.NONE

    async def upload_encrypted_backup(
        self,
        backup_blob: bytes,
        filename: str
    ) -> str:
        """
        Upload encrypted backup to cloud
        Returns: cloud file URL/ID
        """
        if not self.enabled:
            raise ValueError("Cloud connector not enabled")

        if self.provider == CloudProvider.S3:
            return await self._upload_s3(backup_blob, filename)
        elif self.provider == CloudProvider.GOOGLE_DRIVE:
            return await self._upload_google_drive(backup_blob, filename)
        # ... other providers

    async def download_encrypted_backup(self, file_id: str) -> bytes:
        """Download encrypted backup from cloud"""
        if not self.enabled:
            raise ValueError("Cloud connector not enabled")

        if self.provider == CloudProvider.S3:
            return await self._download_s3(file_id)
        # ... other providers

    async def _upload_s3(self, data: bytes, filename: str) -> str:
        """Upload to S3 (TODO: implement)"""
        pass

    async def _download_s3(self, file_id: str) -> bytes:
        """Download from S3 (TODO: implement)"""
        pass
```

**Frontend:** `apps/frontend/src/components/settings/CloudSyncTab.tsx` (NEW)

```tsx
export function CloudSyncTab() {
    const [provider, setProvider] = useState<CloudProvider>('none');
    const [isSyncing, setIsSyncing] = useState(false);

    return (
        <div>
            <h3>Cloud Backup (Optional)</h3>
            <p>Securely backup encrypted vault to cloud storage</p>

            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="none">Disabled (Local Only)</option>
                <option value="s3">Amazon S3</option>
                <option value="google_drive">Google Drive</option>
                <option value="dropbox">Dropbox</option>
            </select>

            <button onClick={handleManualBackup}>
                Manual Backup to Cloud
            </button>

            <div className="warning">
                ⚠️ Only encrypted data is uploaded. Decryption keys never leave your device.
            </div>
        </div>
    );
}
```

---

### Task 4.8: Context Preservation Improvements
**Status:** Not implemented
**Priority:** Low (AI enhancement)

**Description:** Improve context handling for better AI responses and conversation continuity.

**Implementation:**
```typescript
// apps/frontend/src/lib/contextManager.ts

interface ConversationContext {
    userId: string;
    conversationId: string;
    messageHistory: Message[];
    relevantDocuments: Document[];
    userPreferences: UserPreferences;
    sessionMetadata: SessionMetadata;
}

export class ContextManager {
    private maxContextTokens: number = 8000;

    /**
     * Build optimized context for AI queries
     */
    buildContext(conversation: ConversationContext): string {
        const parts: string[] = [];

        // User preferences
        if (conversation.userPreferences) {
            parts.push(this.formatPreferences(conversation.userPreferences));
        }

        // Recent message history (prioritize recent messages)
        const recentMessages = conversation.messageHistory.slice(-10);
        parts.push(this.formatMessages(recentMessages));

        // Relevant documents (use semantic search to find most relevant)
        const topDocs = this.rankRelevantDocuments(
            conversation.relevantDocuments,
            conversation.messageHistory
        );
        parts.push(this.formatDocuments(topDocs.slice(0, 3)));

        // Truncate to token limit
        return this.truncateToTokenLimit(parts.join('\n\n'), this.maxContextTokens);
    }

    private rankRelevantDocuments(docs: Document[], history: Message[]): Document[] {
        // TODO: Implement semantic ranking
        return docs;
    }

    private truncateToTokenLimit(text: string, maxTokens: number): string {
        // Rough estimation: 1 token ≈ 4 characters
        const maxChars = maxTokens * 4;
        if (text.length <= maxChars) return text;
        return text.slice(0, maxChars) + '\n[Context truncated]';
    }
}
```

---

## PHASE 5: Performance & Polish

### Task 5.1: Large File Encryption Optimization
**Status:** Not implemented
**Priority:** HIGH (Production blocker for large files)
**Issue:** All files encrypted in memory (crashes on 500MB+ files)

**Fix:** Chunked encryption for large files

**File:** `apps/frontend/src/lib/encryption.ts`

**Implementation:**
```typescript
/**
 * Encrypt large file using chunked approach
 * Prevents memory overflow for files > 500MB
 */
export async function encryptLargeFile(
    file: File,
    key: CryptoKey,
    onProgress?: (percent: number) => void
): Promise<Blob> {
    const CHUNK_SIZE = 1024 * 1024 * 10;  // 10 MB chunks
    const chunks: Blob[] = [];

    // Generate single IV for entire file
    const iv = crypto.getRandomValues(new Uint8Array(12));

    // Prepend IV to first chunk
    chunks.push(new Blob([iv]));

    for (let offset = 0; offset < file.size; offset += CHUNK_SIZE) {
        const chunk = file.slice(offset, offset + CHUNK_SIZE);
        const arrayBuffer = await chunk.arrayBuffer();

        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            arrayBuffer
        );

        chunks.push(new Blob([encrypted]));

        // Update progress bar
        if (onProgress) {
            const progress = ((offset + chunk.size) / file.size) * 100;
            onProgress(Math.min(progress, 100));
        }
    }

    return new Blob(chunks);
}

/**
 * Helper: Estimate encryption time for large files
 */
export function estimateEncryptionTime(fileSizeBytes: number): number {
    // Rough estimate: ~50 MB/second encryption speed
    const speedMBps = 50;
    const fileSizeMB = fileSizeBytes / (1024 * 1024);
    return Math.ceil(fileSizeMB / speedMBps);
}
```

---

### Task 5.2: Streaming Decryption with Progress
**Status:** Not implemented
**Priority:** HIGH (Pairs with 5.1)

**File:** `apps/frontend/src/lib/encryption.ts`

**Implementation:**
```typescript
/**
 * Decrypt large file using chunked approach with progress callback
 */
export async function decryptLargeFile(
    encryptedBlob: Blob,
    key: CryptoKey,
    onProgress?: (percent: number) => void
): Promise<Blob> {
    const CHUNK_SIZE = 1024 * 1024 * 10;  // 10 MB chunks
    const decryptedChunks: Blob[] = [];

    // Extract IV from first 12 bytes
    const ivBlob = encryptedBlob.slice(0, 12);
    const ivBuffer = await ivBlob.arrayBuffer();
    const iv = new Uint8Array(ivBuffer);

    // Process remaining data in chunks
    const dataBlob = encryptedBlob.slice(12);

    for (let offset = 0; offset < dataBlob.size; offset += CHUNK_SIZE) {
        const chunk = dataBlob.slice(offset, offset + CHUNK_SIZE);
        const arrayBuffer = await chunk.arrayBuffer();

        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            arrayBuffer
        );

        decryptedChunks.push(new Blob([decrypted]));

        // Update progress
        if (onProgress) {
            const progress = ((offset + chunk.size) / dataBlob.size) * 100;
            onProgress(Math.min(progress, 100));
        }
    }

    return new Blob(decryptedChunks);
}
```

**Frontend Progress Component:**
```tsx
// apps/frontend/src/components/vault/FileEncryptionProgress.tsx

export function FileEncryptionProgress({
    fileName,
    progress,
    operation
}: {
    fileName: string
    progress: number
    operation: 'encrypting' | 'decrypting'
}) {
    const estimatedTime = Math.ceil((100 - progress) * 0.5);  // seconds

    return (
        <div className="encryption-progress">
            <div className="flex items-center justify-between mb-2">
                <span className="font-medium">
                    {operation === 'encrypting' ? '🔒 Encrypting' : '🔓 Decrypting'} {fileName}
                </span>
                <span className="text-sm text-gray-500">
                    {progress.toFixed(1)}%
                </span>
            </div>

            <div className="progress-bar">
                <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                />
            </div>

            {progress < 100 && (
                <p className="text-xs text-gray-500 mt-1">
                    Estimated time remaining: ~{estimatedTime}s
                </p>
            )}
        </div>
    );
}
```

---

### Task 5.3: SettingsModal Code Splitting (Optional)
**Status:** Not implemented
**Priority:** LOW (Deferred - bundle size optimization)

**Description:** Code-split large settings tabs to reduce initial bundle size. Only load when needed.

**Implementation:**
```tsx
// apps/frontend/src/components/SettingsModal.tsx

import { lazy, Suspense } from 'react';

// Lazy load heavy tabs
const PowerUserTab = lazy(() => import('./settings/PowerUserTab'));
const DangerZoneTab = lazy(() => import('./settings/DangerZoneTab'));
const ModelManagementTab = lazy(() => import('./settings/ModelManagementTab'));
const AuditLogsTab = lazy(() => import('./settings/AuditLogsTab'));

export function SettingsModal() {
    const [activeTab, setActiveTab] = useState('general');

    return (
        <div className="settings-modal">
            <TabList activeTab={activeTab} onChange={setActiveTab} />

            <Suspense fallback={<LoadingSpinner />}>
                {activeTab === 'general' && <GeneralTab />}
                {activeTab === 'power-user' && <PowerUserTab />}
                {activeTab === 'danger-zone' && <DangerZoneTab />}
                {activeTab === 'models' && <ModelManagementTab />}
                {activeTab === 'audit-logs' && <AuditLogsTab />}
            </Suspense>
        </div>
    );
}
```

**Expected Impact:**
- Reduce initial bundle by ~150KB
- Faster initial page load
- Tabs load on-demand (< 100ms delay)

---

## Summary: Remaining Priorities

### DO NEXT (Low Priority - Phase 4):
1. MagnetarMesh connection pooling (performance)
2. Optional cloud connector (backup feature)
3. Context preservation improvements (AI enhancement)

### DO LAST (Critical for Production - Phase 5):
4. **Large file encryption** ⚠️ HIGH - Production blocker for 500MB+ files
5. **Streaming decryption** ⚠️ HIGH - Pairs with #4
6. Code splitting (Optional - Low priority)

---

## Recommended Implementation Order

### Phase 5 First (Critical):
1. **Task 5.1 & 5.2** - Large file encryption/decryption (HIGH priority, production blocker)
   - Current limitation: Cannot handle files > 500MB
   - Will crash browser on large files
   - Must be fixed before production release

### Phase 4 Last (Optional):
2. **Task 4.6** - MagnetarMesh pooling (Low priority, performance optimization)
3. **Task 4.7** - Cloud connector (Low priority, optional feature)
4. **Task 4.8** - Context preservation (Low priority, AI enhancement)
5. **Task 5.3** - Code splitting (Low priority, optimization)

---

**Total Remaining:** 6 tasks | **Critical:** 2 tasks | **Optional:** 4 tasks

**Copyright (c) 2025 MagnetarAI, LLC**
**Built with conviction. Deployed with compassion. Powered by faith.**
