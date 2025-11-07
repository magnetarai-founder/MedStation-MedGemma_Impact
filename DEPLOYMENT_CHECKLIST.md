# ElohimOS Production Deployment Checklist

**Status:** ✅ Ready for Production Deployment  
**Date:** 2025-11-07  
**Security Hardening:** Complete

---

## Pre-Deployment Verification Summary

### ✅ Security Configuration

#### JWT Secret Management
- **Location:** `apps/backend/api/auth_middleware.py:33-42`
- **Status:** ✅ Properly configured with environment checks
- **Dev Mode:** Falls back to ephemeral secret with clear warning
- **Production:** Requires `ELOHIM_JWT_SECRET` env var (fails fast if missing)
- **Action Required:** Set `ELOHIM_JWT_SECRET` to a secure random value in production

```bash
export ELOHIM_JWT_SECRET=$(openssl rand -base64 32)
```

#### Founder Rights Account
- **Location:** `apps/backend/api/auth_middleware.py:47-50`
- **Status:** ✅ Requires `ELOHIM_FOUNDER_PASSWORD` in production
- **Dev Mode:** Uses dev default with security warnings
- **Production:** Must set custom password via env var
- **Action Required:** Set strong password for field support access

```bash
export ELOHIM_FOUNDER_PASSWORD="your-secure-password-here"
export ELOHIM_FOUNDER_USERNAME="elohim_founder"  # Optional, defaults to elohim_founder
```

#### Permission System
- **Terminal Endpoints:** ✅ Protected with `@require_perm("code.terminal")`
- **Code Operations:** ✅ All write/delete operations require permissions
- **Absolute Paths:** ✅ Restricted to workspace only (stricter boundary)
- **Path Validation:** ✅ Uses resolve() + relative_to() for canonicalization

#### Rate Limiting
- **Write Operations:** 30 requests/minute per user
- **Delete Operations:** 20 requests/minute per user
- **Implementation:** Token bucket algorithm in `code_operations.py`

---

### ✅ Cross-Platform Robustness

#### File Locking
- **Unix/Linux/macOS:** fcntl-based locking
- **Windows:** msvcrt-based locking with safe import fallback
- **Location:** `apps/backend/api/agent/engines/codex_engine.py:20-24, 51-61`

#### AI Engine Fallbacks
- **Aider:** ✅ Falls back to PATH if not in venv, clear error if missing
- **Continue:** ✅ Standardized to stdin (no argv length limits)
- **Location:** `apps/backend/api/agent/engines/aider_engine.py:43-57`

---

### ✅ Model & Engine Availability

#### Ollama Status
```
✅ Running on localhost:11434
✅ Models available:
   - phi3.5:3.8b (2.0 GB)
   - qwen2.5-coder:14b (8.4 GB)
```

#### Aider CLI
```
✗ Not in PATH (optional engine)
```
**To Install:** `pip install aider-chat`

#### Continue CLI
```
✅ Found at /Users/indiedevhipps/.npm-global/bin/cn
```

---

### ✅ Data Directory Structure

**Location:** `.neutron_data/`

**Existing Databases:**
- `audit.db` (40 KB) - Audit logging
- `elohimos_app.db` (260 KB) - Main application database
- `teams.db` (116 KB) - Teams and collaboration
- `workflows.db` (112 KB) - Workflow definitions
- `docs.db` (28 KB) - Documentation
- `learning.db` (20 KB) - Learning system
- `project_library.db` (12 KB) - Project library

**Created on First Use:**
- `unified_context.db` - Agent context management
- `workspace_sessions.db` - Workspace session tracking

**Subdirectories:**
- `code_workspaces/` - User workspace isolation
- `datasets/` - Dataset storage
- `memory/` - Memory subsystem
- `uploads/` - File uploads
- `insights/` - Analytics and insights

---

### ✅ CORS Configuration

**Location:** `apps/backend/api/main.py:242-267`

**Default Allowed Origins:**
- `http://localhost:4200` (Angular dev server)
- `http://localhost:4201` (Angular fallback)
- `http://localhost:5173-5175` (Vite dev servers)
- `http://127.0.0.1:4200` (IPv4 localhost)
- `http://127.0.0.1:5173-5175` (Vite IPv4 localhost)
- `http://localhost:3000` (General fallback)

**Production Override:**
```bash
export ELOHIM_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

---

## Deployment Steps

### 1. Environment Variables (Production)

Create `.env` file or set system environment:

```bash
# Required
export ELOHIM_ENV=production
export ELOHIM_JWT_SECRET=$(openssl rand -base64 32)
export ELOHIM_FOUNDER_PASSWORD="your-secure-password"

# Optional
export ELOHIM_FOUNDER_USERNAME="elohim_founder"
export ELOHIM_CORS_ORIGINS="https://yourdomain.com"
```

### 2. Install AI Engines (Optional)

```bash
# Activate venv
source venv/bin/activate

# Install Aider (optional)
pip install aider-chat

# Install Continue CLI (optional, already available system-wide)
npm install -g continue
```

### 3. Verify Ollama

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull required models if missing
ollama pull qwen2.5-coder:14b
ollama pull phi3.5:3.8b
```

### 4. Backup Data Directory

```bash
# Create backup before first production run
tar -czf neutron_data_backup_$(date +%Y%m%d).tar.gz .neutron_data/
```

### 5. Start Services

```bash
# Development mode (uses start_web.sh)
./elohim

# Production mode (set env first)
export ELOHIM_ENV=production
export ELOHIM_JWT_SECRET="your-secret-here"
./elohim
```

**Expected Output:**
- Backend starts on `http://localhost:8000`
- Vite dev server starts on `http://localhost:4200` (or fallback port)
- Both services should start without errors

---

## Post-Deployment Validation

### 1. Capabilities Endpoint

```bash
curl http://localhost:8000/api/v1/agent/capabilities
```

**Expected Response:**
```json
{
  "ollama": {
    "available": true,
    "models": ["qwen2.5-coder:14b", "phi3.5:3.8b"],
    "url": "http://localhost:11434"
  },
  "aider": {
    "available": false,
    "message": "Install via: pip install aider-chat"
  },
  "continue": {
    "available": true,
    "binary": "/Users/indiedevhipps/.npm-global/bin/cn"
  }
}
```

### 2. Permission Enforcement

**Test 1: Terminal spawn without permission (should fail 403)**
```bash
# Authenticate as non-privileged user
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json"

# Expected: 403 Forbidden (missing code.terminal permission)
```

**Test 2: Terminal spawn with permission (should succeed)**
```bash
# Authenticate as admin or user with code.terminal permission
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"

# Expected: 200 OK with terminal session details
```

### 3. Absolute Path Restrictions

**Test 1: Access file outside workspace (should fail 403)**
```bash
curl http://localhost:8000/api/v1/code/tree?absolute_path=/etc/passwd \
  -H "Authorization: Bearer <token>"

# Expected: 403 Forbidden (outside workspace)
```

**Test 2: Access file in workspace (should succeed)**
```bash
curl http://localhost:8000/api/v1/code/tree?absolute_path=/path/to/workspace/file \
  -H "Authorization: Bearer <token>"

# Expected: 200 OK with file tree
```

### 4. Rate Limiting

**Test: Burst write operations**
```bash
# Send 35 write requests rapidly (limit is 30/min)
for i in {1..35}; do
  curl -X POST http://localhost:8000/api/v1/code/write \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d "{\"path\":\"test_$i.txt\",\"content\":\"test\"}" &
done
wait

# Expected: First 30 succeed (200 OK), remaining 5 fail (429 Too Many Requests)
```

### 5. Patch Flow (Dry Run)

**Step 1: Generate plan**
```bash
curl -X POST http://localhost:8000/api/v1/agent/plan \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"description":"Add a hello function","files":["test.py"]}'

# Expected: 200 OK with plan details
```

**Step 2: Apply with dry_run**
```bash
curl -X POST http://localhost:8000/api/v1/agent/apply \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"<from-step-1>","dry_run":true}'

# Expected: 200 OK with diff preview (no files modified)
```

### 6. CORS Validation

**Browser Test:**
1. Open browser to `http://localhost:4200`
2. Open DevTools Console
3. Verify no CORS errors in console
4. Check Network tab - API requests should succeed with proper headers

**Expected CORS Headers:**
```
Access-Control-Allow-Origin: http://localhost:4200
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

---

## Security Hardening Summary

### Critical Fixes Applied (Commits)

1. **ed9f10f0** - Fix permission bypass and arbitrary file access
   - Added `@require_perm` to terminal spawn endpoints
   - Restricted absolute path access with validation

2. **79d0ded2** - Add cross-platform support and rate limiting
   - Implemented fcntl/msvcrt file locking
   - Added 30/min write, 20/min delete rate limits

3. **f7fb3b0c** - Use try/except for fcntl import (Windows safety)
   - Prevents import-time crashes on Windows

4. **7440ca40** - Tighten absolute path policy (workspace only)
   - Removed home directory from allowed roots
   - Standardized Continue to use stdin

### Security Posture

✅ **Zero known critical vulnerabilities**  
✅ **Permission-based access control on all sensitive endpoints**  
✅ **Path traversal prevention with canonicalization**  
✅ **Rate limiting on destructive operations**  
✅ **Cross-platform file locking**  
✅ **Fail-fast on missing production secrets**  
✅ **Clear security warnings in dev mode**  
✅ **Audit logging for all sensitive operations**

---

## Nice-to-Have Next Steps

### UI Enhancements
- Wire capabilities endpoint into Assist UI
- Grey out unavailable engines with remediation hints
- Show install commands for missing dependencies

### Logging & Retention
- Implement log rotation for server logs
- Configure periodic pruning for audit.db (90-day retention already implemented)
- Consider archival strategy for unified_context.db if usage is heavy

### Monitoring
- Add health check endpoint (`/api/v1/health`)
- Monitor rate limit hit rates
- Track patch application success/failure rates
- Alert on repeated permission denials (potential attacks)

### Documentation
- Create user guide for workspace management
- Document RBAC permission model
- Add troubleshooting guide for common deployment issues

---

## Quick Reference

**Start Services:**
```bash
./elohim
```

**Check Logs:**
```bash
tail -f logs/backend.log  # If log files are configured
# Or check console output
```

**Verify Backend:**
```bash
curl http://localhost:8000/health
```

**Verify Ollama:**
```bash
curl http://localhost:11434/api/tags
```

**Check Capabilities:**
```bash
curl http://localhost:8000/api/v1/agent/capabilities
```

**Backup Data:**
```bash
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz .neutron_data/
```

---

## Support & Troubleshooting

### Backend Won't Start

**Issue:** Missing ELOHIM_JWT_SECRET in production
```
RuntimeError: ELOHIM_JWT_SECRET environment variable is required
```

**Fix:**
```bash
export ELOHIM_JWT_SECRET=$(openssl rand -base64 32)
./elohim
```

### Ollama Not Responding

**Issue:** Models not available in capabilities
```json
{"ollama": {"available": false}}
```

**Fix:**
```bash
# Start Ollama
ollama serve

# Pull required models
ollama pull qwen2.5-coder:14b
```

### CORS Errors in Browser

**Issue:** Browser console shows CORS policy errors

**Fix:**
```bash
# Add your frontend URL to CORS origins
export ELOHIM_CORS_ORIGINS="http://localhost:4200,http://localhost:5173"
./elohim
```

### Permission Denied on Terminal Spawn

**Issue:** 403 Forbidden when accessing /api/v1/terminal/spawn

**Expected Behavior:** This is correct - requires `code.terminal` permission

**Fix:** Grant the user `code.terminal` permission via admin panel

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-07  
**Prepared By:** Claude Code (Security Hardening Session)
