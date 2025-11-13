# Code Tab - Monaco Editor + Terminal

ElohimOS Code Tab provides Monaco-based code editing with workspace management, file tree navigation, diff-confirm saves, and integrated terminal.

## Features

- **Monaco Editor**: VS Code's editor component with syntax highlighting
- **Workspace Management**: Disk-based workspaces with file tracking
- **Diff-Confirm Save**: Preview changes before saving (unified diff)
- **Optimistic Concurrency**: Prevents silent overwrites (409 conflict detection)
- **Terminal**: Integrated shell access via WebSocket
- **RBAC**: Permission-based access control

## Permissions

| Permission | Required For |
|------------|--------------|
| `code.use` | View files, workspaces, file tree, generate diffs |
| `code.edit` | Create/update/delete files, open disk workspaces, sync |
| `code.terminal` | Spawn terminal sessions |

## Setup

### Backend

```bash
cd apps/backend
./setup_dev.sh
# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ELOHIM_ENV=development
uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

## Usage

### 1. Open Folder

1. Click "Open Project or Folder" in sidebar
2. Enter absolute path (e.g., `/Users/you/code/myproject`)
3. Workspace created → file tree loads

### 2. Edit Files

1. Click file in tree → opens in Monaco
2. Click "Edit" → enable editing
3. Make changes
4. Click "Save" → diff modal appears
5. Review changes → "Confirm Save"

### 3. Conflict Handling

If file was modified by another user:
- Diff modal shows conflict warning
- Current server content displayed
- Options: overwrite or reload file

### 4. Terminal

1. Click "Terminal" button in file header
2. Terminal panel opens below editor
3. Type commands → press Enter
4. Output streams in real-time

## Troubleshooting

### 403 Permission Denied

**Symptoms**: Red banner "Permission denied: code.use/code.edit required"

**Fix**: Contact admin to grant permissions via Admin Panel → Permissions

### 409 Conflict on Save

**Symptoms**: "File was modified by another user" toast

**Fix**:
1. Reload file to see latest changes
2. Reapply your edits
3. Save again

### Terminal WebSocket Error

**Symptoms**: "WebSocket connection error" in terminal panel

**Fix**:
- Check token validity (refresh page)
- Verify `code.terminal` permission
- Check backend logs for WebSocket errors

### Workspace Not Loading

**Symptoms**: Empty file tree after opening folder

**Fix**:
- Check path exists and is readable
- Open browser DevTools → Console for errors
- Verify backend is running on port 8000

## Verification Checklist

- [ ] Open folder → workspace created
- [ ] File tree loads
- [ ] Click file → Monaco loads content
- [ ] Edit → Save → diff modal → confirm → saved
- [ ] Edit → another user edits → Save → 409 conflict shown
- [ ] Terminal button → session spawns → typing echoes
- [ ] Close terminal → graceful shutdown

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/code-editor/workspaces/open-disk` | POST | Create disk workspace |
| `/api/v1/code-editor/workspaces/{id}/files` | GET | List workspace files |
| `/api/v1/code-editor/files/{id}` | GET | Get file content |
| `/api/v1/code-editor/files/{id}` | PUT | Update file (with concurrency) |
| `/api/v1/code-editor/files/{id}/diff` | POST | Generate diff |
| `/api/v1/terminal/spawn` | POST | Spawn terminal session |

## Technical Notes

- Workspace IDs persist in `localStorage.ns.code.workspaceId`
- File tracking uses UUIDs (not paths)
- Optimistic concurrency uses `updated_at` timestamps
- Diff format: unified diff (GNU diffutils compatible)
- Terminal: WebSocket protocol (see `terminal_api.py`)

## Architecture

### Backend (`apps/backend/api/code_editor_service.py`)

- **RBAC Protection**: All endpoints require `code.use` or `code.edit` permissions
- **Path Guards**: `ensure_under_root()` prevents path traversal attacks
- **Audit Logging**: All write operations logged with user_id, action, resource
- **Optimistic Concurrency**: PUT `/files/{id}` checks `base_updated_at`, returns 409 on mismatch
- **Diff Endpoint**: POST `/files/{id}/diff` generates unified diff, detects conflicts

### Frontend (`apps/frontend/src`)

- **API Wrapper** (`api/codeEditor.ts`): Typed helpers for all endpoints
- **FileBrowser** (`components/FileBrowser.tsx`): Workspace-based file tree
- **CodeView** (`components/CodeView.tsx`): Main editor with diff-confirm save flow
- **DiffConfirmModal**: Review changes before saving
- **TerminalPanel**: WebSocket terminal integration

### Security Features

1. **RBAC**: Permission checks on all operations
2. **Path Traversal Protection**: `ensure_under_root()` validates all paths
3. **Audit Trail**: All write operations logged to `audit.db`
4. **Optimistic Concurrency**: Prevents lost updates in concurrent editing
5. **Conflict Detection**: Diff endpoint warns of concurrent modifications

## Development

### Adding New File Operations

1. Add endpoint in `api/code_editor_service.py`
2. Add RBAC decorator (`@require_perm("code.edit")`)
3. Add path guard for disk operations
4. Add audit logging with appropriate `AuditAction`
5. Add type-safe method to `api/codeEditor.ts`
6. Update UI components as needed

### Testing

Run backend smoke tests:
```bash
cd apps/backend
source venv/bin/activate
export ELOHIM_ENV=development
pytest tests/smoke/test_code_editor_security.py -v
```

Expected output:
- Path guard validation tests pass
- RBAC decorator presence verified
- Audit action constants exist

## Future Enhancements

- [ ] Multi-file diff view
- [ ] Git integration (commit, push, pull)
- [ ] Collaborative editing (OT/CRDT)
- [ ] File search within workspace
- [ ] Code completion (LSP integration)
- [ ] Terminal multiplexing (tmux/screen)
