# Security Testing Guide
## MagnetarStudio - Comprehensive Security Validation

This guide provides step-by-step instructions for validating all security enhancements implemented during Sprint 0.

---

## 🎯 Testing Objectives

1. Verify all critical/high vulnerabilities are fixed
2. Validate security features work as designed
3. Test edge cases and attack scenarios
4. Confirm OWASP compliance
5. Measure performance impact

---

## Test Environment Setup

### Prerequisites

```bash
# Install testing tools
pip install pytest pytest-asyncio aiohttp requests

# Install security scanning tools (optional)
brew install nmap sqlmap
docker pull owasp/zap2docker-stable

# Start test instance
ELOHIM_ENV=development python3 -m uvicorn api.main:app --reload --port 8000
```

---

## Test Suite 1: Authentication & Session Security

### TEST-01: Short-Lived Access Tokens (MED-05)

**Objective:** Verify JWT tokens expire after 1 hour

```bash
# 1. Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!",
    "device_fingerprint": "test-device"
  }' | jq -r '.token')

echo "Token: $TOKEN"

# 2. Use token immediately (should work)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files

# Expected: 200 OK

# 3. Wait 1 hour + 1 minute
# (For testing, modify JWT_EXPIRATION_HOURS to 1/60 = 1 minute)

# 4. Use token again (should fail)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files

# Expected: 401 Unauthorized
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-02: Token Refresh Flow (MED-05)

**Objective:** Verify refresh tokens work for 30 days

```bash
# 1. Login
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!",
    "device_fingerprint": "test-device"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.token')
REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

# 2. Wait for access token to expire (1 hour or modify to 1 min)

# 3. Refresh access token
NEW_TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" \
  | jq -r '.token')

# 4. Use new token
curl -H "Authorization: Bearer $NEW_TOKEN" \
  http://localhost:8000/api/v1/vault/files

# Expected: 200 OK
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-03: Session Fingerprinting (MED-03)

**Objective:** Verify session anomaly detection works

```bash
# 1. Login from IP 1
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!",
    "device_fingerprint": "browser-firefox-linux"
  }' | jq -r '.token')

# 2. Use token from different IP (suspicious)
curl -H "Authorization: Bearer $TOKEN" \
  -H "X-Forwarded-For: 203.0.113.50" \
  http://localhost:8000/api/v1/vault/files

# 3. Check logs for anomaly detection
tail -f logs/app.log | grep "anomaly detected"

# Expected: Log entry with suspicion score >= 0.5
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-04: Concurrent Session Limits (MED-03)

**Objective:** Verify max 3 sessions per user

```bash
# Login 4 times with same user
for i in {1..4}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "username": "testuser",
      "password": "TestPass123!",
      "device_fingerprint": "device-'$i'"
    }' > token$i.json
  sleep 1
done

# Check database for active sessions
sqlite3 /path/to/auth.db "SELECT COUNT(*) FROM sessions WHERE user_id='user_id' AND is_active=1"

# Expected: 3 (oldest session terminated)
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Suite 2: Password Security

### TEST-05: Password Breach Detection (MED-02)

**Objective:** Verify compromised passwords are rejected

```bash
# 1. Try to register with known breached password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "password123",
    "device_fingerprint": "test"
  }'

# Expected: 400 Bad Request
# Error: "This password has been exposed in X data breach(es)"

# 2. Try strong unique password
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "Xy9Kp2Lm!@#$%^&*()",
    "device_fingerprint": "test"
  }'

# Expected: 200 OK (or 201 Created)
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-06: Breach Detection Caching (MED-02)

**Objective:** Verify 24-hour cache works

```bash
# 1. Check password (should hit API)
python3 << EOF
import asyncio
from api.password_breach_checker import get_breach_checker

async def test():
    checker = get_breach_checker()
    is_breached, count = await checker.check_password("test123")
    stats = checker.get_stats()
    print(f"Breached: {is_breached}, Count: {count}")
    print(f"Cache stats: {stats}")
    await checker.close()

asyncio.run(test())
EOF

# 2. Check same password again (should hit cache)
# Run same script again

# Expected: cache_hits increases, cache_misses stays same
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Suite 3: Input Sanitization

### TEST-07: XSS Prevention (MED-06)

**Objective:** Verify dangerous HTML is stripped

```bash
# 1. Submit XSS payload
curl -X POST http://localhost:8000/api/v1/vault/files \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "<script>alert(\"XSS\")</script>test.txt",
    "content": "test"
  }'

# 2. Check logs for sanitization
tail -f logs/app.log | grep "Dangerous XSS pattern"

# Expected: Log entry showing pattern detected and stripped

# 3. Verify stored filename is clean
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files | jq '.files[].filename'

# Expected: Filename without <script> tags
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-08: SQL Injection Detection (MED-06)

**Objective:** Verify SQL injection patterns are logged

```bash
# 1. Submit SQL injection payload
curl -X POST http://localhost:8000/api/v1/database/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM users WHERE username = \"admin\" OR 1=1--"
  }'

# 2. Check logs for detection
tail -f logs/app.log | grep "SQL injection pattern"

# Expected: Warning log entry (query still executed safely via parameterization)
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-09: Path Traversal Prevention (MED-06)

**Objective:** Verify path traversal is blocked

```bash
# 1. Try path traversal attack
curl -X GET "http://localhost:8000/api/v1/vault/files/../../etc/passwd" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 400 Bad Request or sanitized path

# 2. Try URL-encoded traversal
curl -X GET "http://localhost:8000/api/v1/vault/files/%2e%2e%2f%2e%2e%2fetc%2fpasswd" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 400 Bad Request or sanitized path

# 3. Check logs
tail -f logs/app.log | grep "Path traversal pattern"

# Expected: Warning log entry
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Suite 4: Security Headers

### TEST-10: OWASP Security Headers (MED-04)

**Objective:** Verify all security headers are present

```bash
# Check headers
curl -I http://localhost:8000/api/health

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: default-src 'self'; ...
# Permissions-Policy: geolocation=(), microphone=(), camera=()
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload (production only)
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-11: CORS Enforcement (HIGH-02)

**Objective:** Verify production CORS restrictions

```bash
# 1. Set production environment
export ELOHIM_ENV=production
export ELOHIM_CORS_ORIGINS=https://example.com

# Restart server

# 2. Try request from unauthorized origin
curl -X OPTIONS http://localhost:8000/api/v1/auth/login \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST"

# Expected: CORS error (no Access-Control-Allow-Origin header)

# 3. Try request from authorized origin
curl -X OPTIONS http://localhost:8000/api/v1/auth/login \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST"

# Expected: Access-Control-Allow-Origin: https://example.com
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Suite 5: Encryption & Audit

### TEST-12: Audit Log Encryption (CRIT-07)

**Objective:** Verify audit logs are encrypted

```bash
# 1. Generate audit log entry
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123!",
    "device_fingerprint": "test"
  }'

# 2. Check encrypted audit database
sqlite3 /path/to/encrypted_audit.db "SELECT * FROM audit_logs LIMIT 1"

# Expected: Encrypted binary data in user_id, action, details columns
# (should NOT be readable plaintext)

# 3. Verify decryption works
python3 << EOF
from api.encrypted_audit_logger import get_encrypted_audit_logger
logger = get_encrypted_audit_logger()
logs = logger.get_logs(limit=1)
print(logs)
# Expected: Decrypted readable data
EOF
```

**Result:** ✅ PASS / ❌ FAIL

---

### TEST-13: Connection Pool Performance (RACE-04)

**Objective:** Verify connection pooling improves concurrency

```bash
# 1. Disable connection pool (for comparison)
# Comment out pool usage in code

# 2. Benchmark without pool
ab -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files

# Record: Requests/sec, Failed requests

# 3. Enable connection pool

# 4. Benchmark with pool
ab -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files

# Expected: 80-100% increase in req/sec, 0 failed requests
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Suite 6: Command Injection

### TEST-14: Terminal Shell Validation (CRIT-02b)

**Objective:** Verify shell whitelist works

```bash
# 1. Try allowed shell
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shell": "/bin/bash",
    "cwd": "/tmp"
  }'

# Expected: 200 OK

# 2. Try disallowed shell
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shell": "/bin/evil",
    "cwd": "/tmp"
  }'

# Expected: 400 Bad Request
# Error: "Invalid shell"

# 3. Try shell injection via path
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shell": "/bin/bash",
    "cwd": "/tmp; rm -rf /"
  }'

# Expected: Path sanitized or rejected
```

**Result:** ✅ PASS / ❌ FAIL

---

## Automated Security Scanning

### SCAN-01: OWASP ZAP Baseline

```bash
# Run ZAP baseline scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t http://localhost:8000 \
  -r zap-report.html

# Review report for:
# - SQL Injection vulnerabilities
# - XSS vulnerabilities
# - CSRF vulnerabilities
# - Missing security headers

# Expected: No high/medium issues (informational only)
```

**Result:** ✅ PASS / ❌ FAIL

---

### SCAN-02: SQL Injection Scanner

```bash
# Run sqlmap (should find no vulnerabilities due to parameterized queries)
sqlmap -u "http://localhost:8000/api/v1/database/query" \
  --data='{"query":"SELECT * FROM users WHERE id=1"}' \
  --headers="Authorization: Bearer $TOKEN\nContent-Type: application/json" \
  --batch

# Expected: No SQL injection vulnerabilities found
```

**Result:** ✅ PASS / ❌ FAIL

---

### SCAN-03: Port Scanner

```bash
# Scan for open ports
nmap -sV localhost

# Expected: Only 8000 (or 80/443 in production) open
# No unnecessary services exposed
```

**Result:** ✅ PASS / ❌ FAIL

---

## Performance Impact Testing

### PERF-01: Sanitization Overhead

```bash
# Benchmark with sanitization
ab -n 10000 -c 100 -p payload.json -T application/json \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/vault/files

# payload.json contains normal text

# Record: Mean response time

# Expected: <1ms overhead compared to no sanitization
```

**Result:** ✅ PASS / ❌ FAIL

---

### PERF-02: Breach Detection Overhead

```bash
# Benchmark password changes
ab -n 100 -c 10 -p password-change.json -T application/json \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/change-password

# password-change.json contains password change request

# Record: Mean response time

# Expected: <100ms (first call), <1ms (cached)
```

**Result:** ✅ PASS / ❌ FAIL

---

## Test Results Summary

### Checklist

- [ ] TEST-01: Token expiration (1 hour)
- [ ] TEST-02: Token refresh flow
- [ ] TEST-03: Session fingerprinting
- [ ] TEST-04: Concurrent session limits
- [ ] TEST-05: Password breach detection
- [ ] TEST-06: Breach detection caching
- [ ] TEST-07: XSS prevention
- [ ] TEST-08: SQL injection detection
- [ ] TEST-09: Path traversal prevention
- [ ] TEST-10: OWASP security headers
- [ ] TEST-11: CORS enforcement
- [ ] TEST-12: Audit log encryption
- [ ] TEST-13: Connection pool performance
- [ ] TEST-14: Terminal shell validation
- [ ] SCAN-01: OWASP ZAP scan
- [ ] SCAN-02: SQL injection scan
- [ ] SCAN-03: Port scan
- [ ] PERF-01: Sanitization overhead
- [ ] PERF-02: Breach detection overhead

### Summary Report

**Total Tests:** 19
**Passed:** ___
**Failed:** ___
**Pass Rate:** ___%

**Critical Failures:** ___
**Blockers:** ___

**Recommendation:**
- ✅ APPROVED FOR PRODUCTION
- ⚠️ APPROVED WITH WARNINGS
- ❌ NOT APPROVED - FIX REQUIRED

---

## Continuous Security Testing

### Integration with CI/CD

Add to `.github/workflows/security.yml`:

```yaml
name: Security Tests

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run OWASP ZAP
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'http://localhost:8000'

      - name: Run Security Tests
        run: |
          pytest tests/security/ -v

      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: security-report
          path: zap-report.html
```

---

## Appendix: Testing Tools

### Required Tools

- **curl** - HTTP client
- **jq** - JSON processor
- **ab** (Apache Bench) - Load testing
- **sqlite3** - Database inspection
- **pytest** - Python testing
- **OWASP ZAP** - Security scanner
- **sqlmap** - SQL injection scanner (optional)
- **nmap** - Port scanner (optional)

### Installation

```bash
# macOS
brew install curl jq apache2 sqlite3
brew install nmap sqlmap  # Optional

# Ubuntu/Debian
sudo apt install curl jq apache2-utils sqlite3
sudo apt install nmap sqlmap  # Optional

# Python tools
pip install pytest pytest-asyncio
```

---

**Testing Status:** Ready for validation
**Last Updated:** 2025-12-16
**Test Coverage:** 100% of security features
