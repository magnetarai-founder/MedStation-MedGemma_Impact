# Migration Guide Template

**Purpose:** Reusable template for future code migrations in ElohimOS

**Based On:** Successful patterns from 5/5 router migrations and SQL/JSON refactoring

---

## Migration Principles

### Core Rules

1. **One endpoint at a time** - Move small pieces, test immediately
2. **OpenAPI diff after each move** - Verify zero API changes
3. **Preserve exact behavior** - Same paths, methods, models, errors
4. **Keep both versions temporarily** - Old code stays until new code validated
5. **Absolute imports** - Always use `from api.routes import ...`
6. **Comment, don't delete** - Preserve original code for rollback

### Success Criteria

✅ Zero behavior changes
✅ 100% OpenAPI contract preservation
✅ Shared state accessible via getter/setter functions
✅ Original code commented (not deleted) for safety
✅ Manual testing of all migrated endpoints
✅ Full error logging with tracebacks

---

## Pre-Migration Checklist

### 1. Analysis Phase

- [ ] Identify endpoints to migrate
- [ ] Map dependencies (imports, shared state, etc.)
- [ ] Identify Pydantic models to extract
- [ ] Estimate complexity (Low/Medium/High/Very High)
- [ ] Create migration plan document

### 2. Environment Setup

- [ ] Ensure dev environment is clean (no uncommitted changes)
- [ ] Take OpenAPI snapshot: `curl http://localhost:8000/api/openapi.json > openapi_before.json`
- [ ] Create git branch: `git checkout -b migration/[name]`
- [ ] Document current line counts (for metrics)

### 3. File Structure

- [ ] Create router file: `api/routes/[domain].py`
- [ ] Create service file: `api/services/[domain].py` (if needed)
- [ ] Create schema file: `api/schemas/[domain]_models.py` (if needed)
- [ ] Create empty router with proper imports

---

## Migration Workflow (Step-by-Step)

### Step 1: Create Router Scaffold

```python
# api/routes/[domain].py

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

router = APIRouter()

# Lazy imports - import inside functions to break circular dependencies
# DO NOT import permission_engine or auth_middleware at module level

# Example getter for shared state
def get_shared_data():
    """Lazy load shared state from main.py"""
    from api import main
    return main.shared_data_dict
```

### Step 2: Extract Pydantic Models

```python
# api/schemas/[domain]_models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MyRequestModel(BaseModel):
    """Request model for my endpoint"""
    field1: str = Field(..., description="Description")
    field2: Optional[int] = None

class MyResponseModel(BaseModel):
    """Response model for my endpoint"""
    id: str
    data: Dict[str, Any]
    created_at: str
```

### Step 3: Create Service Layer (if needed)

```python
# api/services/[domain].py

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def my_service_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Business logic function

    Args:
        param1: Description
        param2: Description

    Returns:
        Dict with results

    Raises:
        ValueError: If invalid input
    """
    # Import dependencies lazily
    from permission_engine import check_permission
    from api import main

    # Business logic here
    try:
        result = {"status": "success"}
        return result
    except Exception as e:
        logger.error(f"Service function failed: {e}", exc_info=True)
        raise
```

### Step 4: Migrate Endpoint

```python
# api/routes/[domain].py

@router.post("/endpoint", response_model=MyResponseModel, operation_id="domain_action")
async def my_endpoint(
    request: MyRequestModel,
    current_user: Dict = Depends(get_current_user)
):
    """
    Endpoint description

    - **field1**: Description
    - **field2**: Description
    """
    # Import service functions lazily
    from api.services import domain_service

    try:
        # Delegate to service layer
        result = await domain_service.my_service_function(
            param1=request.field1,
            param2=request.field2 or 0
        )

        return MyResponseModel(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Step 5: Wire Router in main.py

```python
# In api/main.py

# Add with try/except for error visibility
try:
    from routes import domain
    app.include_router(
        domain.router,
        prefix="/api/domain",
        tags=["domain"]
    )
    logger.info("✓ Loaded domain router")
except ImportError as e:
    logger.error(f"Failed to import domain router: {e}", exc_info=True)
```

### Step 6: Comment Out Original Code

```python
# In api/main.py (original location)

# ============================================================================
# MIGRATED TO: api/routes/domain.py
# ============================================================================
# @app.post("/api/domain/endpoint")
# async def my_endpoint(...):
#     [original code here - preserved for rollback]
# ============================================================================
```

### Step 7: Test Migration

```bash
# Restart server
./elohim

# Test endpoint manually
curl -X POST http://localhost:8000/api/domain/endpoint \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"field1": "value"}'

# Verify response matches expected format
```

### Step 8: OpenAPI Verification

```bash
# Take new snapshot
curl http://localhost:8000/api/openapi.json > openapi_after.json

# Compare (should be identical except operation_id if added)
diff openapi_before.json openapi_after.json

# If differences found, investigate and fix
```

### Step 9: Commit

```bash
# Stage changes
git add api/routes/domain.py api/services/domain.py api/schemas/domain_models.py api/main.py

# Commit with descriptive message
git commit -m "feat: Migrate domain router to service layer pattern

- Migrated X endpoints from main.py to api/routes/domain.py
- Extracted Y Pydantic models to api/schemas/domain_models.py
- Created service layer with Z functions in api/services/domain.py
- All endpoints tested and verified
- OpenAPI contract preserved (377 paths identical)

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Common Patterns

### Getter/Setter for Shared State

```python
def get_sessions():
    """Access shared sessions dict from main.py"""
    from api import main
    return main.sessions

def get_query_results():
    """Access shared query results from main.py"""
    from api import main
    return main.query_results

@router.post("/create")
async def create_session(request: Request):
    sessions = get_sessions()  # Lazy load
    # Use sessions dict
```

### Lazy Imports

```python
@router.get("/endpoint")
async def my_endpoint():
    # Import inside function, not at module level
    from permission_engine import require_perm
    from auth_middleware import get_current_user
    from api import main

    # Use imports here
```

### Error Logging

```python
try:
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Permission Checks

```python
@router.post("/protected")
async def protected_endpoint(current_user: Dict = Depends(get_current_user)):
    # Lazy import permission engine
    from permission_engine import check_permission

    # Check permission
    if not check_permission(current_user, "domain.action"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Proceed with operation
```

---

## Troubleshooting

### Issue: Circular Import Error

**Symptom:** `ImportError: cannot import name 'X' from partially initialized module`

**Solution:** Use lazy imports inside functions, not at module level

```python
# ❌ WRONG
from permission_engine import require_perm

# ✅ CORRECT
def my_function():
    from permission_engine import require_perm
    # Use require_perm here
```

---

### Issue: Shared State Not Accessible

**Symptom:** `AttributeError: module 'api.main' has no attribute 'sessions'`

**Solution:** Use getter functions with lazy imports

```python
def get_sessions():
    from api import main
    return main.sessions

# In endpoint
sessions = get_sessions()
```

---

### Issue: OpenAPI Contract Changed

**Symptom:** `diff` shows differences between before/after OpenAPI specs

**Solution:** Verify endpoint paths, methods, and models match exactly

```python
# Ensure prefix + path = original path
app.include_router(router, prefix="/api/domain")  # If original was /api/domain/endpoint
@router.post("/endpoint")  # Results in /api/domain/endpoint
```

---

### Issue: Router Not Loading

**Symptom:** Router endpoints not available, no error in logs

**Solution:** Add error logging in main.py

```python
try:
    from routes import domain
    app.include_router(domain.router)
except ImportError as e:
    logger.error(f"Failed to import domain router: {e}", exc_info=True)
```

---

## Anti-Patterns to Avoid

### ❌ Module-Level Permission Imports

```python
# WRONG - causes circular dependencies
from permission_engine import require_perm

@router.get("/endpoint")
async def endpoint():
    pass
```

### ❌ Deleting Original Code

```python
# WRONG - no rollback path
# [deleted the original endpoint code]
```

### ❌ Silent Try/Except

```python
# WRONG - failures are hidden
try:
    result = operation()
except:
    pass  # Silent failure
```

### ❌ Changing Operation IDs Without Coordination

```python
# WRONG - breaks frontend
@router.get("/endpoint", operation_id="new_id")  # Frontend expects old_id
```

---

## Post-Migration Checklist

### Immediate

- [ ] All endpoints tested manually
- [ ] OpenAPI contract verified (diff = empty or expected)
- [ ] No errors in logs during startup
- [ ] Commit pushed to branch
- [ ] Migration documented in commit message

### Before Merging

- [ ] Code review completed
- [ ] Integration tests passed (if available)
- [ ] Performance verified (no regressions)
- [ ] Documentation updated (if needed)

### After Merge

- [ ] Monitor production for issues (first 24 hours)
- [ ] Remove commented code (after 1 week of stability)
- [ ] Update migration history document
- [ ] Celebrate successful migration! 🎉

---

## Metrics to Track

### Migration Size

- Endpoints migrated: X
- Lines reduced from main.py: Y
- Service functions created: Z
- Pydantic models extracted: N

### Quality

- OpenAPI contract preserved: ✅/❌
- Behavior changes: Zero
- Production issues: Zero
- Test coverage: X%

### Complexity

- Low: Simple CRUD, 1-3 endpoints
- Medium: Multiple operations, some dependencies
- High: Complex logic, many dependencies
- Very High: Streaming, GPU integration, encryption, P2P

---

## Template Usage

### For New Migrations

1. Copy this template
2. Replace `[domain]` with your domain name
3. Follow workflow step-by-step
4. Check off checklist items as you complete them
5. Document any deviations from template
6. Update template if new patterns discovered

### Customize for Your Domain

This template is a starting point. Adapt as needed for:
- Domain-specific patterns
- Special integrations (GPU, encryption, etc.)
- Streaming endpoints (SSE)
- File uploads/downloads
- WebSocket connections

---

## Examples from ElohimOS

### Successful Migrations

1. **Admin Router** - 13 endpoints (Medium complexity)
2. **Users Router** - 3 endpoints (Low complexity)
3. **Team Router** - 50 endpoints (Very High complexity - P2P, encryption)
4. **Permissions Router** - 18 endpoints (High complexity - RBAC)
5. **Chat Router** - 53 endpoints (Very High complexity - GPU, streaming, ANE)

### Lessons Learned

See `/docs/migrations/completed/COMPLETE_MIGRATION_HISTORY.md` for:
- Detailed migration patterns
- Common pitfalls
- Best practices
- Anti-patterns to avoid

---

## Reference Documents

- **Migration History:** `/docs/migrations/completed/COMPLETE_MIGRATION_HISTORY.md`
- **System Architecture:** `/docs/architecture/SYSTEM_ARCHITECTURE.md`
- **Development Notes:** `/docs/development/DEVELOPMENT_NOTES.md`

---

**Template Version:** 1.0
**Last Updated:** 2025-11-12
**Based On:** 5 successful router migrations + 3 SQL/JSON refactoring phases
