# Security Remediation Roadmap
## Created: 2025-12-27 (Post-Audit)

This roadmap addresses security vulnerabilities identified in the comprehensive security audit conducted on 2025-12-27. Items are ordered from **least complex to most complex** for efficient remediation.

---

## Executive Summary

| Severity | Count | Estimated Effort |
|----------|-------|------------------|
| CRITICAL | 3 | 4-6 hours |
| HIGH | 4 | 6-8 hours |
| MEDIUM | 5 | 4-6 hours |
| **Total** | **12** | **14-20 hours** |

---

## TIER 1: QUICK WINS (< 30 min each)

### 1.1 Add chunk_index Upper Bound Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/routes/cloud_storage.py:272-278`
**Effort:** 10 minutes

**Current:**
```python
chunk_index: int = Form(..., ge=0),  # No upper bound
```

**Fix:**
```python
chunk_index: int = Form(..., ge=0, le=10000),  # Reasonable upper bound
```

**Why:** Prevents DoS via excessive chunk_index values creating thousands of files.

---

### 1.2 Add Model Name Regex Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/agent/intent_classifier.py:30`
**Effort:** 15 minutes

**Fix:** Add validation before subprocess call:
```python
import re

def _validate_model_name(model: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._-]+(?::[a-zA-Z0-9._-]+)?$', model))

def _run_ollama(model: str, prompt: str, timeout: int = 20):
    if not _validate_model_name(model):
        return None
    # ... existing code
```

---

### 1.3 Fix HTTP Header Injection in Download
**Severity:** HIGH
**File:** `apps/backend/api/routes/vault/files/download.py:297`
**Effort:** 20 minutes

**Fix:** Sanitize filename for HTTP headers:
```python
import re

def sanitize_header_value(value: str) -> str:
    """Remove characters that could break HTTP headers"""
    return re.sub(r'[\r\n\x00-\x1f\x7f"]', '_', value)

# In endpoint:
safe_filename = sanitize_header_value(file_row['filename'])
return FileResponse(
    path=temp_file.name,
    filename=safe_filename,
    media_type=file_row['mime_type'] or 'application/octet-stream',
    headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""}
)
```

---

## TIER 2: EASY FIXES (30-60 min each)

### 2.1 Fix SQL Injection in ORDER BY Clause
**Severity:** CRITICAL
**File:** `apps/backend/api/routes/vault/files/management.py:201-212`
**Effort:** 30 minutes

**Current (vulnerable):**
```python
order_clause = {...}.get(sort_by, 'filename ASC')
cursor.execute(f"... ORDER BY {order_clause} ...")
```

**Fix:** Use enum validation + SafeSQLBuilder:
```python
from enum import Enum
from api.security.sql_safety import SafeSQLBuilder

class SortField(str, Enum):
    NAME = "name"
    DATE = "date"
    SIZE = "size"

# In endpoint:
def get_vault_files_paginated(
    sort_by: SortField = SortField.NAME,  # Enum enforces valid values
    ...
):
    order_map = {
        SortField.NAME: ("filename", False),
        SortField.DATE: ("created_at", True),
        SortField.SIZE: ("file_size", True),
    }
    col, desc = order_map[sort_by]

    builder = SafeSQLBuilder("vault_files")
    builder.select(["*"]).where("user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0")
    builder.order_by(col, desc=desc).limit(page_size).offset(offset)

    cursor.execute(builder.build(), (user_id, vault_type, folder_path))
```

---

### 2.2 Fix SQL Injection in NLQ Table Name
**Severity:** CRITICAL
**File:** `apps/backend/api/services/nlq_service.py:270`
**Effort:** 30 minutes

**Current (vulnerable):**
```python
sample_query = f"SELECT * FROM {table_name} LIMIT 3"
```

**Fix:** Use existing sql_safety module:
```python
from api.security.sql_safety import quote_identifier, validate_identifier

# Get allowed tables from engine
allowed_tables = engine.get_all_table_names()

# Validate table name
try:
    validated_table = validate_identifier(table_name, allowed=allowed_tables, context="table name")
    sample_query = f"SELECT * FROM {quote_identifier(validated_table)} LIMIT 3"
except SQLInjectionError:
    logger.error(f"Invalid table name in NLQ: {table_name}")
    raise ValueError(f"Invalid table name")
```

---

### 2.3 Add SQLite-Specific Keywords to NLQ Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/services/nlq_service.py:417-486`
**Effort:** 45 minutes

**Fix:** Extend dangerous keywords list:
```python
# Add SQLite-specific keywords
dangerous_keywords = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
    'EXEC', 'EXECUTE', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE',
    # SQLite-specific additions:
    'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX',
]

# Add Unicode normalization before checking
import unicodedata
sql_normalized = unicodedata.normalize('NFKD', sql).upper()

for keyword in dangerous_keywords:
    if re.search(r'\b' + keyword + r'\b', sql_normalized):
        errors.append(f"Forbidden keyword: {keyword}")
```

---

### 2.4 Add Path Containment Check in File Download
**Severity:** HIGH
**File:** `apps/backend/api/routes/vault/files/download.py:259-270`
**Effort:** 30 minutes

**Fix:** Validate file path is within vault directory:
```python
# Get the vault files directory
vault_files_dir = service.files_path.resolve()

# Resolve the encrypted path
encrypted_file_path = Path(file_row['encrypted_path']).resolve()

# SECURITY: Ensure path is within vault directory (prevents path traversal)
if not str(encrypted_file_path).startswith(str(vault_files_dir)):
    logger.error(f"SECURITY: Path traversal attempt: {file_row['encrypted_path']}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(
            error_code=ErrorCode.FORBIDDEN,
            message="Invalid file path"
        ).model_dump()
    )

if not encrypted_file_path.exists():
    raise HTTPException(...)
```

---

## TIER 3: MODERATE FIXES (1-2 hours each)

### 3.1 Add File Locking for Chunked Uploads
**Severity:** HIGH
**Files:**
- `apps/backend/api/routes/vault/files/upload.py:181-198`
- `apps/backend/api/routes/cloud_storage.py:406-411`
**Effort:** 1-2 hours

**Fix:** Use file locking to prevent TOCTOU race conditions:
```python
import fcntl
from contextlib import contextmanager

@contextmanager
def file_lock(lock_path: Path):
    """Acquire exclusive file lock for atomic operations"""
    lock_file = lock_path / ".lock"
    lock_file.touch(exist_ok=True)
    with open(lock_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# In chunked upload endpoint:
async def upload_chunk(...):
    temp_dir = service.files_path / "temp_chunks" / file_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Use lock for chunk counting and assembly
    with file_lock(temp_dir):
        # Save chunk
        chunk_path = temp_dir / f"chunk_{chunk_index}"
        chunk_data = await chunk.read()
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)

        # Check if all chunks received (atomic under lock)
        received_chunks = list(temp_dir.glob("chunk_*"))

        if len(received_chunks) == total_chunks:
            # Assemble file (still under lock)
            # ... assembly code ...
```

---

### 3.2 Add SQL Validation to execute_sql
**Severity:** HIGH
**File:** `apps/backend/api/data_engine.py:357`
**Effort:** 1 hour

**Fix:** Block dangerous SQL keywords:
```python
import re

def execute_sql(self, query: str) -> Dict[str, Any]:
    """Execute SQL with safety validation"""

    # SECURITY: Validate SQL before execution
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'ATTACH', 'DETACH', 'PRAGMA', 'CREATE', 'TRUNCATE'
    ]

    query_upper = query.upper()
    for keyword in dangerous_keywords:
        if re.search(r'\b' + keyword + r'\b', query_upper):
            raise ValueError(f"Forbidden SQL keyword: {keyword}. Use dedicated API endpoints for modifications.")

    # Limit result size to prevent DoS
    if 'LIMIT' not in query_upper:
        query = f"{query} LIMIT {self.max_query_rows}"

    # Existing execution code...
```

---

### 3.3 Complete Shell Validation
**Severity:** MEDIUM
**File:** `apps/backend/services/terminal_bridge.py:106-118`
**Effort:** 30 minutes

**Fix:** Add file type and permission checks:
```python
import stat

def validate_shell(shell: str) -> str:
    """Validate shell binary with comprehensive checks"""

    # Check whitelist
    if shell not in ALLOWED_SHELLS:
        logger.error(f"SECURITY: Rejected invalid shell: {shell}")
        raise ValueError(f"Invalid shell. Allowed: {', '.join(ALLOWED_SHELLS)}")

    # Check existence
    if not os.path.exists(shell):
        raise ValueError(f"Shell does not exist: {shell}")

    # Check it's a regular file (not symlink to malicious binary)
    shell_stat = os.stat(shell)
    if not stat.S_ISREG(shell_stat.st_mode):
        logger.error(f"SECURITY: Shell is not a regular file: {shell}")
        raise ValueError(f"Shell is not a regular file: {shell}")

    # Check executable permission
    if not os.access(shell, os.X_OK):
        raise ValueError(f"Shell is not executable: {shell}")

    # Check for null bytes in path
    if '\x00' in shell:
        logger.error(f"SECURITY: Null byte in shell path")
        raise ValueError("Invalid shell path")

    return shell
```

---

## TIER 4: COMPLEX FIXES (2-4 hours each)

### 4.1 Remove shell=True from Codex Engine
**Severity:** CRITICAL
**File:** `apps/backend/api/agent/engines/codex_engine.py`
**Lines:** 96-120, 195-197, 445-462
**Effort:** 3-4 hours

**Current (CRITICAL VULNERABILITY):**
```python
dry = subprocess.run(
    f"patch -p{patch_level} --dry-run < '{tmp.name}'",
    shell=True,  # CRITICAL: Command injection vector!
    ...
)
```

**Fix:** Convert ALL shell=True calls to list arguments:
```python
# SECURE: No shell, no injection
def apply_patch_secure(patch_file: Path, patch_level: int, dry_run: bool = True) -> tuple[bool, str]:
    """Apply patch without shell=True (no command injection)"""

    cmd = ['patch', f'-p{patch_level}']
    if dry_run:
        cmd.append('--dry-run')

    with open(patch_file, 'r') as f:
        result = subprocess.run(
            cmd,
            stdin=f,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    return result.returncode == 0, result.stdout + result.stderr

# Update all 6 locations in codex_engine.py:
# Lines 96-97, 107-108, 119-120, 196-197, 446-447, 461-462
```

**Testing Checklist:**
- [ ] Test dry-run patch application
- [ ] Test actual patch application
- [ ] Test with malicious filenames
- [ ] Test timeout behavior
- [ ] Verify no regressions in aider/codex integration

---

## Progress Tracking

### Status Legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked

### Checklist

#### Tier 1: Quick Wins
- [ ] 1.1 Add chunk_index upper bound
- [ ] 1.2 Add model name validation
- [ ] 1.3 Fix HTTP header injection

#### Tier 2: Easy Fixes
- [ ] 2.1 Fix ORDER BY SQL injection
- [ ] 2.2 Fix NLQ table name injection
- [ ] 2.3 Add SQLite keywords to NLQ
- [ ] 2.4 Add path containment check

#### Tier 3: Moderate Fixes
- [ ] 3.1 Add file locking for chunked uploads
- [ ] 3.2 Add SQL validation to execute_sql
- [ ] 3.3 Complete shell validation

#### Tier 4: Complex Fixes
- [ ] 4.1 Remove shell=True from codex_engine

#### Tier 5: Technical Debt (Optional)
- [ ] 5.1 Replace remaining datetime.utcnow()
- [ ] 5.2 Wire Swift chat messaging
- [ ] 5.3 Wire settings actions

---

## Verification

After completing all fixes, run:

```bash
# Run security-focused tests
PYTHONPATH="$PWD:$PWD/api:$PYTHONPATH" pytest tests/test_middleware_security.py -v

# Run full test suite
PYTHONPATH="$PWD:$PWD/api:$PYTHONPATH" pytest tests/ -v

# Manual security verification
# 1. Try SQL injection in sort_by parameter
# 2. Try path traversal in file download
# 3. Try command injection in codex operations
```

---

---

## TIER 5: TECHNICAL DEBT (Optional)

These items are from other roadmaps and are non-security, lower priority:

### 5.1 Replace Remaining `datetime.utcnow()` Calls
**Source:** `MEDIUM_PRIORITY_ISSUES.md` (MED-01)
**Severity:** LOW (deprecation warning)
**Effort:** 2-3 hours (automated search/replace)

**Note:** Tier 5 already modernized 20+ Metal files. Some files remain.

**Fix:**
```python
# OLD (deprecated)
from datetime import datetime
datetime.utcnow()

# NEW
from datetime import datetime, UTC
datetime.now(UTC)
```

### 5.2 Swift Chat Messaging Wiring
**Source:** `TODO_WIRING.md` (HIGH PRIORITY #1)
**File:** `apps/native/Shared/Stores/ChatStore.swift:79-88`
**Effort:** 2-3 hours

Currently returns simulated response. Need to wire to `/api/v1/chat/completions` with SSE streaming.

### 5.3 Settings Actions Wiring
**Source:** `TODO_WIRING.md` (MEDIUM PRIORITY #5)
**File:** `apps/native/macOS/SettingsView.swift`
**Effort:** 1-2 hours

Wire "Test API Connection", "Clear Cache", and other settings actions.

---

## Related Documentation

- Previous security audit: `CRITICAL_BUGS_FOUND.md` (Dec 16, 2025)
- Sprint 0 fixes: `SECURITY_FIXES.md` (Dec 16, 2025)
- Test coverage: `TEST_COVERAGE_ROADMAP.md`
- Refactoring status: `docs/REFACTORING_ROADMAP.md`
- Backend wiring: `TODO_WIRING.md`
- Medium issues: `MEDIUM_PRIORITY_ISSUES.md`

---

## Notes

**Development Mode Considerations:**
Since this is currently in dev mode, prioritize:
1. **CRITICAL items** (command injection) - even in dev, could compromise dev machine
2. **SQL injection** - protects your dev database
3. **TOCTOU** - harder to test, fix architecture now

**Items that can wait for production:**
- HTTP header injection (lower risk in dev)
- Shell validation completeness (already has whitelist)

---

**Created:** 2025-12-27
**Last Updated:** 2025-12-27
**Status:** NEW - Pending Implementation
