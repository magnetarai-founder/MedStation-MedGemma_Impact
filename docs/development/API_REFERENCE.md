# ElohimOS API Reference

Complete API documentation for the ElohimOS backend REST API.

**Base URL**: `http://localhost:8000`
**API Version**: v1
**Base Path**: `/api/v1`

---

## Table of Contents

- [Authentication](#authentication)
- [Vault API](#vault-api)
  - [File Operations](#file-operations)
  - [Comments](#comments)
  - [Versions](#versions)
  - [Trash](#trash)
  - [Search](#search)
  - [Sharing](#sharing)
  - [Analytics](#analytics)
- [Pagination Contract](#pagination-contract)
- [Rate Limiting](#rate-limiting)
- [Error Codes](#error-codes)
- [Model Preloader](#model-preloader)

---

## Authentication

### Forced Password Change Flow

Users with `must_change_password=1` flag are required to change their password before accessing the system.

#### 1. Login Attempt with Temporary Password

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user&password=TempPassword123
```

**Response (403 Forbidden)**:
```json
{
  "detail": {
    "error_code": "AUTH_PASSWORD_CHANGE_REQUIRED",
    "message": "You must change your password before continuing"
  }
}
```

#### 2. Change Password (First Login)

```http
POST /api/v1/auth/change-password-first-login
Content-Type: application/x-www-form-urlencoded

username=user&temp_password=TempPassword123&new_password=NewSecure!Pass456&confirm_password=NewSecure!Pass456
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

#### 3. Normal Login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user&password=NewSecure!Pass456
```

**Response (200 OK)**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "user_123",
  "username": "user",
  "role": "member"
}
```

---

## Vault API

All vault endpoints require authentication via `Authorization: Bearer <token>` header.

### File Operations

#### Upload File

```http
POST /api/v1/vault/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file=<binary>
vault_passphrase=MySecurePass123!
vault_type=real
folder_path=/documents
```

**Rate Limit**: Not rate-limited (upload operations)

**Response (200 OK)**:
```json
{
  "file_id": "file_abc123",
  "filename": "document.pdf",
  "file_size": 1048576,
  "mime_type": "application/pdf",
  "vault_type": "real",
  "folder_path": "/documents",
  "created_at": "2025-11-14T12:34:56Z"
}
```

#### Download File

```http
GET /api/v1/vault/files/{file_id}/download?vault_type=real&vault_passphrase=MySecurePass123!
Authorization: Bearer <token>
```

**Rate Limit**: 120 requests/min per user

**Response (200 OK)**:
- Binary file content
- Headers: `Content-Type`, `Content-Disposition`, `Content-Length`

**Audit Log**: `vault.file.downloaded`

#### File Preview

File preview uses the same download endpoint with optional `preview=true` parameter for generating thumbnails or previews.

---

### Comments

#### Add Comment

```http
POST /api/v1/vault/files/{file_id}/comments
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

comment_text=This is a test comment
vault_type=real
```

**Rate Limit**: 60 requests/min per user

**Response (200 OK)**:
```json
{
  "comment_id": "comment_xyz789",
  "file_id": "file_abc123",
  "user_id": "user_123",
  "comment_text": "This is a test comment",
  "created_at": "2025-11-14T12:35:00Z"
}
```

**Audit Log**: `vault.comment.added`

#### List Comments (with Pagination)

```http
GET /api/v1/vault/files/{file_id}/comments?vault_type=real&limit=10&offset=0
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Response (200 OK)**:
```json
{
  "data": [
    {
      "comment_id": "comment_xyz789",
      "user_id": "user_123",
      "username": "john_doe",
      "comment_text": "This is a test comment",
      "created_at": "2025-11-14T12:35:00Z",
      "updated_at": "2025-11-14T12:35:00Z"
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

#### Update Comment

```http
PUT /api/v1/vault/comments/{comment_id}
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

comment_text=Updated comment text
vault_type=real
```

**Rate Limit**: 60 requests/min per user

**Audit Log**: `vault.comment.updated`

#### Delete Comment

```http
DELETE /api/v1/vault/comments/{comment_id}?vault_type=real
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Audit Log**: `vault.comment.deleted`

---

### Versions

#### List File Versions (with Pagination)

```http
GET /api/v1/vault/files/{file_id}/versions?vault_type=real&limit=10&offset=0
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Response (200 OK)**:
```json
{
  "data": [
    {
      "version_id": "v_abc123",
      "file_id": "file_abc123",
      "version_number": 3,
      "file_size": 1048576,
      "created_at": "2025-11-14T12:00:00Z",
      "created_by": "user_123"
    }
  ],
  "total": 15,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

#### Restore Version

```http
POST /api/v1/vault/files/{file_id}/versions/{version_id}/restore
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

vault_type=real
```

**Rate Limit**: 20 requests/min per user

**Response (200 OK)**:
```json
{
  "success": true,
  "file_id": "file_abc123",
  "version_id": "v_abc123",
  "message": "Version restored successfully"
}
```

**Audit Log**: `vault.version.restored`

#### Delete Version

```http
DELETE /api/v1/vault/files/{file_id}/versions/{version_id}?vault_type=real
Authorization: Bearer <token>
```

**Rate Limit**: 20 requests/min per user

**Audit Log**: `vault.version.deleted`

---

### Trash

#### Move File to Trash

```http
POST /api/v1/vault/files/{file_id}/trash
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

vault_type=real
```

**Rate Limit**: 60 requests/min per user

**Audit Log**: `vault.file.trashed`

#### List Trash Files (with Pagination)

```http
GET /api/v1/vault/trash?vault_type=real&limit=10&offset=0
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Response (200 OK)**:
```json
{
  "data": [
    {
      "file_id": "file_abc123",
      "filename": "old_document.pdf",
      "file_size": 1048576,
      "deleted_at": "2025-11-14T10:00:00Z",
      "deleted_by": "user_123"
    }
  ],
  "total": 8,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

#### Restore from Trash

```http
POST /api/v1/vault/files/{file_id}/restore
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

vault_type=real
```

**Rate Limit**: 30 requests/min per user

**Audit Log**: `vault.file.restored`

#### Empty Trash

```http
DELETE /api/v1/vault/trash/empty?vault_type=real
Authorization: Bearer <token>
```

**Rate Limit**: 5 requests/min per user (destructive operation)

**Response (200 OK)**:
```json
{
  "success": true,
  "deleted_count": 12,
  "message": "Trash emptied successfully"
}
```

**Audit Log**: `vault.trash.emptied` with `details.count`

---

### Search

#### Advanced Search (with Pagination)

```http
GET /api/v1/vault/search?vault_type=real&query=report&mime_type=application/pdf&date_from=2025-01-01&date_to=2025-12-31&min_size=1024&max_size=10485760&limit=50&offset=0
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Query Parameters**:
- `vault_type` (required): `real` or `decoy`
- `query`: Filename search term
- `mime_type`: MIME type filter (e.g., `image`, `video`, `application/pdf`)
- `date_from`: ISO 8601 date (files created after)
- `date_to`: ISO 8601 date (files created before)
- `min_size`: Minimum file size in bytes
- `max_size`: Maximum file size in bytes
- `folder_path`: Folder path filter
- `limit`: Results per page (default: 100)
- `offset`: Skip N results (default: 0)

**Response (200 OK)**:
```json
{
  "results": [
    {
      "file_id": "file_abc123",
      "filename": "annual_report_2025.pdf",
      "file_size": 2097152,
      "mime_type": "application/pdf",
      "folder_path": "/reports",
      "created_at": "2025-06-15T09:30:00Z"
    }
  ],
  "total": 127,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

---

### Sharing

#### Create Share Link

```http
POST /api/v1/vault/files/{file_id}/share
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

vault_type=real
password=SharePass123
expires_at=2025-11-21T12:00:00Z
max_downloads=5
permissions=download
one_time=false
```

**Rate Limit**: 10 requests/min per user

**Parameters**:
- `vault_type` (required): `real` or `decoy`
- `password` (optional): Password protection
- `expires_at` (optional): ISO 8601 expiry time (default: 24h from now)
- `max_downloads` (optional): Maximum download count
- `permissions` (optional): `download` or `view` (default: `download`)
- `one_time` (optional): Boolean, forces `max_downloads=1` (default: `false`)

**Response (200 OK)**:
```json
{
  "id": "share_123",
  "share_token": "dGVzdF90b2tlbl8xMjM0NTY3ODkw...",
  "expires_at": "2025-11-21T12:00:00Z",
  "max_downloads": 5,
  "permissions": "download",
  "created_at": "2025-11-14T12:00:00Z"
}
```

**Audit Log**: `vault.share.created` (token not logged)

**Defaults**:
- If `expires_at` not provided: 24 hours from creation
- If `one_time=true` and `max_downloads` not provided: `max_downloads=1`

#### Access Share Link

```http
GET /api/v1/vault/share/{share_token}?password=SharePass123
```

**Rate Limits** (per-token IP throttles):
- 5 requests/min per share token per IP
- 50 requests/day per share token per IP

**Response (200 OK)**:
```json
{
  "id": "share_123",
  "file_id": "file_abc123",
  "filename": "document.pdf",
  "file_size": 1048576,
  "mime_type": "application/pdf",
  "requires_password": true,
  "permissions": "download",
  "download_count": 2,
  "max_downloads": 5
}
```

**Error Responses**:

| HTTP | Code | Message |
|------|------|---------|
| 401 | `password_required` | Password required |
| 401 | `password_incorrect` | Incorrect password |
| 404 | `invalid_token` | Invalid or revoked share token |
| 410 | `expired` | Share link has expired |
| 410 | `max_downloads_reached` | Download limit reached |
| 429 | `rate_limited` | Too many downloads (1 min or 24h), includes `retry_after` |

#### List Share Links

```http
GET /api/v1/vault/files/{file_id}/shares?vault_type=real
Authorization: Bearer <token>
```

**Rate Limit**: 60 requests/min per user

**Response (200 OK)**:
```json
{
  "shares": [
    {
      "id": "share_123",
      "created_at": "2025-11-14T12:00:00Z",
      "expires_at": "2025-11-21T12:00:00Z",
      "max_downloads": 5,
      "download_count": 2,
      "permissions": "download"
    }
  ]
}
```

#### Revoke Share Link

```http
DELETE /api/v1/vault/shares/{share_id}?vault_type=real
Authorization: Bearer <token>
```

**Rate Limit**: 30 requests/min per user

**Audit Log**: `vault.share.revoked`

---

### Analytics

#### Storage Trends

```http
GET /api/v1/vault/analytics/storage-trends?vault_type=real&days=30
Authorization: Bearer <token>
```

**Rate Limit**: 120 requests/min per user

**Query Parameters**:
- `vault_type` (required): `real` or `decoy`
- `days` (optional): Number of days to analyze (default: 30)

**Response (200 OK)**:
```json
{
  "trends": [
    {
      "date": "2025-11-14",
      "total_files": 145,
      "total_size_bytes": 524288000,
      "files_added": 12,
      "files_deleted": 3
    }
  ],
  "summary": {
    "current_total_files": 145,
    "current_total_size": 524288000,
    "average_file_size": 3616124,
    "growth_rate": 8.5
  }
}
```

#### Access Patterns

```http
GET /api/v1/vault/analytics/access-patterns?vault_type=real&days=30
Authorization: Bearer <token>
```

**Rate Limit**: 120 requests/min per user

**Response (200 OK)**:
```json
{
  "patterns": [
    {
      "hour": 14,
      "access_count": 87,
      "unique_files": 34
    }
  ],
  "top_files": [
    {
      "file_id": "file_abc123",
      "filename": "quarterly_report.pdf",
      "access_count": 45
    }
  ]
}
```

#### Activity Timeline

```http
GET /api/v1/vault/analytics/activity-timeline?vault_type=real&days=30
Authorization: Bearer <token>
```

**Rate Limit**: 120 requests/min per user

**Response (200 OK)**:
```json
{
  "activities": [
    {
      "timestamp": "2025-11-14T12:34:56Z",
      "action": "upload",
      "file_id": "file_abc123",
      "filename": "document.pdf",
      "user_id": "user_123",
      "details": {}
    }
  ],
  "summary": {
    "total_activities": 234,
    "uploads": 45,
    "downloads": 123,
    "deletes": 12,
    "shares": 8
  }
}
```

---

## Pagination Contract

All paginated endpoints follow this consistent response structure:

```json
{
  "data": [...],       // Array of results (or "results", "comments", "versions", etc.)
  "total": 127,        // Total count of all results
  "limit": 10,         // Results per page
  "offset": 0,         // Current offset
  "has_more": true     // Boolean: more results available
}
```

**Pagination Parameters**:
- `limit`: Number of results per page (default varies by endpoint, typically 10-100)
- `offset`: Number of results to skip

**Example**:
```http
GET /api/v1/vault/files/{file_id}/comments?limit=10&offset=20
```
Returns items 21-30 of total results.

**Endpoints with Pagination**:
- Comments: `/files/{file_id}/comments`
- Versions: `/files/{file_id}/versions`
- Trash: `/trash`
- Search: `/search`

---

## Rate Limiting

ElohimOS uses token-bucket rate limiting per user+IP. Limits are enforced per-endpoint.

### Vault Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| File download | 120 req/min | per user+IP |
| File versions (list) | 60 req/min | per user+IP |
| Version restore | 20 req/min | per user+IP |
| Version delete | 20 req/min | per user+IP |
| Move to trash | 60 req/min | per user+IP |
| Restore from trash | 30 req/min | per user+IP |
| List trash | 60 req/min | per user+IP |
| Empty trash | 5 req/min | per user+IP |
| Search | 60 req/min | per user+IP |
| Analytics (all) | 120 req/min | per user+IP |
| Comments (all ops) | 60 req/min | per user+IP |
| Share create | 10 req/min | per user+IP |
| Share list | 60 req/min | per user+IP |
| Share revoke | 30 req/min | per user+IP |

### Share Link IP Throttles

Per-token IP throttles for share access (no authentication required):

- **5 downloads/min** per share token per IP
- **50 downloads/day** per share token per IP

**Rate Limit Response (429)**:
```json
{
  "code": "rate_limited",
  "message": "Too many downloads for this link from your IP (1 min)",
  "retry_after": 60
}
```

---

## Error Codes

ElohimOS returns machine-readable error codes in responses.

### Authentication Errors

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_PASSWORD_CHANGE_REQUIRED` | 403 | Must change password before continuing |
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid username or password |
| `AUTH_TOKEN_EXPIRED` | 401 | JWT token has expired |
| `AUTH_TOKEN_INVALID` | 401 | Invalid JWT token |

### Share Link Errors

| Code | HTTP | Description |
|------|------|-------------|
| `invalid_token` | 404 | Share token not found or revoked |
| `expired` | 410 | Share link has expired |
| `max_downloads_reached` | 410 | Download limit reached |
| `password_required` | 401 | Password required for access |
| `password_incorrect` | 401 | Incorrect password |
| `rate_limited` | 429 | Too many requests (includes `retry_after`) |

### Vault Errors

| Code | HTTP | Description |
|------|------|-------------|
| `VAULT_FILE_NOT_FOUND` | 404 | File does not exist |
| `VAULT_PERMISSION_DENIED` | 403 | Insufficient permissions |
| `VAULT_QUOTA_EXCEEDED` | 413 | Storage quota exceeded |

---

## Model Preloader

ElohimOS preloads AI models on a per-user basis to optimize inference performance.

### Behavior

**Per-User Model Preloading**:
- Models are loaded into memory when a user first requests inference
- Models remain cached for the duration of the user's session
- Idle models are unloaded after 15 minutes of inactivity
- Each user can have different model preferences (configured in settings)

**Model Priority**:
1. User-specific model (if configured in preferences)
2. Team default model (if team member)
3. System default model (`llama-3.2-3b-instruct` on Metal4)

**Memory Management**:
- Maximum 3 models loaded concurrently
- LRU (Least Recently Used) eviction when limit reached
- Models are shared between users requesting the same model

**API Endpoints**:

```http
GET /api/v1/ai/models/preload-status
Authorization: Bearer <token>
```

**Response**:
```json
{
  "user_id": "user_123",
  "loaded_models": [
    {
      "model_id": "llama-3.2-3b-instruct",
      "loaded_at": "2025-11-14T12:00:00Z",
      "last_used": "2025-11-14T12:30:00Z",
      "memory_usage_mb": 4096
    }
  ],
  "preload_enabled": true,
  "session_timeout_minutes": 15
}
```

**Configuration**:

Users can configure model preferences:

```http
POST /api/v1/users/preferences
Authorization: Bearer <token>

{
  "preferred_model": "llama-3.2-3b-instruct",
  "enable_preload": true
}
```

---

## Terminal API

### POST /api/v1/terminal/socket/start

Start a Unix socket listener for terminal bridge integration.

**Permission Required**: `code.terminal`

**Request Body** (JSON):
```json
{
  "terminal_app": "iterm" | "warp" | "unknown",  // optional
  "workspace_root": "/Users/..."                 // optional
}
```

**Response**:
```json
{
  "terminal_id": "term_xxxxxxxx",
  "socket_path": "/absolute/path/.neutron_data/term_term_xxxxx.sock"
}
```

**Notes**:
- Starts a non-blocking Unix socket listener
- External terminal or script can connect and send bytes to stream output into ElohimOS
- Socket path is always under `PATHS.data_dir`
- Path validation enforced to prevent directory traversal
- Socket cleanup handled automatically on disconnect
- See `apps/backend/api/services/terminal_bridge.py` for implementation details

**Example**:
```http
POST /api/v1/terminal/socket/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "terminal_app": "iterm",
  "workspace_root": "/Users/indiedevhipps/Documents/ElohimOS"
}
```

**Error Responses**:
- `403 Forbidden` - Missing `code.terminal` permission
- `500 Internal Server Error` - Socket creation failed

---

## Changelog

- **2025-11-14**: Added share link hardening (IP throttles, one-time links, default 24h TTL)
- **2025-11-14**: Added comprehensive test coverage (lifecycle, auth, analytics, pagination)
- **2025-11-14**: Added rate limiting to vault endpoints
- **2025-11-13**: Added forced password change flow
- **2025-11-13**: Added per-user model preloader

---

## Support

For API support and questions:
- GitHub Issues: https://github.com/hipps-joshua/ElohimOS/issues
- Documentation: `/docs`
