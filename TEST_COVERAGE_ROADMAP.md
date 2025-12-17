# Test Coverage Expansion Roadmap

## Current Status: 62% Coverage (315 tests)
## Target: 75%+ Coverage
## Gap: +13% coverage needed (~40-50 additional tests)

---

## ✅ Completed Test Suites

### Security & Performance (36 tests)
- ✅ test_security_fixes.py (11 tests) - All critical/high security fixes validated
- ✅ test_performance_benchmark.py (5 tests) - Connection pool, queries, cache, IPv6
- ✅ test_api_integration.py (20 tests) - Health, security headers, session security, etc.

### Authentication & Authorization (Multiple test files)
- ✅ test_auth_sessions.py - Session management
- ✅ test_auth_founder_bootstrap.py - Founder setup
- ✅ test_auth_migrations.py - Auth DB migrations
- ✅ test_auth_update_safety.py - Safe auth updates
- ✅ test_rbac_policies.py - RBAC permissions

### Workflows & Agent System (Multiple test files)
- ✅ test_workflow_* (8 test files) - Workflow operations
- ✅ test_agent_* (3 test files) - Agent routing, sessions, workflow integration

### Other Functional Areas
- ✅ test_users_api.py - User management
- ✅ test_emergency_mode.py - Emergency wipe
- ✅ test_audit_events.py - Audit logging
- ✅ test_neutron_core.py - Data engine
- ✅ test_pulsar_core.py - Excel processing

**Total:** 315 tests across 29 test files

---

## 🎯 High-Priority Test Gaps (Remaining Work)

### Priority 1: Authentication & Security (Critical)

#### 1.1 test_auth_middleware_unit.py (NEW - 15-20 tests)
**Coverage:** JWT validation, token lifecycle, refresh tokens

Tests needed:
- JWT token generation with correct claims
- JWT token validation (valid/invalid/expired)
- Access token lifetime enforcement (1 hour)
- Refresh token lifecycle (30 days)
- Token blacklisting on password change
- Invalid signature detection
- Malformed token handling
- Missing claims handling
- Expired token refresh flow
- Concurrent token refresh handling
- Token secret rotation
- get_current_user dependency testing
- Authorization header parsing
- Bearer token format validation
- Session invalidation on logout

**Estimated Coverage Gain:** +3-4%

---

#### 1.2 test_encrypted_audit_logger.py (NEW - 10-15 tests)
**Coverage:** Encryption at rest, audit trails, tamper detection

Tests needed:
- AES-256-GCM encryption/decryption
- Audit log creation with all fields
- Log rotation at size limit
- Tamper detection (hash verification)
- Log retrieval with decryption
- Concurrent log writes (thread safety)
- Log levels (INFO, WARN, ERROR)
- Action types (LOGIN, LOGOUT, etc.)
- User context in logs
- IP address logging
- Log file permissions (600)
- Encryption key management
- Log cleanup (retention policy)
- Performance under load
- Error handling (disk full, etc.)

**Estimated Coverage Gain:** +2-3%

---

### Priority 2: Middleware & Infrastructure

#### 2.1 test_middleware_security.py (NEW - 8-12 tests)
**Coverage:** Security headers, CORS, rate limiting

Tests needed:
- OWASP security headers present
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy validation
- HSTS header (production + reverse proxy)
- CORS policy enforcement
- Allowed origins validation
- Rate limiting per endpoint
- Rate limit headers (X-RateLimit-*)
- Request ID generation/propagation
- Error response format consistency
- Middleware ordering correctness

**Estimated Coverage Gain:** +2-3%

---

#### 2.2 test_cache_service.py (NEW - 6-10 tests)
**Coverage:** Redis caching, fallback behavior

Tests needed:
- Redis connection handling
- Cache hit/miss behavior
- Cache expiration (TTL)
- Cache invalidation
- Redis unavailable fallback
- Thread-safe cache operations
- Cache key generation
- Cache statistics
- LRU eviction
- Serialization/deserialization

**Estimated Coverage Gain:** +1-2%

---

### Priority 3: Edge Cases & Error Handling

#### 3.1 test_error_handling.py (NEW - 8-12 tests)
**Coverage:** HTTP errors, exception handling, error responses

Tests needed:
- 400 Bad Request format
- 401 Unauthorized scenarios
- 403 Forbidden with reasons
- 404 Not Found responses
- 409 Conflict handling
- 422 Validation errors (Pydantic)
- 429 Rate limit exceeded
- 500 Internal server error
- Database connection errors
- File I/O errors
- External API failures
- Graceful degradation

**Estimated Coverage Gain:** +2%

---

#### 3.2 test_input_validation.py (NEW - 6-10 tests)
**Coverage:** Pydantic models, input sanitization

Tests needed:
- SQL injection patterns blocked
- XSS payloads sanitized
- Path traversal attempts blocked
- Command injection prevention
- File upload validation
- Size limit enforcement
- MIME type validation
- Filename sanitization
- JSON schema validation
- Email validation
- URL validation

**Estimated Coverage Gain:** +1-2%

---

## 📊 Expected Coverage After Completion

| Priority | Tests Added | Coverage Gain | Cumulative Coverage |
|----------|-------------|---------------|---------------------|
| Current | 315 | 62% | 62% |
| Priority 1 (Auth) | +35 | +6-7% | 68-69% |
| Priority 2 (Middleware) | +18 | +3-5% | 71-74% |
| Priority 3 (Edge Cases) | +18 | +3% | 74-77% |
| **Total** | **+71 tests** | **+12-15%** | **74-77%** ✅ |

---

## 🔄 Implementation Strategy

### Phase 1: Critical Security Tests (Week 1)
1. Create test_auth_middleware_unit.py
2. Create test_encrypted_audit_logger.py
3. Run full test suite, fix any failures
4. Update coverage metrics

### Phase 2: Infrastructure Tests (Week 2)
1. Create test_middleware_security.py
2. Create test_cache_service.py
3. Run full test suite
4. Update coverage metrics

### Phase 3: Edge Cases & Polish (Week 3)
1. Create test_error_handling.py
2. Create test_input_validation.py
3. Fill any remaining gaps
4. Final coverage validation
5. Update documentation

---

## 🛠️ Testing Best Practices

### Test File Structure
```python
"""
Module: test_<module_name>.py
Purpose: Test <module> functionality

Coverage:
- Feature 1
- Feature 2
- Edge cases
"""

import pytest
from api.<module> import <classes>

class Test<FeatureName>:
    """Test <feature> functionality"""
    
    def test_<scenario>(self):
        """Test <specific scenario>"""
        # Arrange
        # Act
        # Assert
```

### Test Naming Convention
- `test_<feature>_<scenario>_<expected_outcome>`
- Example: `test_jwt_validation_expired_token_raises_unauthorized`

### Coverage Goals
- Critical paths: 100%
- Security features: 100%
- Error handling: 90%+
- Happy paths: 80%+
- Edge cases: 70%+

---

## 📈 Progress Tracking

### Metrics to Track
- Total test count
- Coverage percentage
- Tests per module
- Test execution time
- Flaky test count (target: 0)
- Code coverage by file

### Success Criteria
- ✅ 75%+ overall coverage
- ✅ 100% coverage on security-critical modules
- ✅ All tests passing
- ✅ < 2 second test suite execution time
- ✅ Zero flaky tests

---

## 🎯 Quick Start: Next Steps

1. **Start with Priority 1.1** (test_auth_middleware_unit.py)
   - Most critical for security validation
   - Covers 632 lines of auth code
   - Expected: +3-4% coverage

2. **Run after each test file:**
   ```bash
   pytest tests/test_<new_file>.py -v
   pytest tests/ --cov=api --cov-report=term-missing
   ```

3. **Commit after each completed test file:**
   ```bash
   git add tests/test_<new_file>.py
   git commit -m "test: Add <module> unit tests (+X tests, coverage: Y%)"
   ```

---

**Last Updated:** 2025-12-17  
**Current Coverage:** 62% (315 tests)  
**Target Coverage:** 75%+  
**Status:** Roadmap complete, ready for implementation
