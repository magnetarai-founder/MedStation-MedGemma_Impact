# Changelog

All notable changes to ElohimOS will be documented in this file.

## [Unreleased] - 2025-11-07

### Added

#### Queue Status Badge (Frontend)
- **GPU queue indicator** in app header - Shows active buffer count with pulsing badge
- **Auto-polling** every 5s with 3-failure backoff to minimize network spam
- **Tooltip integration** - Displays count on hover over Activity button
- Located in `apps/frontend/src/components/Header.tsx:22-68,224-240`

### Added (Backend + Frontend)

#### macOS-Only Platform Hardening
- **Darwin OS checks** in `elohim` entrypoint script - fails fast on non-macOS systems
- **Darwin OS checks** in `tools/scripts/start_web.sh` - validates platform before startup
- **Backend platform validation** in `apps/backend/api/main.py:lifespan` - raises RuntimeError on non-Darwin
- **Platform markers** in `apps/backend/requirements.txt` - Metal frameworks install only on macOS

#### Audit Log System (Backend + Frontend)
- **GET `/api/v1/admin/audit/logs`** - Query audit logs with filters (user, action, resource, date range, pagination)
- **GET `/api/v1/admin/audit/export`** - Export audit logs to CSV with date filtering
- **Frontend integration** in `AuditLogsTab.tsx` - Real-time audit log viewing and CSV export
- **Permission gating** - Both endpoints require `system.view_audit_logs` permission
- **Audit trail** - All audit log access is itself logged for compliance

#### Backup System (Backend + Frontend)
- **Backend Router**: `apps/backend/api/backup_router.py` with 5 endpoints
  - **POST `/api/v1/backups/create`** - Create encrypted local backup
  - **GET `/api/v1/backups/list`** - List all available backups with metadata
  - **POST `/api/v1/backups/verify`** - Verify backup integrity with checksum validation
  - **POST `/api/v1/backups/restore`** - Restore from backup file
  - **POST `/api/v1/backups/cleanup`** - Delete backups older than 7 days
  - **Permission gating** - All endpoints require `backups.use` permission
  - **Audit logging** - All backup operations logged via `AuditAction`
- **Frontend UI**: Complete backup management in DangerZoneTab
  - Create backup button with status feedback
  - List view with size/date metadata
  - Verify and restore actions per backup
  - Cleanup old backups (7-day retention)
  - Empty state handling
  - Toast notifications for all operations
  - Located in `apps/frontend/src/components/settings/DangerZoneTab.tsx:1-17,24-124,243-348`

### Changed

#### Export Button Improvements
- **File download handling** in DangerZoneTab - Export buttons now properly download files
  - `export-all` downloads as ZIP
  - `export-chats` and `export-queries` download as JSON
  - Blob download via `URL.createObjectURL` with cleanup
  - Error handling with toast notifications
  - No page navigation on export actions

- **Documentation updates**:
  - `docs/dev/README.md` - Updated prerequisites to specify macOS-only, added Homebrew dependencies
  - `DEPLOYMENT_CHECKLIST.md` - Added platform requirements section emphasizing offline-first
  - `.env.example` - Added platform requirements comment block

#### Trash Bin Status
- **Verified existing implementation** - All endpoints properly wired in VaultWorkspace:
  - `GET /api/v1/vault/trash` - List trashed items (line 1242)
  - `POST /api/v1/vault/files/{fileId}/restore` - Restore from trash (line 1522)
  - `DELETE /api/v1/vault/trash/empty` - Empty trash bin (line 1536)

### Technical Details

**Files Modified:**
- `elohim` - Added Darwin check at line 6-11
- `tools/scripts/start_web.sh` - Added Darwin check at line 5-10
- `apps/backend/api/main.py` - Added platform check at line 190; registered backup router at line 444-445
- `apps/backend/requirements.txt` - Added `;sys_platform == "darwin"` to Metal frameworks (lines 15-17)
- `apps/backend/api/admin_service.py` - Added audit log routes (lines 629-803)
- `apps/frontend/src/components/settings/AuditLogsTab.tsx` - Wired to backend API (lines 43-92)
- `apps/frontend/src/components/settings/DangerZoneTab.tsx` - Added backup UI + export download handling (316 lines total)
- `apps/frontend/src/components/Header.tsx` - Added queue status badge with polling (lines 22-68, 224-240)
- `docs/dev/README.md` - Updated prerequisites section
- `DEPLOYMENT_CHECKLIST.md` - Added platform requirements
- `.env.example` - Added platform comments

**Files Created:**
- `apps/backend/api/backup_router.py` - Complete backup API router (316 lines)
- `CHANGELOG.md` - Project changelog

### Migration Notes

**For Non-macOS Users:**
- ElohimOS now **explicitly requires macOS**. Running `./elohim` or `start_web.sh` on Linux/Windows will exit with clear error message.
- Backend startup will fail with `RuntimeError` on non-Darwin systems.

**For Administrators:**
- Audit logs are now accessible via Settings → Audit Logs (requires admin/super_admin role)
- Export functionality uses backend CSV generation for consistency
- Backup endpoints available at `/api/v1/backups/*` (requires `backups.use` permission)

### Security Notes
- All new endpoints are permission-gated
- Audit log access is itself audited
- Backup operations are logged with full details
- Platform checks prevent unsupported OS execution

---

## [1.0.0-alpha] - 2025-11-06

Initial release of ElohimOS.
