# Vault Wiring Complete ✓

## Overview
Step 5 (Vault) has been fully implemented with all endpoints, models, service layer, and state management wired to the FastAPI backend with secure file storage.

## Components Created

### 1. Vault Models
**Location**: `apps/native/Shared/Models/VaultModels.swift`

#### VaultFolder
```swift
struct VaultFolder: Codable, Identifiable {
    let id: String
    let folderName: String
    let folderPath: String
    let parentPath: String
    let createdAt: String

    var pathComponents: [String]  // For breadcrumb navigation
}
```

#### VaultFile
```swift
struct VaultFile: Codable, Identifiable {
    let id: String
    let filename: String
    let fileSize: Int
    let mimeType: String
    let folderPath: String
    let createdAt: String

    var fileExtension: String      // e.g., "pdf"
    var formattedSize: String       // e.g., "1.2 MB"
    var fileCategory: FileCategory  // .image, .pdf, .document, etc.
}
```

#### VaultListResponse
```swift
struct VaultListResponse: Codable {
    let folders: [VaultFolder]
    let files: [VaultFile]
}
```

#### UnlockResponse
```swift
struct UnlockResponse: Codable {
    let success: Bool
}
```

#### VaultType
```swift
enum VaultType: String {
    case primary = "primary"
    case decoy = "decoy"
    case team = "team"
}
```

### 2. ApiClient Extensions
**Location**: `apps/native/Shared/Networking/APIClient.swift`

Added `extraHeaders` parameter to all convenience methods:
- `request(path:method:jsonBody:authenticated:extraHeaders:)`
- `multipart(path:fileField:fileURL:parameters:authenticated:extraHeaders:)`
- `requestRaw(path:method:jsonBody:authenticated:extraHeaders:)`

Allows passing custom headers like `X-Vault-Passphrase`.

### 3. VaultService
**Location**: `apps/native/Shared/Services/VaultService.swift`

All endpoints wired:

| Method | Endpoint | Returns |
|--------|----------|---------|
| `unlock(password:requireTouchId:)` | `POST /v1/vault/unlock` | `Bool` |
| `list(folderPath:vaultType:passphrase:)` | `GET /v1/vault/files?folder_path=...&vault_type=...` | `VaultListResponse` |
| `download(fileId:vaultType:passphrase:)` | `GET /v1/vault/files/{id}/download?vault_type=...` | `Data` |
| `upload(fileURL:folderPath:vaultType:passphrase:)` | `POST /v1/vault/files?vault_type=...&folder_path=...` | `VaultFile` |
| `createFolder(folderPath:vaultType:passphrase:)` | `POST /v1/vault/folders` | `EmptyResponse` |
| `deleteFile(fileId:vaultType:passphrase:)` | `DELETE /v1/vault/files/{id}?vault_type=...` | `EmptyResponse` |
| `deleteFolder(folderPath:vaultType:passphrase:)` | `DELETE /v1/vault/folders` | `EmptyResponse` |

#### Passphrase Header
All authenticated vault operations include:
```
X-Vault-Passphrase: {passphrase}
```

### 4. VaultStore
**Location**: `apps/native/Shared/Stores/VaultStore.swift`

State management with secure unlock and file operations:

#### Published State
```swift
@Published var unlocked: Bool = false
@Published var vaultType: String = "primary"  // "primary" | "decoy" | "team"
@Published var currentFolder: String = "/"
@Published var folders: [VaultFolder] = []
@Published var files: [VaultFile] = []
@Published var previewFile: VaultFile?
@Published var previewData: Data?
@Published var isLoading = false
@Published var isUploading = false
@Published var error: String?
```

#### Private State
```swift
private var passphrase: String?  // In-memory only, never persisted
```

#### Public Methods

**Unlock/Lock**
- `unlock(password:requireTouchId:)` - Unlocks vault, stores passphrase, loads root
- `lock()` - Locks vault, clears passphrase and state

**Navigation**
- `load(folderPath:)` - Loads folder contents
- `setFolder(path:)` - Navigates to specific folder
- `navigateUp()` - Goes to parent folder

**File Operations**
- `download(file:)` - Downloads file data
- `preview(file:)` - Sets preview file and downloads data
- `closePreview()` - Clears preview
- `upload(fileURL:)` - Uploads file to current folder
- `deleteFile(_:)` - Deletes file

**Folder Operations**
- `createFolder(name:)` - Creates subfolder in current folder
- `deleteFolder(_:)` - Deletes folder

**Vault Mode**
- `switchVaultType(_:)` - Switches between primary/decoy/team vaults

**Helpers**
- `breadcrumbComponents` - Array of folder names for breadcrumbs
- `pathForBreadcrumb(index:)` - Builds path from breadcrumb index
- `clear()` - Resets all state (call on logout)

## API Endpoints Wired

### Unlock
```
POST /api/v1/vault/unlock
Body: { password: String, require_touch_id: Bool }
→ { success: Bool }
```

### List Files & Folders
```
GET /api/v1/vault/files?folder_path={path}&vault_type={type}
Headers: X-Vault-Passphrase: {passphrase}
→ { folders: [VaultFolder], files: [VaultFile] }
```

### Download File
```
GET /api/v1/vault/files/{id}/download?vault_type={type}
Headers: X-Vault-Passphrase: {passphrase}
→ Blob (Data)
```

### Upload File
```
POST /api/v1/vault/files?vault_type={type}&folder_path={path}
Headers: X-Vault-Passphrase: {passphrase}
Content-Type: multipart/form-data
Field: file
→ VaultFile
```

### Create Folder
```
POST /api/v1/vault/folders
Headers: X-Vault-Passphrase: {passphrase}
Body: { folder_path: String, vault_type: String }
→ EmptyResponse
```

### Delete File
```
DELETE /api/v1/vault/files/{id}?vault_type={type}
Headers: X-Vault-Passphrase: {passphrase}
→ EmptyResponse
```

### Delete Folder
```
DELETE /api/v1/vault/folders
Headers: X-Vault-Passphrase: {passphrase}
Body: { folder_path: String, vault_type: String }
→ EmptyResponse
```

## UI Binding Checklist

### Locked View
✓ **Show when**: `!vaultStore.unlocked`
✓ **Password field**: Text input
✓ **Touch ID toggle**: Optional biometric unlock
✓ **Unlock button**: `vaultStore.unlock(password:requireTouchId:)`
✓ **Loading**: `vaultStore.isLoading`
✓ **Error**: `vaultStore.error`

### Vault Content View (Unlocked)
✓ **Breadcrumbs**:
  - Components: `vaultStore.breadcrumbComponents`
  - Click: `vaultStore.setFolder(path:)`
  - Up arrow: `vaultStore.navigateUp()`

✓ **Folders list**: `vaultStore.folders`
  - Click to navigate: `setFolder(folder.folderPath)`
  - Delete: `deleteFolder(folder)`

✓ **Files grid/list**: `vaultStore.files`
  - Click to preview: `preview(file)`
  - Download: `download(file)`
  - Delete: `deleteFile(file)`

✓ **Upload button**:
  - File picker → `upload(fileURL:)`
  - Progress: `isUploading`

✓ **New folder button**:
  - Show prompt for name
  - Create: `createFolder(name:)`

✓ **Vault mode selector**:
  - Options: primary, decoy, team
  - Selected: `vaultType`
  - Change: `switchVaultType(_:)`

✓ **Lock button**: `vaultStore.lock()`

### File Preview
✓ **Show when**: `previewFile != nil`
✓ **File info**: `vaultStore.previewFile`
✓ **Data**: `vaultStore.previewData`
✓ **Close**: `closePreview()`
✓ **Render by type**:
  - Images: Use `previewData` with Image
  - PDFs: Use PDFKit
  - Text: Decode as String
  - Other: Show download button

## State Flow Examples

### Unlock Vault → Load Files
```swift
// 1. User enters password
await vaultStore.unlock(password: "secret123", requireTouchId: false)
// → unlocked = true, passphrase stored, root folder loaded

// 2. Files displayed
let files = vaultStore.files
let folders = vaultStore.folders
```

### Navigate Folders
```swift
// 1. User in root folder ("/")
let current = vaultStore.currentFolder  // "/"

// 2. Click on folder "Documents"
await vaultStore.setFolder(path: "/Documents")
// → currentFolder = "/Documents", loads contents

// 3. Navigate up
await vaultStore.navigateUp()
// → back to "/"
```

### Upload File
```swift
// 1. User selects file
let fileURL = selectedFileURL

// 2. Upload
await vaultStore.upload(fileURL: fileURL)
// → file uploaded to currentFolder
// → folder reloaded, new file appears in list
```

### Preview and Download
```swift
// 1. User clicks file
await vaultStore.preview(file: selectedFile)
// → previewFile set, previewData downloaded

// 2. Display preview
if let data = vaultStore.previewData,
   let file = vaultStore.previewFile {
    switch file.fileCategory {
    case .image:
        Image(data: data)
    case .pdf:
        PDFView(data: data)
    // ...
    }
}

// 3. Close preview
vaultStore.closePreview()
// → previewFile = nil, previewData = nil
```

### Create and Delete Folders
```swift
// 1. Create subfolder
await vaultStore.createFolder(name: "Private")
// → folder created at "/Private"
// → folder list reloaded

// 2. Delete folder
await vaultStore.deleteFolder(folder)
// → folder deleted
// → removed from local list
```

### Switch Vault Types
```swift
// 1. Switch to decoy vault
await vaultStore.switchVaultType("decoy")
// → vaultType = "decoy"
// → currentFolder reset to "/"
// → new vault contents loaded
```

### Lock Vault
```swift
// 1. User locks vault
vaultStore.lock()
// → unlocked = false
// → passphrase cleared
// → all state reset
```

## Security Features

### Passphrase Storage
- **In-memory only**: Never persisted to disk
- **Cleared on lock**: Immediately cleared when vault locked
- **Cleared on logout**: Call `clear()` on app logout

### Vault Types
- **Primary**: Main encrypted vault
- **Decoy**: Fake vault with decoy data
- **Team**: Shared team vault

### File Categories
Auto-detected from file extension:
- Images: jpg, png, gif, etc.
- PDFs: pdf
- Documents: doc, docx, txt, etc.
- Spreadsheets: xls, xlsx, csv
- Videos: mp4, mov, avi
- Audio: mp3, wav, aac
- Archives: zip, rar, 7z
- Other: Everything else

## Error Handling

All errors surfaced via `@Published var error: String?`:
- Unlock failures (wrong password)
- Network errors
- 401/403 auth errors
- File not found
- Permission denied
- Upload failures
- Delete failures

UI should bind to `vaultStore.error` for toast/banner display.

## Integration with ContentView

Add to ContentView (if needed):
```swift
@StateObject private var vaultStore = VaultStore.shared

// In .authenticated case:
MainAppView()
    .environmentObject(vaultStore)

// On logout:
.onChange(of: authStore.authState) { _, newState in
    if newState == .welcome {
        vaultStore.clear()
    }
}
```

## File Size Formatting

VaultFile includes `formattedSize`:
```swift
let file: VaultFile
print(file.formattedSize)  // "1.2 MB", "458 KB", etc.
```

Uses `ByteCountFormatter` for human-readable sizes.

## Breadcrumb Navigation

Helper methods for breadcrumb UI:
```swift
// Get breadcrumb components
let crumbs = vaultStore.breadcrumbComponents
// e.g., "/Documents/Work/Projects" → ["Documents", "Work", "Projects"]

// Build path from breadcrumb index
let path = vaultStore.pathForBreadcrumb(index: 1)
// e.g., index 1 → "/Documents/Work"

// Navigate to breadcrumb
await vaultStore.setFolder(path: path)
```

## Next Steps

Vault is fully wired! Ready for:

### Step 6: Settings
- Saved queries: `GET/POST/PUT/DELETE /v1/settings/saved-queries`
- Metal4 monitoring: `GET /v1/monitoring/metal4`
- User preferences
- API keys management

### Optional Vault Enhancements (Future)
- Rename file/folder
- Move file/folder
- Tags/labels
- File versions
- Trash/recovery
- Analytics
- Sharing/permissions

## Notes

- Passphrase **never** persisted - in-memory only
- `X-Vault-Passphrase` header used for all vault operations
- Folder paths URL-encoded for special characters
- Auto-reload after create/upload/delete operations
- File category auto-detected from extension
- Breadcrumb navigation fully functional
- Support for 3 vault types (primary, decoy, team)
- All snake_case API fields auto-converted
- All auth requests auto-inject Bearer token
- Extra headers support added to all ApiClient methods
