# Router Migration Status - Service Layer Pattern

## Overview
Migrating ElohimOS routers to follow the service layer pattern with lazy imports to break circular dependencies and improve code organization.

## Pattern Established

**Architecture:**
```
api/routes/[domain].py    → Thin router (delegation only)
api/services/[domain].py   → Business logic (lazy imports)
api/schemas/[domain]_models.py → Pydantic models
```

**Key Principles:**
- Lazy imports: All heavy dependencies imported inside function bodies
- Thin routers: Minimal logic, delegate to service layer
- Error logging: Full traceback on router registration failures
- Operation IDs: `{domain}_{action}` format
- Tags: `["{domain}"]` format

---

## Completed Migrations (3/5)

### ✅ Admin Router
- **Files:**
  - `api/services/admin.py` - 13 admin operations
  - `api/routes/admin.py` - Thin router
- **Endpoints:** 13 danger zone operations
- **Status:** Fully migrated, tested, committed
- **Commit:** b46e84c4

### ✅ Users Router
- **Files:**
  - `api/services/users.py` - 3 user profile operations
  - `api/routes/users.py` - Thin router
  - `api/schemas/user_models.py` - Pydantic models
- **Endpoints:** 3 user profile operations (GET/PUT /me, POST /reset)
- **Status:** Fully migrated, tested, committed
- **Removed:** `api/user_service.py` (legacy)
- **Commit:** b46e84c4

### ✅ Team Router
- **Files:**
  - `api/schemas/team_models.py` - 76 Pydantic models (525 lines)
  - `api/services/team.py` - Business logic (2,911 lines, 65 methods)
  - `api/routes/team.py` - Thin router (1,334 lines, 50 endpoints)
- **Endpoints:** 50 team management operations
  - Core team management (5 endpoints)
  - Member management & roles (8 endpoints)
  - Promotion system (7 endpoints)
  - Job roles (2 endpoints)
  - Workflow permissions (4 endpoints)
  - Queue management (7 endpoints)
  - Founder Rights (5 endpoints)
  - Team vault (12 endpoints)
- **Complexity:** Very High (P2P mesh, crypto, RBAC, vault encryption)
- **Status:** Fully migrated, tested
- **Details:** All 76 models, 65 service methods, and 50 endpoints successfully migrated with lazy imports, permission checks, audit logging, and rate limiting preserved

---

## In Progress (1/5)

### 🔄 Permissions Router (Phase 1/3)
- **Files:**
  - ✅ `api/schemas/permission_models.py` - 10 Pydantic models extracted
  - ⏳ `api/services/permissions.py` - Needs 14 service functions (~600 lines)
  - ⏳ `api/routes/permissions.py` - Needs 18 thin endpoints (~400 lines)
- **Endpoints:** 18 RBAC management operations
- **Complexity:** High (audit logging, cache invalidation, permission engine integration)
- **Current Status:** Models extracted and committed
- **Commit:** 312094da
- **Remaining Work:**
  - Extract business logic from `permissions_admin.py` to service layer
  - Create thin router with lazy imports
  - Preserve audit logging and cache invalidation calls
  - Test all 18 endpoints

**Migration Plan:** See detailed plan in session notes (14 service functions mapped)

---

## Pending Migrations (1/5)

### ⏸️ Chat Standardization
- **Current State:** Various chat routes with inconsistent tags/IDs
- **Work Needed:**
  - Normalize operation IDs and tags
  - Extract logic to `api/services/chat.py`
  - Ensure consistent patterns
- **Estimated Effort:** 2-3 hours
- **Priority:** Medium

---

## Benefits Achieved

1. **Circular Dependencies:** Broken via lazy imports
2. **Code Organization:** Clear separation of concerns
3. **Error Visibility:** Router failures now logged with full traceback
4. **Testability:** Service functions easier to unit test
5. **Maintainability:** Thin routers easier to understand

---

## Next Steps

**Recommended Order:**
1. Complete Permissions router (finish phases 2-3)
2. Tackle Team router (largest, most complex)
3. Standardize Chat routes
4. Review and consolidate remaining routers

**Alternative Approach:**
- Skip complex routers (Permissions, Team) for now
- Focus on smaller routers first to establish momentum
- Return to complex ones with fresh context

---

## Code Quality Guardrails

✅ **Must Have:**
- Lazy imports for all cycle-prone dependencies
- Error logging with `exc_info=True` in main.py
- Preserve all existing functionality
- Keep operation IDs stable (breaking changes require frontend updates)
- Test endpoints before committing

❌ **Must Avoid:**
- Module-level imports of permission_engine, auth_middleware
- Silent try/except blocks (use logger.error)
- Changing operation IDs without coordination
- Deleting old files before testing new ones

---

*Last Updated: 2025-11-12*
*Session: Router migration with service layer pattern*
