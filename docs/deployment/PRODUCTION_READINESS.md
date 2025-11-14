# ElohimOS Production Readiness Checklist

Complete checklist for deploying ElohimOS v1.0.0-rc1 to production.

**Last Updated**: 2025-11-14
**Version**: 1.0.0-rc1

---

## ✅ Pre-Deployment Checklist

### 1. Environment Variables

#### Required (Production)
- [ ] `ELOHIM_FOUNDER_PASSWORD` - Strong password (20+ characters, mixed case, numbers, symbols)
  ```bash
  export ELOHIM_FOUNDER_PASSWORD="$(openssl rand -base64 32)"
  ```

#### Recommended (Production)
- [ ] `ELOHIM_JWT_SECRET` - Random 32+ character secret for JWT signing
  ```bash
  export ELOHIM_JWT_SECRET="$(openssl rand -base64 48)"
  ```

- [ ] `ELOHIM_CORS_ORIGINS` - Lock down allowed origins (scheme + host, no wildcards)
  ```bash
  export ELOHIM_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
  # CRITICAL: Must include https:// scheme, NO wildcards (*)
  ```

#### Optional (Recommended)
- [ ] `ELOHIMOS_DATA_DIR` - Custom data directory path
  ```bash
  export ELOHIMOS_DATA_DIR="/var/lib/elohimos/data"
  ```

- [ ] `ELOHIMOS_TEMP_DIR` - Temp files directory
  ```bash
  export ELOHIMOS_TEMP_DIR="/var/lib/elohimos/temp"
  ```

- [ ] `ELOHIMOS_EXPORTS_DIR` - Exports directory
  ```bash
  export ELOHIMOS_EXPORTS_DIR="/var/lib/elohimos/exports"
  ```

---

### 2. Secrets Management

#### macOS Keychain
- [ ] Verify founder password stored in Keychain (optional, but recommended for macOS deployments)
  ```bash
  security add-generic-password -s "ElohimOS" -a "founder" -w "your-password"
  ```

- [ ] Test Keychain access
  ```bash
  security find-generic-password -s "ElohimOS" -a "founder" -w
  ```

#### Environment File
- [ ] Create `.env` file with secrets (development only, not for production servers)
- [ ] Set proper permissions: `chmod 600 .env`
- [ ] Never commit `.env` to git (verify `.gitignore`)

#### Production Secret Management
- [ ] Use secure secret management service (AWS Secrets Manager, Vault, etc.)
- [ ] Rotate secrets regularly (90-day rotation recommended)
- [ ] Document secret rotation procedures

---

### 3. CORS Configuration

- [ ] Lock down CORS origins for production
  ```python
  # DO NOT use "*" in production
  ELOHIM_CORS_ORIGINS="https://yourdomain.com"
  ```

- [ ] Test CORS from allowed origins
- [ ] Verify OPTIONS preflight requests work
- [ ] Test cross-origin requests with credentials

---

### 4. Database Backups

#### Backup Strategy
- [ ] Implement automated daily backups
- [ ] Test backup creation
  ```bash
  # Backup all databases
  tar -czf elohimos_backup_$(date +%Y%m%d).tar.gz .neutron_data/
  ```

- [ ] Test backup restoration on fresh temp directory
  ```bash
  # Test restore
  mkdir /tmp/elohimos_restore_test
  tar -xzf elohimos_backup_20251114.tar.gz -C /tmp/elohimos_restore_test
  ```

- [ ] Verify restored data integrity
- [ ] Document backup retention policy (recommended: 30 days daily, 12 months monthly)

#### Backup Locations
- [ ] `.neutron_data/elohimos_app.db` - Main application database
- [ ] `.neutron_data/vault.db` - Vault database (encrypted files metadata)
- [ ] `.neutron_data/datasets/datasets.db` - Datasets database
- [ ] `.neutron_data/memory/chat_memory.db` - Chat memory database
- [ ] `.neutron_data/vault_files/` - Encrypted file storage

---

### 5. Logging Configuration

#### Log Levels
- [ ] Set appropriate log levels for production
  ```python
  # INFO for rate limits and share errors (not noisy)
  # ERROR for critical failures
  # DEBUG disabled in production
  ```

- [ ] Verify rate limit 429s log at INFO level
- [ ] Verify share link errors log at INFO level
- [ ] Confirm sensitive data (tokens, passwords) are redacted

#### Log Rotation
- [ ] Configure log rotation (logrotate or similar)
- [ ] Set max log size (e.g., 100MB per file)
- [ ] Retain logs for compliance period (e.g., 90 days)

#### Sensitive Data Redaction
- [ ] Verify share tokens logged as prefix only (`token[:6]...`)
- [ ] Verify passwords never logged
- [ ] Verify JWT tokens never logged in full
- [ ] Check audit logs don't contain sensitive data

---

### 6. Security Hardening

#### Rate Limiting
- [ ] Verify rate limits enforced on all endpoints (see API_REFERENCE.md)
- [ ] Test rate limit responses (429 with retry_after)
- [ ] Monitor rate limit metrics
- [ ] Verify client IPs preserved (requires --proxy-headers if behind proxy)

#### Share Link Security
- [ ] Verify IP throttles active (5/min, 50/day per token)
- [ ] Test one-time link behavior
- [ ] Verify default 24h TTL applied
- [ ] Test expired share link handling
- [ ] Confirm client IP detection works for per-IP throttles

#### Authentication
- [ ] Verify forced password change flow works
- [ ] Test JWT token expiry (7 days default)
- [ ] Test refresh token flow (30 days)
- [ ] Verify founder rights access restricted

#### Encryption
- [ ] Verify vault files encrypted at rest
- [ ] Test zero-knowledge architecture (server can't decrypt)
- [ ] Verify PBKDF2 password hashing (600k iterations)

---

### 7. Performance Optimization

#### Model Preloader
- [ ] Verify per-user model preloading active
- [ ] Test 15-minute idle timeout
- [ ] Monitor memory usage with 3 models loaded
- [ ] Test LRU eviction behavior

#### Database
- [ ] Run VACUUM on all databases
  ```bash
  sqlite3 .neutron_data/elohimos_app.db "VACUUM;"
  sqlite3 .neutron_data/vault.db "VACUUM;"
  ```

- [ ] Verify indexes exist on critical tables
- [ ] Monitor query performance (slow query log)

#### Metal4 Acceleration
- [ ] Verify Metal frameworks installed (macOS only)
  ```bash
  python -c "import Metal; print('Metal OK')"
  ```

- [ ] Test GPU acceleration for embeddings
- [ ] Monitor GPU utilization

---

### 8. Monitoring & Alerting

#### Health Checks
- [ ] Implement `/health` endpoint
- [ ] Monitor database connectivity
- [ ] Monitor disk space (alert at 80% full)
- [ ] Monitor memory usage

#### Metrics to Track
- [ ] Request rate (requests/second)
- [ ] Error rate (5xx responses)
- [ ] Response latency (P50, P95, P99)
- [ ] Rate limit triggers (429 responses)
- [ ] Share link creation/access
- [ ] Database size growth
- [ ] Model loading times

#### Alerting Rules
- [ ] Alert on error rate > 1%
- [ ] Alert on P95 latency > 1s
- [ ] Alert on disk usage > 80%
- [ ] Alert on database corruption
- [ ] Alert on failed backups

---

### 9. Testing

#### Integration Tests
- [ ] Run full test suite
  ```bash
  cd apps/backend
  source venv/bin/activate
  pytest tests/ -v --cov=api --cov-report=term
  ```

- [ ] Verify all tests pass
- [ ] Review coverage report (target: >80%)

#### Smoke Tests
- [ ] Test user registration/login
- [ ] Test vault upload/download
- [ ] Test share link creation/access
- [ ] Test forced password change flow
- [ ] Test rate limiting (manually trigger 429)
- [ ] Test analytics endpoints

#### Load Testing (Recommended)
- [ ] Install Locust for load testing
  ```bash
  pip install locust
  ```

- [ ] Create Locust scenarios:
  - File upload (10 users, 1 file/sec)
  - File download (50 users, 5 files/sec)
  - Search (20 users, 2 searches/sec)
  - Analytics (10 users, 1 request/sec)

- [ ] Run load test and record baseline:
  - P50 latency
  - P95 latency
  - P99 latency
  - Max throughput
  - Error rate

- [ ] Save results to `docs/performance/baseline_v1.0.0-rc1.md`

---

### 10. Documentation

- [ ] Update deployment docs with production config
- [ ] Document secret rotation procedures
- [ ] Document backup/restore procedures
- [ ] Document incident response procedures
- [ ] Create runbook for common operations

---

### 11. Legal & Compliance

- [ ] Review data retention policies
- [ ] Verify GDPR compliance (if applicable)
- [ ] Update privacy policy
- [ ] Update terms of service
- [ ] Document data deletion procedures

---

### 12. Rollback Plan

- [ ] Document rollback procedure
- [ ] Test database schema backward compatibility
- [ ] Create rollback script
- [ ] Document version downgrade steps
- [ ] Identify breaking changes (none for v1.0.0-rc1)

---

## 🚀 Deployment Steps

### 1. Pre-Deployment
```bash
# 1. Backup current production data
tar -czf elohimos_backup_pre_v1.0.0-rc1.tar.gz .neutron_data/

# 2. Set environment variables
export ELOHIM_ENV=production
export ELOHIM_FOUNDER_PASSWORD="your-secure-password"
export ELOHIM_JWT_SECRET="your-jwt-secret"
export ELOHIM_CORS_ORIGINS="https://yourdomain.com"

# 3. Verify dependencies
cd apps/backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Deployment
```bash
# 4. Run database migrations (none for v1.0.0-rc1)
# No migrations needed - fully backward compatible
# Note: users.must_change_password column auto-applied at startup

# 5. Start server
# If behind proxy (nginx, ALB, etc.): add --proxy-headers --forwarded-allow-ips='*'
uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips='*'

# Without proxy (direct access):
# uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 6. Verify startup logs
# Look for "✓ Services: Chat API, Users API, Team API, Vault API..."
```

### 3. Post-Deployment Validation
```bash
# 7. Test health endpoint
curl http://localhost:8000/api/v1/health

# 8. Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=founder&password=your-password"

# 9. Run smoke tests
pytest tests/smoke/ -v

# 10. Monitor logs for errors
tail -f logs/elohimos.log
```

---

## 📊 Performance Baselines

### Expected Performance (M1 Mac, 16GB RAM)
- File upload (1MB): <200ms
- File download (1MB): <150ms
- Search (100 files): <100ms
- Analytics query: <300ms
- Model loading (first): <5s
- Model inference (cached): <100ms

### Resource Usage
- Memory (idle): ~500MB
- Memory (3 models loaded): ~4.5GB
- Disk (fresh install): ~100MB
- Disk (with models): ~10GB

---

## 🐛 Troubleshooting

### Common Issues

**JWT Secret Errors**
```bash
# Verify JWT secret is set
echo $ELOHIM_JWT_SECRET

# Regenerate if needed
export ELOHIM_JWT_SECRET="$(openssl rand -base64 48)"
```

**Founder Password Errors**
```bash
# Development mode (uses default password)
export ELOHIM_ENV=development

# Production mode (requires ELOHIM_FOUNDER_PASSWORD)
export ELOHIM_FOUNDER_PASSWORD="your-secure-password"
```

**Metal Framework Errors** (macOS)
```bash
# Install Metal frameworks
pip install pyobjc-framework-Metal \
  pyobjc-framework-MetalPerformanceShaders \
  pyobjc-framework-MetalPerformanceShadersGraph
```

**Database Locked**
```bash
# Check for stale connections
lsof | grep elohimos_app.db

# Kill stale processes if needed
pkill -f uvicorn
```

---

## 📞 Support

- **Issues**: https://github.com/hipps-joshua/ElohimOS/issues
- **Documentation**: `/docs`
- **API Reference**: `docs/development/API_REFERENCE.md`

---

## ✅ Final Checklist

Before going live:

- [ ] All secrets set and strong
- [ ] CORS locked down
- [ ] Backups tested and automated
- [ ] Logs configured and rotating
- [ ] Rate limits verified
- [ ] Security hardening complete
- [ ] Monitoring and alerts active
- [ ] Tests passing (100%)
- [ ] Load testing complete
- [ ] Documentation updated
- [ ] Rollback plan ready

**Sign-off**: _________________  Date: _________

---

**Generated with Claude Code**
Co-Authored-By: Claude <noreply@anthropic.com>
