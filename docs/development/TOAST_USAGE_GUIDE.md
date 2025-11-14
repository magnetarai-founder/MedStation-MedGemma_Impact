# Toast Notification Usage Guide

**ElohimOS uses `react-hot-toast` for all toast notifications.**

---

## ✅ Recommended: Use the Toast Wrapper

ElohimOS provides a centralized toast wrapper at `src/lib/toast.tsx` for consistent styling and behavior.

### Import

```typescript
import { showToast } from '@/lib/toast'
```

### Basic Usage

```typescript
// Success
showToast.success('File uploaded successfully')

// Error
showToast.error('Failed to save changes')

// Info
showToast.info('New version available')

// Warning
showToast.warning('Disk space running low')

// Loading (with auto-dismiss on complete)
const toastId = showToast.loading('Processing...')
// Later: showToast.dismiss(toastId)
```

### Advanced Features

#### Promise-based Toast
```typescript
showToast.promise(
  uploadFile(),
  {
    loading: 'Uploading...',
    success: 'Upload complete',
    error: (err) => `Upload failed: ${err.message}`,
  }
)
```

#### Undo Toast (5s default)
```typescript
import { showUndoToast } from '@/lib/toast'

showUndoToast(
  'File deleted',
  async () => {
    await restoreFile(fileId)
  },
  { duration: 5000, undoText: 'Undo' }
)
```

#### Action Toast
```typescript
import { showActionToast } from '@/lib/toast'

showActionToast(
  'Export ready',
  'Download',
  () => window.open(downloadUrl),
  { type: 'success', duration: 4000 }
)
```

#### Specialized Toasts
```typescript
import { showChatNotification, showWorkflowNotification, showBackupNotification } from '@/lib/toast'

// Chat notification
showChatNotification('Alice', 'Hey, check this out!', () => openChat())

// Workflow status
showWorkflowNotification('Data Sync', 'completed', () => viewWorkflow())

// Backup status
showBackupNotification('completed', () => restoreBackup())
```

---

## ⚠️ Direct Import (Avoid)

While importing `react-hot-toast` directly works, it bypasses centralized theming:

```typescript
// ❌ Avoid - no consistent styling
import toast from 'react-hot-toast'
toast.success('Done')

// ✅ Prefer - centralized styling
import { showToast } from '@/lib/toast'
showToast.success('Done')
```

---

## 🚫 Banned Imports

**Do NOT use `sonner`**. The project uses `react-hot-toast`.

```typescript
// ❌ BANNED - Will fail CI
import { toast } from 'sonner'

// ✅ Use react-hot-toast wrapper instead
import { showToast } from '@/lib/toast'
```

CI will reject PRs with `sonner` imports.

---

## Configuration

The `<Toaster />` component is configured once in `src/App.tsx`:

```typescript
<Toaster
  position="bottom-right"
  toastOptions={{
    duration: 3000,
    style: {
      background: '#363636',
      color: '#fff',
    },
    success: {
      duration: 3000,
      iconTheme: {
        primary: '#10b981',
        secondary: '#fff',
      },
    },
    error: {
      duration: 4000,
      iconTheme: {
        primary: '#ef4444',
        secondary: '#fff',
      },
    },
  }}
/>
```

**Do not add additional `<Toaster />` instances** - it's a singleton.

---

## Migration Guide

### From Sonner

```diff
- import { toast } from 'sonner'
+ import { showToast } from '@/lib/toast'

- toast.success('Done')
+ showToast.success('Done')

- toast.error('Failed')
+ showToast.error('Failed')

- toast('Info message')
+ showToast.info('Info message')
```

### From Direct react-hot-toast

```diff
- import toast from 'react-hot-toast'
+ import { showToast } from '@/lib/toast'

- toast.success('Done')
+ showToast.success('Done')

- toast.loading('Processing...')
+ showToast.loading('Processing...')

- toast.dismiss(id)
+ showToast.dismiss(id)
```

---

## Styling Customization

To change toast appearance globally, edit `src/lib/toast.tsx`:

```typescript
export const showToast = {
  success: (message: string, duration: number = 3000) => {
    return toast.success(message, {
      duration,
      style: {
        background: 'rgba(16, 185, 129, 0.1)', // Change colors here
        color: '#059669',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        padding: '16px',
        borderRadius: '12px',
      },
      // ...
    })
  },
  // ...
}
```

---

## CI Checks

GitHub Actions runs these checks on every PR:

1. **Banned imports**: Fails if `sonner` is imported
2. **Single Toaster**: Fails if multiple `<Toaster />` instances found
3. **Direct imports**: Informational warning (not blocking) if files import `react-hot-toast` directly

---

## Best Practices

1. ✅ **Use the wrapper** (`showToast`) for consistent styling
2. ✅ **Keep Toaster singleton** in `App.tsx`
3. ✅ **Use specialized toasts** for chat, workflows, backups
4. ✅ **Use undo toasts** for reversible actions
5. ❌ **Don't import sonner** - banned
6. ⚠️ **Avoid direct imports** - use wrapper instead

---

## Examples

### File Upload
```typescript
const handleUpload = async (file: File) => {
  const toastId = showToast.loading('Uploading file...')

  try {
    await uploadFile(file)
    showToast.dismiss(toastId)
    showToast.success('File uploaded successfully')
  } catch (error) {
    showToast.dismiss(toastId)
    showToast.error('Upload failed')
  }
}
```

### Delete with Undo
```typescript
const handleDelete = async (fileId: string) => {
  await deleteFile(fileId)

  showUndoToast(
    'File deleted',
    async () => {
      await restoreFile(fileId)
      refreshFileList()
    },
    { duration: 5000 }
  )
}
```

### Export with Download Action
```typescript
const handleExport = async () => {
  const exportUrl = await createExport()

  showActionToast(
    'Export ready',
    'Download',
    () => window.open(exportUrl, '_blank'),
    { type: 'success', duration: 6000 }
  )
}
```

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/hipps-joshua/ElohimOS/issues
- Toast wrapper source: `apps/frontend/src/lib/toast.tsx`
