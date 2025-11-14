# ElohimOS {{VERSION}} — Release Notes

**Release Date**: {{DATE}}
**Tag**: `{{TAG}}`

---

## 🎯 Highlights

<!-- Replace with key highlights for this release -->
- 🔐 **Enhanced Security**: Share link IP throttling, one-time links, default 24h TTL
- ✅ **Comprehensive Testing**: 950+ lines of test coverage across vault, auth, analytics
- 📚 **Complete API Documentation**: Full endpoint reference with rate limits and error codes
- 🚀 **Production Ready**: CI/CD pipeline, smoke tests, load testing scenarios
- 🔧 **Database Consolidation**: Streamlined to 3 DBs with auto-applied migrations

---

## 📋 Changes

See the complete changelog:
- **Changelog**: [{{VERSION}}]({{CHANGELOG_ANCHOR}})
- **Commit Range**: `{{FROM_TAG}}..{{TAG}}`

### Key Features
<!-- Auto-populated from conventional commits -->
- Vault security hardening (IP throttles, one-time links, TTL defaults)
- Forced password change flow with PBKDF2
- Per-user model preloader
- Terminal socket bridge
- Comprehensive rate limiting

### Key Fixes
<!-- Auto-populated from conventional commits -->
- Backend startup errors resolved
- Router registry centralized

---

## 🔌 API Additions

Full API reference available at [docs/development/API_REFERENCE.md](docs/development/API_REFERENCE.md).

### New Endpoints
- `POST /api/v1/auth/change-password-first-login` - Forced password change
- `POST /api/v1/terminal/socket/start` - Terminal bridge
- `GET /api/v1/vault/analytics/*` - Storage trends, access patterns, activity timeline

### Enhanced Endpoints
- All vault endpoints now include rate limiting
- Share endpoints with IP throttling
- Pagination contract across list endpoints

---

## 🔒 Security Notes

### Rate Limiting
- **Vault Operations**: 120 req/min (downloads), 60 req/min (comments/versions)
- **Share Links**: 5 req/min per IP per token, 50 req/day per IP per token
- **429 Responses**: Include `retry_after` header

### Share Link Protection
- **One-Time Links**: `one_time` parameter sets `max_downloads=1`
- **Default TTL**: 24-hour expiry applied automatically
- **IP-Based Throttling**: Per-token rate limits prevent abuse

### Token Redaction
- Share tokens logged as prefix only (`token[:6]...`)
- Passwords never logged
- JWT tokens never logged in full

### Audit Logging
- File downloads, version restores/deletes
- Trash operations, comment changes
- Share link creation/revocation
- Metadata updates

---

## 🚀 Operations

### Go-Live Checklist
See [docs/deployment/GO_LIVE_CHECKLIST.md](docs/deployment/GO_LIVE_CHECKLIST.md) for complete 5-minute validation guide.

**Quick Start**:
```bash
# Required env vars
export ELOHIM_FOUNDER_PASSWORD="your-strong-password"
export ELOHIM_JWT_SECRET="$(openssl rand -base64 48)"
export ELOHIM_CORS_ORIGINS="https://yourdomain.com"

# Start with proxy headers (if behind proxy)
uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips='*'
```

### Smoke Testing
```bash
python3 scripts/smoke_test_production.py --host http://localhost:8000
```

### Load Testing
```bash
locust -f apps/backend/locustfile.py --host http://localhost:8000
```

### Production Readiness
See [docs/deployment/PRODUCTION_READINESS.md](docs/deployment/PRODUCTION_READINESS.md) for complete checklist:
- Environment variables (secrets, CORS, paths)
- Backup strategy (automated daily, 30-day retention)
- Monitoring & alerting (Prometheus, Grafana)
- Security hardening (rate limits, encryption, PBKDF2)

---

## 🔄 Migration Notes

### Database Changes
**Auto-applied, backward-compatible migrations run on startup.**

- `users.must_change_password` column added (default: 0, non-breaking)
- Migration runner: `apps/backend/api/db_init.py`
- No manual intervention required

### Backward Compatibility
- 100% compatible with previous versions
- Rollback to previous versions is safe
- No breaking changes to API contracts

### New Behavior
- Share links without `expires_at` default to 24-hour expiry
- Rate limiting enforced on vault endpoints
- Share access throttled per-token per-IP (5/min, 50/day)

---

## 📊 Performance

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

## 🧪 Testing

### Test Coverage
```bash
cd apps/backend
source venv/bin/activate
pytest tests/ -v --cov=api --cov-report=term
```

### Test Suites
- **Vault**: File operations, comments, versions, trash, sharing (8+ tests)
- **Auth**: Password change flow, login enforcement (3 tests)
- **Analytics**: Storage trends, access patterns, activity timeline (2 test classes)
- **Pagination**: Pagination contract validation (4 test classes)

---

## 📞 Support

- **Issues**: https://github.com/hipps-joshua/ElohimOS/issues
- **Documentation**: `/docs`
- **API Reference**: [docs/development/API_REFERENCE.md](docs/development/API_REFERENCE.md)

---

## 🙏 Contributors

This release includes contributions and testing from the ElohimOS development team.

**Generated with Claude Code**
Co-Authored-By: Claude <noreply@anthropic.com>

---

## 📝 Placeholders to Replace

Before publishing, replace these placeholders:
- `{{VERSION}}` - Version number (e.g., v1.0.0)
- `{{TAG}}` - Git tag (e.g., v1.0.0)
- `{{DATE}}` - Release date (e.g., 2025-11-14)
- `{{FROM_TAG}}` - Previous tag for commit range (e.g., v0.9.0)
- `{{CHANGELOG_ANCHOR}}` - Link to changelog section (e.g., `changelog/CHANGELOG.md#v100---2025-11-14`)
