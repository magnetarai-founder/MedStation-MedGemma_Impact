# ElohimOS Enhancement Implementation Plan

**Date Created**: November 9, 2025
**Status**: In Progress - Sprint 1 Nearly Complete
**Priority**: High-Impact Quick Wins First

---

## 📊 Current Progress Overview

### ✅ Completed (5/8 Sprint 1 Tasks)

1. **API Documentation System** ✨
   - FastAPI Swagger UI at `/api/docs`
   - ReDoc alternative at `/api/redoc`
   - OpenAPI schema at `/api/openapi.json`
   - Comprehensive platform description with auth guide
   - **Impact**: Improved developer experience, API discoverability

2. **Model Auto-Loading** 🔥
   - `ModelManager.get_favorites()` method implemented
   - Startup hook preloads hot slot models (1-4)
   - Graceful failure handling (app continues if models fail)
   - **Impact**: Faster startup, better UX for switching models

3. **Unified Configuration System** ⚙️
   - 519-line `config.py` with Pydantic BaseSettings
   - 50+ settings with validation
   - Environment variable support (ELOHIMOS_* prefix)
   - Apple Silicon auto-detection
   - Backwards compatible with existing code
   - **Impact**: Centralized config, easier deployment, better validation

4. **Comprehensive .env Documentation** 📝
   - Updated `.env.example` with all 50+ settings
   - 3 deployment examples (high/medium/low RAM)
   - Security best practices documented
   - Performance tuning guidelines
   - **Impact**: Easier onboarding, production deployment ready

5. **Hardcoded Path Removal (Partial)** 🗂️
   - Fixed main.py (3 locations)
   - Unified config paths working
   - **Impact**: More flexible deployment, easier testing

### 🔄 In Progress (3/8 Sprint 1 Tasks)

6. **Remove Remaining Hardcoded Paths** - 85% Complete
   - Remaining: 7 files with legacy paths

7. **Form Field Accessibility** - 2% Complete
   - Fixed: 1 of ~50 input elements

8. **Error Messages & Codes** - Not Started

---

## 🎯 Sprint 1 Completion Plan (Immediate)

### Task 6: Complete Hardcoded Path Removal

**Estimated Time**: 30-45 minutes
**Priority**: HIGH - Technical debt reduction
**Complexity**: LOW - Straightforward find/replace

#### Files Requiring Updates:

1. **`panic_mode.py`** (2 locations)
   ```python
   # Line 117: Path("/tmp/omnistudio_cache")
   # Line 197: Path.home() / ".omnistudio" / "panic_log.txt"
   ```
   **Fix**: Use `settings.cache_dir` and `settings.data_dir / "panic_log.txt"`

2. **`ollama_config.py`** (1 location)
   ```python
   # Line 64: Path.home() / ".omnistudio" / "ollama_config.json"
   ```
   **Fix**: Use `settings.data_dir / "ollama_config.json"`

3. **`ane_router.py`** (1 location)
   ```python
   # Line 206: Path.home() / ".omnistudio" / "router.mlmodel"
   ```
   **Fix**: Use `settings.data_dir / "router.mlmodel"`

4. **`jarvis_memory.py`** (1 location)
   ```python
   # Line 66: Path.home() / ".omnistudio"
   ```
   **Fix**: Use `settings.data_dir`

5. **`learning_system.py`** (1 location)
   ```python
   # Line 86: Path.home() / ".omnistudio" / "learning.db"
   ```
   **Fix**: Use `settings.data_dir / "learning.db"`

6. **`offline_data_sync.py`** (1 location)
   ```python
   # Line 653: Path.home() / ".omnistudio" / "omnistudio.db"
   ```
   **Fix**: Use `settings.app_db`

#### Implementation Steps:

1. **Import unified config** in each file:
   ```python
   try:
       from .config import get_settings
   except ImportError:
       from config import get_settings

   settings = get_settings()
   ```

2. **Replace hardcoded paths** with settings properties

3. **Test each file** - ensure no import errors

4. **Commit with descriptive message**:
   ```bash
   git commit -m "refactor: Complete hardcoded path removal across remaining files"
   ```

---

### Task 7: Form Field Accessibility Enhancement

**Estimated Time**: 2-3 hours (systematic approach)
**Priority**: MEDIUM - UX/Accessibility improvement
**Complexity**: MEDIUM - Repetitive but important

#### Overview:
- ~50 input elements missing `id` and `name` attributes
- Affects browser autofill, screen readers, form validation
- Non-blocking (forms work fine, just missing semantic attributes)

#### Files Requiring Updates:

**Settings Components** (Primary Focus):
1. `PowerUserTab.tsx` - 4 inputs remaining
2. `SettingsTab.tsx` - 25 inputs
3. `AdvancedTab.tsx` - Unknown count
4. `ChatTab.tsx` - Unknown count
5. `ModelsTab.tsx` - Unknown count

**Other Components** (Secondary):
- Form builders, editors, modals - ~20+ inputs

#### Implementation Strategy:

**Option A: Manual Systematic Fix** (Recommended for quality)
```tsx
// Before:
<input
  type="checkbox"
  checked={setting.value}
  onChange={handler}
/>

// After:
<input
  id="setting_name"
  name="setting_name"
  type="checkbox"
  checked={setting.value}
  onChange={handler}
/>
```

**Option B: Create Reusable Component**
```tsx
// Create: src/components/ui/FormInput.tsx
interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const FormInput: React.FC<FormInputProps> = ({
  id,
  name,
  label,
  error,
  ...props
}) => {
  const inputId = id || name || `input-${Math.random().toString(36)}`;

  return (
    <div>
      {label && <label htmlFor={inputId}>{label}</label>}
      <input id={inputId} name={name || inputId} {...props} />
      {error && <span className="error">{error}</span>}
    </div>
  );
};
```

#### Suggested Approach:

1. **Phase 1**: Fix high-traffic components first
   - Login.tsx (if any issues)
   - SettingsTab.tsx (main settings)
   - ChatInput.tsx (main chat interface)

2. **Phase 2**: Fix remaining settings components
   - PowerUserTab.tsx (3 remaining)
   - ModelsTab.tsx
   - AdvancedTab.tsx

3. **Phase 3**: Create reusable FormInput component for future use

4. **Phase 4**: Refactor remaining components to use FormInput

#### Testing Checklist:
- [ ] No browser console warnings about missing id/name
- [ ] Autofill still works (if applicable)
- [ ] Screen reader announces fields correctly
- [ ] Forms submit successfully
- [ ] No TypeScript errors

---

### Task 8: Error Message & Code Enhancement

**Estimated Time**: 3-4 hours
**Priority**: HIGH - Developer experience, debugging
**Complexity**: MEDIUM-HIGH - Requires consistency across codebase

#### Current State:
- Generic error messages: `"Failed to X"`, `"Error occurred"`
- No standardized error codes
- Stack traces exposed in development
- Limited actionable guidance for users

#### Goals:
1. **User-friendly error messages** with actionable suggestions
2. **Standardized error codes** for debugging (ERR-XXX format)
3. **Contextual help** - what went wrong, what to do next
4. **Developer-friendly** - preserve stack traces in logs, not in UI

#### Implementation Plan:

**Step 1: Define Error Code System**

Create `apps/backend/api/error_codes.py`:
```python
from enum import Enum
from typing import Dict, Any

class ErrorCode(str, Enum):
    # Authentication (1000-1099)
    AUTH_INVALID_CREDENTIALS = "ERR-1001"
    AUTH_TOKEN_EXPIRED = "ERR-1002"
    AUTH_INSUFFICIENT_PERMISSIONS = "ERR-1003"
    AUTH_RATE_LIMIT_EXCEEDED = "ERR-1004"

    # Model Operations (2000-2099)
    MODEL_NOT_FOUND = "ERR-2001"
    MODEL_LOAD_FAILED = "ERR-2002"
    MODEL_INFERENCE_TIMEOUT = "ERR-2003"
    MODEL_CONTEXT_EXCEEDED = "ERR-2004"

    # File Operations (3000-3099)
    FILE_TOO_LARGE = "ERR-3001"
    FILE_INVALID_FORMAT = "ERR-3002"
    FILE_UPLOAD_FAILED = "ERR-3003"
    FILE_NOT_FOUND = "ERR-3004"

    # Database (4000-4099)
    DB_CONNECTION_FAILED = "ERR-4001"
    DB_QUERY_FAILED = "ERR-4002"
    DB_CONSTRAINT_VIOLATION = "ERR-4003"

    # Configuration (5000-5099)
    CONFIG_INVALID = "ERR-5001"
    CONFIG_MISSING_REQUIRED = "ERR-5002"

    # Network/P2P (6000-6099)
    NETWORK_UNREACHABLE = "ERR-6001"
    PEER_CONNECTION_FAILED = "ERR-6002"

    # System (9000-9099)
    SYSTEM_RESOURCE_EXHAUSTED = "ERR-9001"
    SYSTEM_INTERNAL_ERROR = "ERR-9002"

ERROR_MESSAGES: Dict[ErrorCode, Dict[str, Any]] = {
    ErrorCode.AUTH_INVALID_CREDENTIALS: {
        "user_message": "Invalid username or password",
        "suggestion": "Please check your credentials and try again",
        "technical": "Authentication failed - invalid credentials provided"
    },
    ErrorCode.MODEL_NOT_FOUND: {
        "user_message": "Model not available",
        "suggestion": "Download the model using 'ollama pull <model>' or select a different model",
        "technical": "Requested model not found in Ollama"
    },
    ErrorCode.FILE_TOO_LARGE: {
        "user_message": "File is too large",
        "suggestion": "Maximum file size is {max_size}MB. Try compressing or splitting the file",
        "technical": "File size exceeds configured maximum"
    },
    # ... add all error codes
}
```

**Step 2: Create Error Response Builder**

Create `apps/backend/api/error_responses.py`:
```python
from fastapi import HTTPException
from typing import Optional, Dict, Any
from .error_codes import ErrorCode, ERROR_MESSAGES

class AppException(HTTPException):
    """Enhanced HTTPException with error codes and suggestions"""

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        technical_detail: Optional[str] = None
    ):
        error_info = ERROR_MESSAGES[error_code]

        # Format suggestion with context variables
        suggestion = error_info["suggestion"]
        if context:
            suggestion = suggestion.format(**context)

        detail = {
            "error_code": error_code.value,
            "message": error_info["user_message"],
            "suggestion": suggestion,
        }

        # Add technical details only in development
        if settings.debug and technical_detail:
            detail["technical"] = technical_detail

        super().__init__(status_code=status_code, detail=detail)

def bad_request(error_code: ErrorCode, **context) -> AppException:
    return AppException(400, error_code, context)

def unauthorized(error_code: ErrorCode, **context) -> AppException:
    return AppException(401, error_code, context)

def forbidden(error_code: ErrorCode, **context) -> AppException:
    return AppException(403, error_code, context)

def not_found(error_code: ErrorCode, **context) -> AppException:
    return AppException(404, error_code, context)

def internal_error(error_code: ErrorCode, **context) -> AppException:
    return AppException(500, error_code, context)
```

**Step 3: Update Existing Endpoints**

Example refactoring:

```python
# Before:
@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    try:
        model = request.model
        # ... chat logic ...
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# After:
from .error_responses import not_found, internal_error
from .error_codes import ErrorCode

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    try:
        model = request.model

        # Check if model exists
        if not await check_model_exists(model):
            raise not_found(
                ErrorCode.MODEL_NOT_FOUND,
                model=model
            )

        # ... chat logic ...

    except AppException:
        raise  # Re-raise our custom exceptions
    except Exception as e:
        logger.exception(f"Unexpected error in chat endpoint")
        raise internal_error(
            ErrorCode.SYSTEM_INTERNAL_ERROR,
            technical_detail=str(e)
        )
```

**Step 4: Frontend Error Display**

Update `apps/frontend/src/lib/errorHandler.ts`:
```typescript
interface AppError {
  error_code: string;
  message: string;
  suggestion: string;
  technical?: string;
}

export function handleApiError(error: any): void {
  const appError: AppError = error.response?.data || {
    error_code: 'ERR-9002',
    message: 'An unexpected error occurred',
    suggestion: 'Please try again or contact support',
  };

  // Show user-friendly notification
  showNotification({
    type: 'error',
    title: appError.message,
    message: appError.suggestion,
    code: appError.error_code,
  });

  // Log technical details to console in dev
  if (import.meta.env.DEV && appError.technical) {
    console.error(`[${appError.error_code}]`, appError.technical);
  }
}
```

#### Priority Endpoints for Refactoring:

**Phase 1 - High Traffic**:
1. `/api/v1/auth/login` - Authentication errors
2. `/api/v1/chat` - Chat/model errors
3. `/api/v1/upload` - File operation errors
4. `/api/v1/models/*` - Model management errors

**Phase 2 - Admin & Settings**:
5. `/api/v1/admin/*` - Admin operation errors
6. `/api/v1/team/*` - Team management errors
7. `/api/v1/vault/*` - Vault operation errors

**Phase 3 - Advanced Features**:
8. `/api/v1/workflow/*` - Workflow errors
9. `/api/v1/agent/*` - Agent orchestration errors
10. `/api/v1/p2p/*` - P2P mesh errors

#### Testing Strategy:
1. **Unit tests** for error code generation
2. **Integration tests** for API error responses
3. **Manual testing** of user-facing error messages
4. **Documentation** of all error codes in API docs

---

## 🚀 Sprint 2: Next Big Wins

### Task 9: Complete P2P Mesh Implementation

**Estimated Time**: 6-8 hours
**Priority**: HIGH - Core feature completion
**Complexity**: HIGH - Network programming, state sync

#### Current State:
- Basic P2P discovery working (mDNS/Bonjour)
- LAN device detection functional
- File sharing stub exists
- Real-time sync incomplete

#### Missing Components:
1. **Peer-to-peer file transfer** protocol
2. **Real-time state synchronization** (chat messages, workflows)
3. **Conflict resolution** for offline edits
4. **Peer authentication** and encryption
5. **Network topology management** (mesh routing)

#### Implementation Plan:

**Phase 1: Secure Peer Authentication**
```python
# apps/backend/api/p2p_auth.py
- Generate per-device Ed25519 keypairs
- Exchange public keys via QR code or pairing code
- Sign all P2P messages with private key
- Verify peer signatures before accepting data
```

**Phase 2: File Transfer Protocol**
```python
# apps/backend/api/p2p_file_transfer.py
- Chunk files into 64KB blocks
- Use reliable transport (TCP) for transfers
- Resume interrupted transfers
- Verify checksums (SHA-256)
```

**Phase 3: State Synchronization**
```python
# apps/backend/api/p2p_sync.py
- Implement CRDT (Conflict-free Replicated Data Type)
- Vector clocks for causality tracking
- Sync chat messages, workflows, documents
- Handle offline edits with merge strategies
```

**Phase 4: Mesh Routing**
```python
# apps/backend/api/p2p_mesh.py
- Distance-vector routing algorithm
- Peer discovery and heartbeat
- Automatic rerouting on peer disconnect
- NAT traversal (STUN/TURN if needed)
```

---

### Task 10: Workflow Automation Persistence

**Estimated Time**: 4-5 hours
**Priority**: MEDIUM - Feature completion
**Complexity**: MEDIUM - Database schema, job queue

#### Current State:
- Workflow designer UI exists
- Manual workflow execution works
- No persistent automation queue

#### Goals:
1. **Persistent job queue** for scheduled workflows
2. **Cron-style scheduling** (every hour, daily, weekly)
3. **Retry logic** for failed workflows
4. **Execution history** with logs and results
5. **Workflow versioning** for safe updates

#### Implementation:

**Schema Updates**:
```sql
-- workflow_schedules table
CREATE TABLE workflow_schedules (
    id INTEGER PRIMARY KEY,
    workflow_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    schedule_type TEXT NOT NULL, -- 'cron', 'interval', 'once'
    schedule_expr TEXT NOT NULL, -- '0 * * * *', '3600', 'timestamp'
    enabled BOOLEAN DEFAULT 1,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- workflow_executions table
CREATE TABLE workflow_executions (
    id INTEGER PRIMARY KEY,
    workflow_id INTEGER NOT NULL,
    schedule_id INTEGER,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'running', 'completed', 'failed'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    result_data TEXT, -- JSON
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

**Background Worker**:
```python
# apps/backend/api/workflow_scheduler.py
import asyncio
from datetime import datetime, timedelta
from croniter import croniter

class WorkflowScheduler:
    async def run_forever(self):
        while True:
            await self.check_and_run_scheduled_workflows()
            await asyncio.sleep(60)  # Check every minute

    async def check_and_run_scheduled_workflows(self):
        now = datetime.utcnow()

        # Get workflows due to run
        schedules = db.query(
            "SELECT * FROM workflow_schedules "
            "WHERE enabled = 1 AND next_run <= ?",
            (now,)
        )

        for schedule in schedules:
            await self.execute_workflow(schedule)
            self.update_next_run(schedule)
```

---

### Task 11: Performance Optimization

**Estimated Time**: 3-4 hours
**Priority**: MEDIUM - UX improvement
**Complexity**: MEDIUM - Profiling, caching

#### Areas for Optimization:

1. **Database Query Optimization**
   - Add indexes on frequently queried columns
   - Use prepared statements consistently
   - Implement query result caching

2. **API Response Caching**
   - Cache static data (model lists, user permissions)
   - Implement ETags for conditional requests
   - Use Redis/in-memory cache for hot paths

3. **Frontend Bundle Optimization**
   - Code splitting by route
   - Lazy load heavy components
   - Tree-shake unused libraries
   - Optimize image/asset loading

4. **Model Inference Optimization**
   - Batch similar requests
   - Implement request queuing with priorities
   - Cache embeddings for common queries
   - Use streaming for long responses

#### Implementation:

**Database Indexes**:
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_workflows_user ON workflows(user_id);
CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action);
```

**API Caching**:
```python
from functools import lru_cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())

@app.get("/api/v1/models")
@cache(expire=300)  # Cache for 5 minutes
async def list_models():
    return await ollama_client.list_models()
```

**Frontend Code Splitting**:
```typescript
// Use React.lazy for route-based splitting
const AdminPanel = React.lazy(() => import('./components/admin/AdminPanel'));
const WorkflowDesigner = React.lazy(() => import('./components/WorkflowDesigner'));

// In router:
<Route path="/admin" element={
  <Suspense fallback={<LoadingSpinner />}>
    <AdminPanel />
  </Suspense>
} />
```

---

## 📋 Sprint 3: Advanced Features

### Task 12: Real-time Collaboration

**Estimated Time**: 8-10 hours
**Priority**: MEDIUM - Advanced feature
**Complexity**: HIGH - WebSockets, OT/CRDT

#### Features:
- Real-time document editing (Google Docs style)
- Live cursor positions and selections
- Presence indicators (who's online)
- Collaborative workflow design
- Chat room synchronization

---

### Task 13: Data Export/Import Wizard

**Estimated Time**: 4-5 hours
**Priority**: LOW - Nice-to-have
**Complexity**: MEDIUM - Data transformation

#### Features:
- Export workflows as JSON/YAML
- Import from external tools (Zapier, n8n format)
- Bulk export chat history
- Database backup/restore UI
- Template marketplace (import community workflows)

---

### Task 14: Frontend Bundle Optimization

**Estimated Time**: 2-3 hours
**Priority**: MEDIUM - Performance
**Complexity**: LOW - Build configuration

---

### Task 15: Usage Analytics Dashboard

**Estimated Time**: 5-6 hours
**Priority**: LOW - Insights
**Complexity**: MEDIUM - Data aggregation

---

## 🎁 Quick Wins (30 min - 2 hours each)

### Task 16: Model Download UI
- Progress indicators for ollama pull
- Cancel/pause downloads
- Recommended models list

### Task 17: Keyboard Shortcuts
- Global shortcuts (Cmd+K for quick chat)
- Vim mode for code editor
- Customizable keybindings

### Task 18: Dark Mode Refinement
- Fix any remaining contrast issues
- Smooth theme transitions
- Respect system preference

### Task 19: Onboarding Tutorial
- Interactive walkthrough for new users
- Tooltips for key features
- Getting started wizard

### Task 20: Health Check Dashboard
- System resource monitoring
- Model performance metrics
- API latency tracking
- Database query profiling

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] Configuration validation tests
- [ ] Error code generation tests
- [ ] Model manager tests
- [ ] P2P protocol tests

### Integration Tests
- [ ] API endpoint tests with error codes
- [ ] Workflow execution end-to-end
- [ ] P2P file transfer
- [ ] Authentication flows

### E2E Tests (Playwright)
- [ ] User registration/login
- [ ] Chat conversation flow
- [ ] Workflow creation and execution
- [ ] Settings changes persistence

### Performance Tests
- [ ] Load testing critical endpoints
- [ ] Database query performance
- [ ] Model inference latency
- [ ] Frontend bundle size tracking

---

## 📚 Documentation Tasks

1. **API Documentation**
   - ✅ OpenAPI spec (completed)
   - [ ] Error code reference
   - [ ] Authentication guide
   - [ ] Rate limiting guide

2. **Developer Documentation**
   - [ ] Architecture overview
   - [ ] Database schema docs
   - [ ] Contribution guidelines
   - [ ] Testing guide

3. **User Documentation**
   - [ ] Getting started guide
   - [ ] Feature tutorials
   - [ ] Troubleshooting guide
   - [ ] FAQ

4. **Deployment Documentation**
   - ✅ .env configuration (completed)
   - [ ] Docker deployment
   - [ ] Production checklist
   - [ ] Backup/restore procedures

---

## 🔒 Security Hardening (Ongoing)

1. **Input Validation**
   - [ ] Pydantic models for all API inputs
   - [ ] SQL injection prevention audit
   - [ ] Path traversal prevention audit

2. **Authentication**
   - [ ] JWT token rotation
   - [ ] Device fingerprinting
   - [ ] Suspicious activity detection

3. **Encryption**
   - [ ] At-rest encryption for sensitive data
   - [ ] In-transit TLS for P2P
   - [ ] Key rotation strategy

4. **Audit Logging**
   - [ ] Comprehensive audit trail
   - [ ] Tamper-proof logs
   - [ ] Security event alerting

---

## 📈 Success Metrics

### Performance
- API response time < 100ms (p95)
- Model inference start < 2s
- Frontend initial load < 3s
- Zero N+1 queries

### Quality
- 80%+ test coverage
- Zero critical security issues
- < 5 bugs per release
- All accessibility warnings resolved

### User Experience
- User onboarding completion > 90%
- Feature discovery rate > 70%
- Error recovery success > 95%
- Support ticket reduction by 50%

---

## 🎯 Immediate Next Steps (Priority Order)

1. **Complete hardcoded path removal** (30 min)
   - Fix remaining 7 files
   - Test imports
   - Commit changes

2. **Implement error code system** (3-4 hours)
   - Create error_codes.py
   - Create error_responses.py
   - Refactor top 10 endpoints
   - Update frontend error handler

3. **Form field accessibility** (2-3 hours)
   - Fix SettingsTab.tsx (25 inputs)
   - Fix PowerUserTab.tsx (3 remaining)
   - Create reusable FormInput component

4. **Sprint 2 kickoff** (Next session)
   - Choose between P2P, workflow automation, or performance
   - Detailed implementation of chosen feature

---

## 💡 Notes & Considerations

### Technical Debt
- Migration output cleanup was attempted but needs backend restart to take effect
- Some files still use legacy path imports (backwards compat)
- Frontend has mix of component patterns (needs standardization)

### Future Considerations
- Multi-user collaborative editing needs CRDT implementation
- P2P mesh requires NAT traversal strategy
- Workflow versioning needs migration strategy
- Rate limiting needs distributed approach for multi-instance

### Dependencies to Monitor
- Ollama API changes (model management)
- Pydantic v2 migration completed
- FastAPI security updates
- React 19 upcoming changes

---

## 📞 Support & Resources

- **Documentation**: `/docs` directory
- **API Docs**: `http://localhost:8000/api/docs`
- **Issues**: Track in GitHub or task management system
- **Architecture Decisions**: Document in ADR format

---

**Last Updated**: November 9, 2025
**Next Review**: After Sprint 1 completion
