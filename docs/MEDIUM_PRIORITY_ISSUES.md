# Medium-Priority Issues

## Status: 5/7 Already Fixed ✅

This document tracks medium-priority improvements for MagnetarStudio.

---

## ✅ FIXED ISSUES (5/7)

### ✅ MED-02: Pre-compile Regex Patterns
**Status:** FIXED  
**Files:** `api/main.py:67`, `api/data_engine.py:31`, `api/utils.py:9`  
**Impact:** Performance optimization - patterns now compiled at module load

### ✅ MED-03: Improved Session Management
**Status:** IMPLEMENTED  
**File:** `api/session_security.py:15`  
**Impact:** Enhanced session tracking, anomaly detection, and fingerprinting

### ✅ MED-04: Security Headers + Composite Index
**Status:** FIXED  
**Files:** `api/app_factory.py:302`, `api/auth_middleware.py:233`  
**Impact:** OWASP-compliant headers + optimized session cleanup queries

### ✅ MED-05: Short-Lived Access Tokens + Refresh Tokens
**Status:** FIXED  
**Files:** `api/auth_middleware.py:99`, `api/auth_routes.py:154`  
**Impact:** Access tokens reduced to 1-hour lifetime, 30-day refresh tokens

### ✅ MED-08: Reduce Hot-Path Logging
**Status:** FIXED  
**File:** `api/metal4_engine.py:419, 466, 480, 495`  
**Impact:** Logging reduced to every 100 frames, slow operations only

---

## ⚠️ REMAINING ISSUES (2/7)

### ⚠️ MED-01: Replace Deprecated `datetime.utcnow()`
**Status:** PARTIALLY COMPLETE (Tier 5 modernized 20+ files, some remain)  
**Files:** 93 files using deprecated `datetime.utcnow()`  
**Priority:** Medium  

**Problem:**
Python 3.12+ deprecates `datetime.utcnow()` in favor of timezone-aware `datetime.now(datetime.UTC)`.

**Impact:**
- Deprecation warnings in tests (19 warnings)
- Future Python versions will remove this API
- Potential timezone confusion bugs

**Files Affected:** 93 files across the codebase
- `api/session_security.py`
- `api/password_breach_checker.py`
- `api/auth_routes.py`
- `api/auth_middleware.py`
- ... and 89 more files

**Recommended Fix:**
Replace all instances of:
```python
# OLD (deprecated)
datetime.utcnow()
datetime.utcnow().isoformat()

# NEW (recommended)
from datetime import datetime, UTC
datetime.now(UTC)
datetime.now(UTC).isoformat()
```

**Effort:** Medium (93 files, automated with search/replace)  
**Benefit:** Future-proof code, cleaner test output

---

### ⚠️ MED-06: True Async Query Cancellation
**Status:** TODO  
**File:** `api/routes/sql_json.py:356`  
**Priority:** Low  

**Problem:**
Using `asyncio.wait_for()` + `asyncio.to_thread()` for query timeout enforcement doesn't actually cancel the running SQLite query.

**Current Behavior:**
- Query times out after N seconds
- But SQLite keeps running the query in background thread
- Thread blocks until query completes

**Recommended Fix:**
Migrate from `sqlite3` to `aiosqlite` for true async support:
```python
# Current (sqlite3)
result = await asyncio.wait_for(
    asyncio.to_thread(engine.execute_sql, sql),
    timeout=300
)

# Proposed (aiosqlite)
async with aiosqlite.connect(db_path) as conn:
    cursor = await asyncio.wait_for(
        conn.execute(sql),
        timeout=300
    )
    # Query actually cancels on timeout
```

**Effort:** High (requires refactoring `data_engine.py` and `neutron_core`)  
**Benefit:** True query cancellation, better resource cleanup

---

## Summary

| Issue | Status | Priority | Effort | Impact |
|-------|--------|----------|--------|--------|
| MED-01 | ⚠️ TODO | Medium | Medium | Future-proofing |
| MED-02 | ✅ FIXED | - | - | Performance |
| MED-03 | ✅ FIXED | - | - | Security |
| MED-04 | ✅ FIXED | - | - | Security |
| MED-05 | ✅ FIXED | - | - | Security |
| MED-06 | ⚠️ TODO | Low | High | Query cancellation |
| MED-07 | ❓ N/A | - | - | Not found |
| MED-08 | ✅ FIXED | - | - | Performance |

**Overall:** 5/7 fixed (71%), 2 remaining (both optional for production)

---

## Recommendations

### Immediate Actions (None Required for Production)
The remaining medium-priority issues are **not blockers** for production deployment:
- MED-01 can be addressed post-launch
- MED-06 is a nice-to-have enhancement

### Post-Launch Improvements
1. **MED-01:** Run automated search/replace for `datetime.utcnow()`
2. **MED-06:** Evaluate aiosqlite migration for Phase 2

---

**Last Updated:** 2025-12-17  
**Production Impact:** None - all critical/high issues already resolved
