# Database Workspace Wiring Complete ✓

## Overview
Step 2 (Database Workspace) has been fully implemented with all endpoints, models, service layer, and state management wired to the FastAPI backend.

## Components Created

### 1. AnyCodable Helper
**Location**: `apps/native/Shared/Models/AnyCodable.swift`
- Type-erased Codable for dynamic JSON handling
- Supports: null, bool, int, double, string, arrays, dictionaries
- Helper accessors: `stringValue`, `intValue`, `doubleValue`, etc.
- Used for preview data: `[[String: AnyCodable]]`

### 2. Database Models
**Location**: `apps/native/Shared/Models/DatabaseModels.swift`

#### SessionResponse
```swift
struct SessionResponse: Codable {
    let sessionId: String
    let createdAt: String
}
```

#### FileUploadResponse
```swift
struct FileUploadResponse: Codable {
    let filename: String
    let sizeMb: Double
    let rowCount: Int
    let columnCount: Int
    let columns: [FileColumn]
    let preview: [[String: AnyCodable]]?
}

struct FileColumn: Codable {
    let originalName: String
    let cleanName: String
    let dtype: String
    let nonNullCount: Int
    let nullCount: Int
}
```

#### JsonUploadResponse
```swift
struct JsonUploadResponse: Codable {
    let filename: String
    let sizeMb: Double
    let objectCount: Int
    let columns: [String]
    let preview: [[String: AnyCodable]]
}
```

#### QueryResponse
```swift
struct QueryResponse: Codable {
    let queryId: String
    let rowCount: Int
    let columnCount: Int
    let columns: [String]
    let executionTimeMs: Int
    let preview: [[String: AnyCodable]]
    let hasMore: Bool
    var isPreviewOnly: Bool?
    let originalTotalRows: Int?
}
```

#### QueryHistoryItem
```swift
struct QueryHistoryItem: Codable, Identifiable {
    let id: String
    let query: String
    let timestamp: String
    let executionTime: Int?
    let rowCount: Int?
    let status: String // "success" | "error"
}
```

#### JsonConvertResponse
```swift
struct JsonConvertResponse: Codable {
    let success: Bool
    let outputFile: String?
    let totalRows: Int
    let sheets: [String]?
    let columns: [String]?
    let preview: [[String: AnyCodable]]
    let isPreviewOnly: Bool?
}
```

### 3. ApiClient Extensions
**Location**: `apps/native/Shared/Networking/APIClient.swift`

Added three convenience methods:

#### request(path:method:jsonBody:)
- Accepts `[String: Any]` dictionary for JSON body
- Returns decoded `T: Decodable`
- Uses `JSONSerialization` for flexible payloads

#### multipart(path:fileField:fileURL:parameters:)
- Multipart file upload
- Auto-detects MIME type (json, csv, xlsx, xls, parquet)
- Returns decoded `T: Decodable`
- Builds proper multipart boundary

#### requestRaw(path:method:jsonBody:)
- Returns raw `Data` for blobs/downloads
- Used for export and download endpoints

### 4. DatabaseService
**Location**: `apps/native/Shared/Services/DatabaseService.swift`

All endpoints wired:

| Method | Endpoint | Returns |
|--------|----------|---------|
| `createSession()` | `POST /sessions/create` | `SessionResponse` |
| `deleteSession(id:)` | `DELETE /sessions/{id}` | `EmptyResponse` |
| `uploadFile(sessionId:fileURL:)` | `POST /sessions/{id}/upload` | `FileUploadResponse` |
| `uploadJson(sessionId:fileURL:)` | `POST /sessions/{id}/json/upload` | `JsonUploadResponse` |
| `executeQuery(sessionId:sql:limit:isPreview:)` | `POST /sessions/{id}/query` | `QueryResponse` |
| `convertJson(sessionId:json:options:)` | `POST /sessions/{id}/json/convert` | `JsonConvertResponse` |
| `exportResults(sessionId:queryId:format:filename:)` | `POST /sessions/{id}/export` | `Data` |
| `downloadJsonResult(sessionId:format:)` | `GET /sessions/{id}/json/download?format=...` | `Data` |
| `fetchQueryHistory(sessionId:)` | `GET /sessions/{id}/query-history` | `[QueryHistoryItem]` |
| `deleteHistoryItem(sessionId:historyId:)` | `DELETE /sessions/{id}/query-history/{id}` | `EmptyResponse` |

### 5. DatabaseStore
**Location**: `apps/native/Shared/Stores/DatabaseStore.swift`

State management with `@MainActor` and `@Published` properties:

#### Published State
```swift
@Published private(set) var sessionId: String?
@Published private(set) var currentFile: FileUploadResponse?
@Published private(set) var currentQuery: QueryResponse?
@Published var contentType: ContentType = .sql  // .sql | .json
@Published private(set) var isExecuting: Bool = false
@Published private(set) var isUploading: Bool = false
@Published var error: String?
```

#### Public Methods
- `createSession()` - Creates fresh session on auth
- `deleteSession()` - Cleans up session
- `uploadFile(url:)` - Handles CSV/Excel/JSON uploads
  - JSON: normalizes to `FileUploadResponse` shape
  - Sets `contentType` appropriately
- `previewQuery(sql:)` - Executes with limit 10, marks preview-only
- `runQuery(sql:limit:isPreview:)` - Full query execution
- `convertJson(jsonText:)` - Converts JSON, normalizes to `QueryResponse`
- `exportResults(format:filename:)` - Exports results (blocks if preview-only)
- `downloadJsonResult(format:)` - Downloads JSON in specified format
- `fetchHistory()` - Returns history items
- `deleteHistoryItem(_:)` - Deletes history item

#### Smart Normalization
- JSON uploads/converts → normalized to `FileUploadResponse` for sidebar
- JSON converts → normalized to `QueryResponse` for results table
- Auto-sets `isPreviewOnly` flag for preview queries

### 6. ContentView Integration
**Location**: `apps/native/macOS/ContentView.swift`

Wiring:
```swift
@StateObject private var databaseStore = DatabaseStore.shared

// On auth success:
.task {
    await authStore.bootstrap()
    if authStore.authState == .authenticated {
        await databaseStore.createSession()
    }
}

// Watch for auth state changes:
.onChange(of: authStore.authState) { _, newState in
    if newState == .authenticated {
        Task { await databaseStore.createSession() }
    }
}

// Pass to MainAppView:
.environmentObject(databaseStore)
```

## API Endpoints Wired

### Session Management
```
POST /api/sessions/create
→ { session_id: String, created_at: String }

DELETE /api/sessions/{id}
→ EmptyResponse
```

### File Uploads
```
POST /api/sessions/{id}/upload
Content-Type: multipart/form-data
Field: file (CSV/Excel)
→ FileUploadResponse

POST /api/sessions/{id}/json/upload
Content-Type: multipart/form-data
Field: file (JSON)
→ JsonUploadResponse
```

### Query Execution
```
POST /api/sessions/{id}/query
Body: { sql: String, limit?: Int, is_preview?: Bool }
→ QueryResponse

POST /api/sessions/{id}/json/convert
Body: { json_data: String, options: [String: Any] }
→ JsonConvertResponse
```

### Export & Download
```
POST /api/sessions/{id}/export
Body: { query_id: String, format: "excel"|"csv"|"parquet"|"json", filename?: String }
→ Blob (Data)

GET /api/sessions/{id}/json/download?format=excel|csv|tsv|parquet
→ Blob (Data)
```

### Query History
```
GET /api/sessions/{id}/query-history
→ { history: [QueryHistoryItem] }

DELETE /api/sessions/{id}/query-history/{historyId}
→ EmptyResponse
```

## UI Binding Checklist

✓ **On auth success**: `createSession()` called automatically
✓ **Upload buttons**: Call `databaseStore.uploadFile(url:)`
✓ **Editor "Preview"**: Call `databaseStore.previewQuery(sql:)`
✓ **Editor "Run"**: Call `databaseStore.runQuery(sql:)`
✓ **JSON mode**: Call `databaseStore.convertJson(jsonText:)`
✓ **Export button**: Call `databaseStore.exportResults(format:)` (auto-disabled if preview-only)
✓ **History modal**: Call `databaseStore.fetchHistory()`, delete via `deleteHistoryItem(_:)`
✓ **Download JSON**: Call `databaseStore.downloadJsonResult(format:)`

## State Flow Examples

### CSV Upload → Preview → Run → Export
```swift
// 1. Upload CSV
await databaseStore.uploadFile(url: csvFileURL)
// → currentFile set, contentType = .sql

// 2. Preview query
await databaseStore.previewQuery(sql: "SELECT * FROM data")
// → currentQuery set, isPreviewOnly = true

// 3. Run full query
await databaseStore.runQuery(sql: "SELECT * FROM data")
// → currentQuery set, isPreviewOnly = false

// 4. Export
let data = await databaseStore.exportResults(format: "excel")
// → Returns blob, save to disk
```

### JSON Upload → Convert → Download
```swift
// 1. Upload JSON
await databaseStore.uploadFile(url: jsonFileURL)
// → currentFile normalized, contentType = .json

// 2. Convert JSON
await databaseStore.convertJson(jsonText: editorContent)
// → currentQuery normalized, currentFile columns updated

// 3. Download result
let data = await databaseStore.downloadJsonResult(format: "excel")
// → Returns blob
```

## Error Handling

All errors are surfaced via `@Published var error: String?`:
- Network errors
- API errors (4xx, 5xx)
- Validation errors (no session, no file uploaded, etc.)
- Decoding errors

UI can bind to `databaseStore.error` for toast/alert display.

## Next Steps

Database workspace is fully wired! Ready for:

### Step 3: Chat Workspace
- Sessions: `GET/POST /api/v1/chat/sessions`
- Messages: `POST /api/v1/chat/sessions/{id}/messages` (SSE streaming)
- Attachments: `POST /api/v1/chat/sessions/{id}/upload`
- Model selection: `PATCH /api/v1/chat/sessions/{id}/model`
- Token meter: `GET /api/v1/chat/sessions/{id}/tokens`

### Step 4: Workflows
- List: `GET /api/v1/workflows`
- Templates: `GET /api/v1/workflow/templates`
- Save/Run: `POST /api/v1/automation/save`, `POST /api/v1/automation/run`
- Queue: Work items endpoints
- Analytics: `GET /api/v1/workflows/{id}/analytics`

### Step 5: Vault
- Unlock: `POST /api/v1/vault/unlock`
- Files: `GET /api/v1/vault/files`, `GET /api/v1/vault/files/{id}/download`
- Upload: `POST /api/v1/vault/files`
- Folders: `GET /api/v1/vault/folders`, `POST /api/v1/vault/folders`

### Step 6: Settings
- Saved queries: `GET/POST/PUT/DELETE /api/v1/settings/saved-queries`
- Metal4 monitoring: `GET /api/v1/monitoring/metal4`

## Notes

- All snake_case API fields auto-converted via `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase`
- All auth requests auto-inject `Authorization: Bearer <token>`
- Session auto-created on auth, auto-cleaned on logout
- Content type switching (SQL vs JSON) handled automatically
- Preview-only flag prevents accidental exports
- All file paths use `apps/native/Shared/` for cross-platform compatibility
