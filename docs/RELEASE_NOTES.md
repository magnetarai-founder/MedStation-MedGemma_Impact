# ElohimOS v1.0.0-rc1 Release Notes

**Release Date**: November 14, 2025
**Status**: Release Candidate 1

This is the first release candidate for ElohimOS v1.0.0, featuring comprehensive vault security, test coverage, and production-ready CI/CD.

---

## 🎯 Highlights

### Vault Security Hardening
- **Share Link Protection**: Per-token IP rate limiting (5/min, 50/day) prevents abuse
- **One-Time Links**: Single-use share links with automatic expiry
- **Default 24h TTL**: All share links expire after 24 hours unless specified
- **Consistent Error Codes**: Machine-readable error responses for all share operations

### Comprehensive Test Coverage
- **950+ lines** of test code across vault, auth, analytics, and pagination
- **Isolated test environment** with temporary data directories
- **Fixture-based architecture** for repeatable, reliable testing
- **FastAPI integration tests** using TestClient with lifespan support

### API Documentation
- **Complete API reference** (826 lines) covering all endpoints
- Request/response examples for every operation
- Rate limiting tables and error code reference
- Pagination contract specification

### CI/CD Pipeline
- **GitHub Actions workflow** for automated testing
- **Matrix testing**: Python 3.12 and 3.13
- **venv caching** for faster runs
- **PR comments** with test summaries
- **Coverage reports** with artifact retention

---

## 🚀 New Features

### Authentication
- **Forced Password Change Flow** - Users with temporary passwords must change them before accessing the system
  - Returns `403` with `AUTH_PASSWORD_CHANGE_REQUIRED` error code
  - Dedicated `/auth/change-password-first-login` endpoint
  - Audit logging of password changes

### Vault File Operations
- **Enhanced Rate Limiting** - Per-user+IP rate limits on all sensitive operations:
  - Downloads: 120 req/min
  - Comments: 60 req/min (all operations)
  - Versions: 60 req/min (list), 20 req/min (restore/delete)
  - Trash: 60 req/min (list/move), 30 req/min (restore), 5 req/min (empty)
  - Search: 60 req/min
  - Analytics: 120 req/min

- **Pagination Contract** - Consistent response structure across all list endpoints:
  ```json
  {
    "data": [...],
    "total": 127,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
  ```

- **Audit Logging** - Comprehensive audit trail for:
  - File downloads
  - Version restores/deletes
  - Trash operations
  - Comment changes
  - Share link creation/revocation
  - Metadata updates

### Share Links
- **One-Time Links** - `one_time` parameter automatically sets `max_downloads=1`
- **Default Expiry** - 24-hour TTL applied automatically if not specified
- **IP-Based Throttling** - Per-token rate limits prevent abuse:
  - 5 downloads/min per IP per token
  - 50 downloads/day per IP per token
- **Enhanced Error Handling** - Consistent error codes:
  - `invalid_token` (404) - Token not found or revoked
  - `expired` (410) - Share link has expired
  - `max_downloads_reached` (410) - Download limit reached
  - `password_required` (401) - Password needed
  - `password_incorrect` (401) - Wrong password
  - `rate_limited` (429) - Too many requests (includes `retry_after`)

### Analytics
- **Storage Trends** - Track vault usage over time (30-day default)
- **Access Patterns** - Hourly access distribution and top files
- **Activity Timeline** - Complete audit trail with action counts

### Per-User Model Preloader
- Models preloaded per user with 15-minute idle timeout
- LRU eviction (max 3 models)
- User preferences API for model selection
- Shared models between users requesting same model

---

## 🔧 Technical Improvements

### Backend
- **Router Registry** - Centralized router management with graceful failure handling
- **Config Paths** - Environment-configurable data directories (`ELOHIMOS_DATA_DIR`)
- **Database Consolidation** - 3 databases (was 7+): app.db, vault.db, datasets.db
- **Metal4 Engine** - Optimized inference on Apple Silicon

### Testing
- **Test Fixtures** - `conftest.py` with temp data dir isolation
- **Dependency Overrides** - Static test user for consistent auth
- **Coverage Reporting** - XML coverage with aggregation across suites
- **Test Organization** - Separate packages: vault, auth, analytics, smoke

### CI/CD
- **macOS Runners** - Required for Metal framework support
- **Matrix Testing** - Python 3.12 and 3.13
- **Smart Caching** - venv cached by Python version + requirements hash
- **Test Summaries** - Markdown summaries with pass/fail/skip counts
- **PR Integration** - Automatic test result comments on pull requests

---

## 📚 Documentation

### New Documentation
- **API Reference** (`docs/development/API_REFERENCE.md`) - Complete endpoint documentation
- **SETUP.md** - Updated with pytest instructions
- **Test Coverage** - Inline test documentation

### Updated Documentation
- Backend setup instructions
- Testing guidelines
- Development workflows

---

## 🔄 Migration Notes

### Database Changes
**Auto-applied, backward-compatible migration at startup.**

The following schema change is applied automatically on first startup (if needed):
- **`users.must_change_password`** column added (default: 0, non-breaking)
  - Enables forced password change flow for new users
  - Existing users unaffected (column defaults to 0)
  - No manual intervention required

Other new features use existing tables:
- Share link hardening uses existing `vault_file_shares` table
- Rate limiting uses in-memory token buckets (no persistence)
- Audit logging uses existing `vault_audit_logs` table

**Backward Compatibility**: 100% compatible. Rollback to previous versions is safe.

### Configuration Changes

#### Required for Production
Set these environment variables before deploying:

```bash
# Required in production
export ELOHIM_FOUNDER_PASSWORD="your-strong-password-here"

# Recommended for production
export ELOHIM_JWT_SECRET="your-random-32+-char-secret"
export ELOHIM_CORS_ORIGINS="https://yourdomain.com"
```

#### Optional Configuration
```bash
# Data directory (default: .neutron_data)
export ELOHIMOS_DATA_DIR="/path/to/data"

# Temp directories
export ELOHIMOS_TEMP_DIR="/path/to/temp"
export ELOHIMOS_EXPORTS_DIR="/path/to/exports"
```

### Breaking Changes
**None.** This release is fully backward-compatible with existing ElohimOS installations.

### New Behavior
- **Share links** created without `expires_at` now default to 24-hour expiry
- **Rate limiting** now enforced on vault endpoints (see API docs for limits)
- **Share access** now throttled per-token per-IP (5/min, 50/day)

---

## 🐛 Bug Fixes

- Fixed startup errors in Code Editor, Terminal, Vault, and model services
- Resolved route modularization issues in backend
- Fixed path shadowing in main.py
- Corrected import errors in various service modules

---

## 🧪 Testing

### Test Suites
- **Vault Lifecycle** - 3 test classes, 8+ test methods
- **Share Hardening** - 4 test classes for security features
- **Authentication** - 3 test methods for password change flow
- **Analytics** - 2 test classes for analytics endpoints
- **Pagination** - 4 test classes for pagination contract

### Test Coverage
```
vault/           - File operations, comments, versions, trash, sharing
auth/            - Password change flow, login enforcement
analytics/       - Storage trends, access patterns, activity timeline
smoke/           - Import validation, router registry
```

### Running Tests
```bash
cd apps/backend
source venv/bin/activate

# All tests
pytest tests/ -v

# Specific suites
pytest tests/vault/ -v
pytest tests/auth/ -v
pytest tests/analytics/ -v

# With coverage
pytest tests/ -v --cov=api --cov-report=term
```

---

## 🔒 Security

### Enhancements
- Per-token IP rate limiting on share downloads
- Token redaction in logs (prefix only)
- Audit logging without sensitive data leakage
- Forced password change flow enforcement
- PBKDF2 password hashing (600,000 iterations)

### Security Checklist
- ✅ Rate limiting on all sensitive endpoints
- ✅ Audit logging for critical operations
- ✅ Share link expiry and download limits
- ✅ IP-based abuse prevention
- ✅ Password strength enforcement
- ✅ JWT token expiry (7 days default)
- ✅ Refresh tokens (30 days)

---

## 📊 Performance

### Optimizations
- venv caching in CI (faster test runs)
- Model preloading with LRU eviction
- Database connection pooling
- Metal4 acceleration for inference

### Benchmarks
Performance benchmarking with Locust recommended for production deployments.

---

## 🙏 Acknowledgments

This release includes contributions and testing from the ElohimOS development team.

**Generated with Claude Code**
Co-Authored-By: Claude <noreply@anthropic.com>

---

## 📝 Changelog

For a complete list of changes, see:
- Commit `7f368454` - Test Coverage (Batch A)
- Commit `947b5489` - Share Hardening (Batch B)
- Commit `29c99f1a` - API Documentation (Batch C)
- Commit `82b90598` - CI Workflow (Batch D)

---

## 🚦 What's Next?

### v1.0.0 Roadmap
- Performance benchmarking with Locust
- Additional analytics dashboards
- Enhanced team collaboration features
- Mobile app development

### Contributing
See `docs/development/ONBOARDING.md` for contribution guidelines.

---

## 📞 Support

- **Issues**: https://github.com/hipps-joshua/ElohimOS/issues
- **Documentation**: `/docs`
- **API Reference**: `docs/development/API_REFERENCE.md`
