# Security Remediation Roadmap
## Updated: 2025-12-28 (Full Repo Audit)

This roadmap addresses security vulnerabilities identified in comprehensive security audits. Items are ordered from **least complex to most complex** for efficient remediation.

---

## Executive Summary

| Severity | Count | Estimated Effort |
|----------|-------|------------------|
| CRITICAL | 5 | 6-8 hours |
| HIGH | 4 | 6-8 hours |
| MEDIUM | 8 | 6-8 hours |
| LOW | 2 | 1-2 hours |
| **Total** | **19** | **19-26 hours** |

**New findings from 2025-12-28 audit:** 7 additional issues identified (marked with 🆕)

---

## TIER 1: QUICK WINS (< 15 min each)

### 1.1 🆕 Fix Hardcoded JWT Fallback Secret
**Severity:** CRITICAL
**File:** `apps/backend/api/collab_ws.py:56`
**Effort:** 5 minutes

**Current (CRITICAL VULNERABILITY):**
```python
JWT_SECRET = os.getenv("ELOHIMOS_JWT_SECRET_KEY", "dev-secret-key")
```

**Fix:**
```python
def _get_jwt_secret() -> str:
    secret = os.getenv("ELOHIMOS_JWT_SECRET_KEY")
    if not secret:
        # In collab_ws context, fallback to the main JWT secret
        from api.auth_middleware import get_jwt_secret
        return get_jwt_secret()
    return secret

JWT_SECRET = _get_jwt_secret()
```

**Why:** Hardcoded fallback allows complete authentication bypass. Attacker can forge any JWT token.

---

### 1.2 🆕 Protect /diagnostics Endpoint
**Severity:** MEDIUM
**File:** `apps/backend/api/routes/system.py` (around line 151)
**Effort:** 5 minutes

**Current:**
```python
@router.get("/diagnostics")
async def get_diagnostics():
```

**Fix:**
```python
@router.get("/diagnostics")
async def get_diagnostics(current_user: Dict = Depends(get_current_user)):
```

**Why:** Exposes system information (Python version, OS, uptime) to unauthenticated users.

---

### 1.3 Add chunk_index Upper Bound Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/routes/cloud_storage.py:272-278`
**Effort:** 5 minutes

**Current:**
```python
chunk_index: int = Form(..., ge=0),  # No upper bound
```

**Fix:**
```python
chunk_index: int = Form(..., ge=0, le=10000),  # Reasonable upper bound
```

---

### 1.4 Add Model Name Regex Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/agent/intent_classifier.py:30`
**Effort:** 10 minutes

**Fix:**
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

### 1.5 🆕 Enable IAT Verification in JWT Decode
**Severity:** LOW
**File:** `apps/backend/api/auth_middleware.py:416`
**Effort:** 5 minutes

**Current:**
```python
options={'verify_iat': False},  # Disabled for clock skew
```

**Fix:**
```python
options={'verify_iat': True},  # Enable with adequate leeway
leeway=120  # 2 minutes handles clock skew
```

---

## TIER 2: EASY FIXES (15-30 min each)

### 2.1 🆕 Fix Unverified JWT in Logout
**Severity:** CRITICAL
**File:** `apps/backend/api/auth_routes.py:465`
**Effort:** 15 minutes

**Current (CRITICAL VULNERABILITY):**
```python
# Decode without verification to get session_id
payload = jwt.decode(token, options={"verify_signature": False})
```

**Fix:**
```python
try:
    # Still verify signature, but allow expired tokens for logout
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"verify_exp": False}  # Allow expired, but verify signature
    )
except jwt.InvalidTokenError:
    # If completely invalid token, just return success (already logged out)
    return SuccessResponse(data={"message": "Logged out"})

session_id = payload.get('session_id')
```

**Why:** Allows attackers to forge logout requests for any user, potentially causing session confusion.

---

### 2.2 Fix HTTP Header Injection in Download
**Severity:** HIGH
**File:** `apps/backend/api/routes/vault/files/download.py:297`
**Effort:** 15 minutes

**Fix:**
```python
import re

def sanitize_header_value(value: str) -> str:
    """Remove characters that could break HTTP headers"""
    return re.sub(r'[\r\n\x00-\x1f\x7f"]', '_', value)

# In endpoint:
safe_filename = sanitize_header_value(file_row['filename'])
```

---

### 2.3 Fix SQL Injection in ORDER BY Clause
**Severity:** CRITICAL
**File:** `apps/backend/api/routes/vault/files/management.py:201-212`
**Effort:** 20 minutes

**Fix:** Use enum validation:
```python
from enum import Enum

class SortField(str, Enum):
    NAME = "name"
    DATE = "date"
    SIZE = "size"

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
    # Use parameterized ORDER BY or SafeSQLBuilder
```

---

### 2.4 Fix SQL Injection in NLQ Table Name
**Severity:** CRITICAL
**File:** `apps/backend/api/services/nlq_service.py:270`
**Effort:** 20 minutes

**Fix:**
```python
from api.security.sql_safety import quote_identifier, validate_identifier

# Get allowed tables from engine
allowed_tables = engine.get_all_table_names()

# Validate table name
validated_table = validate_identifier(table_name, allowed=allowed_tables)
sample_query = f"SELECT * FROM {quote_identifier(validated_table)} LIMIT 3"
```

---

### 2.5 Add Path Containment Check in File Download
**Severity:** HIGH
**File:** `apps/backend/api/routes/vault/files/download.py:259-270`
**Effort:** 20 minutes

**Fix:**
```python
vault_files_dir = service.files_path.resolve()
encrypted_file_path = Path(file_row['encrypted_path']).resolve()

# SECURITY: Ensure path is within vault directory
if not str(encrypted_file_path).startswith(str(vault_files_dir)):
    logger.error(f"SECURITY: Path traversal attempt: {file_row['encrypted_path']}")
    raise HTTPException(status_code=403, detail="Invalid file path")
```

---

### 2.6 🆕 Use Constant-Time Password Comparison
**Severity:** LOW
**File:** `apps/backend/api/auth_middleware.py:263-275`
**Effort:** 5 minutes

**Current:**
```python
return pwd_hash.hex() == hash_hex  # String comparison (timing vulnerable)
```

**Fix:**
```python
import hmac
return hmac.compare_digest(pwd_hash.hex(), hash_hex)  # Constant-time
```

---

## TIER 3: MODERATE FIXES (30-60 min each)

### 3.1 Add SQLite-Specific Keywords to NLQ Validation
**Severity:** MEDIUM
**File:** `apps/backend/api/services/nlq_service.py:417-486`
**Effort:** 30 minutes

**Fix:**
```python
dangerous_keywords = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
    'EXEC', 'EXECUTE', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE',
    # SQLite-specific:
    'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX',
]
```

---

### 3.2 Add SQL Validation to execute_sql
**Severity:** HIGH
**File:** `apps/backend/api/data_engine.py:357`
**Effort:** 45 minutes

**Fix:**
```python
def execute_sql(self, query: str) -> Dict[str, Any]:
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
        'ATTACH', 'DETACH', 'PRAGMA', 'CREATE', 'TRUNCATE'
    ]

    query_upper = query.upper()
    for keyword in dangerous_keywords:
        if re.search(r'\b' + keyword + r'\b', query_upper):
            raise ValueError(f"Forbidden SQL keyword: {keyword}")

    if 'LIMIT' not in query_upper:
        query = f"{query} LIMIT {self.max_query_rows}"
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
    if shell not in ALLOWED_SHELLS:
        raise ValueError(f"Invalid shell")

    shell_stat = os.stat(shell)
    if not stat.S_ISREG(shell_stat.st_mode):
        raise ValueError(f"Shell is not a regular file")

    if not os.access(shell, os.X_OK):
        raise ValueError(f"Shell is not executable")

    if '\x00' in shell:
        raise ValueError("Invalid shell path")

    return shell
```

---

### 3.4 🆕 Move WebSocket JWT to Headers
**Severity:** MEDIUM
**File:** `apps/backend/api/collab_ws.py:62-80`
**Effort:** 45 minutes

**Current:**
```python
# JWT in URL query parameter (can be logged)
token = query_params.get("token")
```

**Fix:**
```python
# Prefer Sec-WebSocket-Protocol header
protocol_header = websocket.headers.get("Sec-WebSocket-Protocol", "")
if protocol_header.startswith("bearer."):
    token = protocol_header.replace("bearer.", "", 1)
else:
    # Fallback to query param for backwards compatibility
    token = query_params.get("token")
```

---

## TIER 4: COMPLEX FIXES (1-2 hours each)

### 4.1 Add File Locking for Chunked Uploads
**Severity:** HIGH
**Files:** `apps/backend/api/routes/vault/files/upload.py`, `cloud_storage.py`
**Effort:** 1-2 hours

**Fix:** Use fcntl file locking to prevent TOCTOU race conditions:
```python
import fcntl
from contextlib import contextmanager

@contextmanager
def file_lock(lock_path: Path):
    lock_file = lock_path / ".lock"
    lock_file.touch(exist_ok=True)
    with open(lock_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

### 4.2 Remove shell=True from Codex Engine
**Severity:** CRITICAL
**File:** `apps/backend/api/agent/engines/codex_engine.py`
**Lines:** 96-120, 195-197, 445-462 (6 locations)
**Effort:** 2-3 hours

**Current (CRITICAL VULNERABILITY):**
```python
dry = subprocess.run(
    f"patch -p{patch_level} --dry-run < '{tmp.name}'",
    shell=True,  # CRITICAL: Command injection vector!
    ...
)
```

**Fix:**
```python
def apply_patch_secure(patch_file: Path, patch_level: int, dry_run: bool = True):
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
```

---

## Progress Tracking

### Status Legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete

### Checklist

#### Tier 1: Quick Wins (< 15 min each) ✅ COMPLETE
- [x] 1.1 🆕 Fix hardcoded JWT fallback secret (CRITICAL) - collab_ws.py now requires secret
- [x] 1.2 🆕 Protect /diagnostics endpoint - Added get_current_user dependency
- [x] 1.3 Add chunk_index upper bound - Added le=10000 validation
- [x] 1.4 Add model name validation - Added regex validation in intent_classifier.py
- [x] 1.5 🆕 Enable IAT verification - Changed to verify_iat=True with 120s leeway

#### Tier 2: Easy Fixes (15-30 min each) ✅ COMPLETE
- [x] 2.1 🆕 Fix unverified JWT in logout (CRITICAL) - Now verifies signature, allows expired
- [x] 2.2 Fix HTTP header injection (HIGH) - Sanitize filename with regex in download.py
- [x] 2.3 Fix ORDER BY SQL injection (CRITICAL) - Strict allowlist in management.py
- [x] 2.4 Fix NLQ table name injection (CRITICAL) - Uses quote_identifier() in nlq_service.py
- [x] 2.5 Add path containment check (HIGH) - Path.resolve() + startswith check in download.py
- [x] 2.6 🆕 Use constant-time password comparison - hmac.compare_digest() in auth_middleware.py

#### Tier 3: Moderate Fixes (30-60 min each) ✅ COMPLETE
- [x] 3.1 Add SQLite keywords to NLQ validation - Added ATTACH, DETACH, PRAGMA, VACUUM, REINDEX
- [x] 3.2 Add SQL validation to execute_sql (HIGH) - Added keyword blocklist + auto LIMIT
- [x] 3.3 Complete shell validation - Added stat.S_ISREG, os.access(X_OK), null byte check
- [x] 3.4 🆕 Move WebSocket JWT to headers - Added `extract_websocket_token()` helper, updated all 4 WS endpoints

#### Tier 4: Complex Fixes (1-2 hours each) ✅ COMPLETE (except 4.1)
- [ ] 4.1 Add file locking for chunked uploads (HIGH) - **Deferred: only matters with concurrent uploads**
- [x] 4.2 Remove shell=True from codex_engine (CRITICAL) - All 6 locations fixed with stdin pipes

---

## Verification Commands

```bash
# Run security-focused tests
PYTHONPATH="$PWD:$PWD/api:$PYTHONPATH" pytest tests/test_middleware_security.py -v

# Run full test suite
PYTHONPATH="$PWD:$PWD/api:$PYTHONPATH" pytest tests/ -v

# Manual verification
# 1. Try SQL injection in sort_by parameter
# 2. Try path traversal in file download
# 3. Try command injection in codex operations
# 4. Verify /diagnostics requires auth
# 5. Check JWT fallback doesn't exist
```

---

## Notes for Pre-Release Development

**Priority Order:**
1. **CRITICAL items first** - even in dev, these could compromise your machine
2. **Tier 1 items are trivial** - can knock out all 5 in under an hour
3. **SQL injections** - protect your dev database from accidents
4. **shell=True removal** - this is the most complex but most dangerous

**What Can Wait:**
- WebSocket JWT migration (client changes needed)
- File locking (complex, only matters with concurrent uploads)
- Constant-time comparison (minimal real-world risk)

---

## Code Quality Review Verification (2025-12-28)

Senior engineering review performed to verify remediation completeness.

### Verified Fixes
- **shell=True removal**: Confirmed removed from all internal code. Only remains in `external/aider/` (third-party).
- **Hardcoded JWT secret**: Confirmed `dev-secret-key` no longer exists.
- **Unverified JWT logout**: Confirmed `verify_signature: False` pattern eliminated.
- **JWT empty default**: Confirmed `model_validator` at `config.py:164-199` handles this:
  - Development: Auto-generates secure secret with warning
  - Production: Fails startup with clear error message

### External Dependency Risk
```
apps/backend/external/aider/aider/commands.py:389,405 - shell=True
```
**Status:** Accepted risk (third-party code, sandboxed usage)
**Recommendation:** Consider subprocess isolation or replacement in future

### Code Quality Findings (Non-Security) ✅ RESOLVED
| Item | Severity | Status |
|------|----------|--------|
| `chat/models.py` 886 lines | HIGH | ✅ Split into 6 focused modules |
| Swift @Observable inconsistency | MEDIUM | ✅ 8 stores migrated to @Observable |
| Type ignores in workflow_storage.py | LOW | ✅ Fixed import paths |

---

**Created:** 2025-12-27
**Last Updated:** 2026-01-03 (WebSocket JWT Header Fix)
**Status:** 18/19 items FIXED, 1 deferred (file locking - low priority for pre-release)
