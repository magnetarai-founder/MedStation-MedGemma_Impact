/**
 * Trash Bin Component
 *
 * 30-day trash system for vault items
 * Soft delete with restoration capability
 */

import { useState } from 'react'
import {
  Trash2,
  RotateCcw,
  XCircle,
  FileText,
  File,
  Folder,
  Clock,
  AlertTriangle,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'

interface TrashItem {
  id: string
  user_id: string
  vault_type: string
  item_type: 'document' | 'file' | 'folder'
  item_id: string
  item_name: string
  deleted_at: string
  permanent_delete_at: string
  original_data: string
}

interface TrashStats {
  total_items: number
  document_count: number
  file_count: number
  folder_count: number
  total_size_bytes: number
  oldest_item_date: string | null
}

interface TrashBinProps {
  userId: string
  vaultType: 'real' | 'decoy'
  onItemRestored?: (itemId: string) => void
  onItemDeleted?: (itemId: string) => void
}

export function TrashBin({ userId, vaultType, onItemRestored, onItemDeleted }: TrashBinProps) {
  const [trashItems, setTrashItems] = useState<TrashItem[]>([])
  const [stats, setStats] = useState<TrashStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [restoringIds, setRestoringIds] = useState<Set<string>>(new Set())
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set())

  // Load trash items
  async function loadTrashItems() {
    setLoading(true)
    try {
      // TODO: Replace with actual API call
      // const response = await api.getTrashItems(userId, vaultType)
      // setTrashItems(response.items)
      // setStats(response.stats)

      // Mock data for now
      await new Promise((resolve) => setTimeout(resolve, 500))

      const mockItems: TrashItem[] = [
        {
          id: 'trash_doc1',
          user_id: userId,
          vault_type: vaultType,
          item_type: 'document',
          item_id: 'doc1',
          item_name: 'Medical Records 2024.txt',
          deleted_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
          permanent_delete_at: new Date(Date.now() + 28 * 24 * 60 * 60 * 1000).toISOString(),
          original_data: '{}',
        },
        {
          id: 'trash_file1',
          user_id: userId,
          vault_type: vaultType,
          item_type: 'file',
          item_id: 'file1',
          item_name: 'family_photo.jpg',
          deleted_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          permanent_delete_at: new Date(Date.now() + 25 * 24 * 60 * 60 * 1000).toISOString(),
          original_data: '{}',
        },
      ]

      setTrashItems(mockItems)
      setStats({
        total_items: 2,
        document_count: 1,
        file_count: 1,
        folder_count: 0,
        total_size_bytes: 0,
        oldest_item_date: mockItems[1].deleted_at,
      })
    } catch (err) {
      toast.error(`Failed to load trash: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  // Restore item from trash
  async function handleRestore(item: TrashItem) {
    setRestoringIds((prev) => new Set(prev).add(item.id))

    try {
      // TODO: Replace with actual API call
      // await api.restoreFromTrash(item.id, userId, vaultType)

      // Mock delay
      await new Promise((resolve) => setTimeout(resolve, 500))

      toast.success(`Restored ${item.item_name}`)
      setTrashItems((prev) => prev.filter((i) => i.id !== item.id))
      onItemRestored?.(item.item_id)

      // Update stats
      if (stats) {
        setStats({
          ...stats,
          total_items: stats.total_items - 1,
          document_count: item.item_type === 'document' ? stats.document_count - 1 : stats.document_count,
          file_count: item.item_type === 'file' ? stats.file_count - 1 : stats.file_count,
          folder_count: item.item_type === 'folder' ? stats.folder_count - 1 : stats.folder_count,
        })
      }
    } catch (err) {
      toast.error(`Failed to restore: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRestoringIds((prev) => {
        const newSet = new Set(prev)
        newSet.delete(item.id)
        return newSet
      })
    }
  }

  // Permanently delete item
  async function handlePermanentDelete(item: TrashItem) {
    if (
      !confirm(
        `Permanently delete "${item.item_name}"?\n\nThis action cannot be undone. The item will be permanently removed.`
      )
    ) {
      return
    }

    setDeletingIds((prev) => new Set(prev).add(item.id))

    try {
      // TODO: Replace with actual API call
      // await api.permanentlyDelete(item.id, userId, vaultType)

      // Mock delay
      await new Promise((resolve) => setTimeout(resolve, 500))

      toast.success(`Permanently deleted ${item.item_name}`)
      setTrashItems((prev) => prev.filter((i) => i.id !== item.id))
      onItemDeleted?.(item.item_id)

      // Update stats
      if (stats) {
        setStats({
          ...stats,
          total_items: stats.total_items - 1,
          document_count: item.item_type === 'document' ? stats.document_count - 1 : stats.document_count,
          file_count: item.item_type === 'file' ? stats.file_count - 1 : stats.file_count,
          folder_count: item.item_type === 'folder' ? stats.folder_count - 1 : stats.folder_count,
        })
      }
    } catch (err) {
      toast.error(`Failed to delete: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDeletingIds((prev) => {
        const newSet = new Set(prev)
        newSet.delete(item.id)
        return newSet
      })
    }
  }

  // Empty entire trash
  async function handleEmptyTrash() {
    if (
      !confirm(
        `Empty trash completely?\n\nThis will permanently delete all ${stats?.total_items || 0} items. This action cannot be undone.`
      )
    ) {
      return
    }

    setLoading(true)

    try {
      // TODO: Replace with actual API call
      // await api.emptyTrash(userId, vaultType)

      // Mock delay
      await new Promise((resolve) => setTimeout(resolve, 1000))

      const count = trashItems.length
      toast.success(`Emptied trash (${count} items deleted)`)
      setTrashItems([])
      setStats({
        total_items: 0,
        document_count: 0,
        file_count: 0,
        folder_count: 0,
        total_size_bytes: 0,
        oldest_item_date: null,
      })
    } catch (err) {
      toast.error(`Failed to empty trash: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  // Get icon for item type
  function getItemIcon(itemType: string) {
    switch (itemType) {
      case 'document':
        return FileText
      case 'file':
        return File
      case 'folder':
        return Folder
      default:
        return File
    }
  }

  // Calculate days until permanent deletion
  function getDaysUntilDeletion(permanentDeleteAt: string): number {
    const now = new Date()
    const deleteDate = new Date(permanentDeleteAt)
    const diffMs = deleteDate.getTime() - now.getTime()
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
    return Math.max(0, diffDays)
  }

  // Format date
  function formatDate(dateStr: string): string {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      return 'Today'
    } else if (diffDays === 1) {
      return 'Yesterday'
    } else if (diffDays < 7) {
      return `${diffDays} days ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  // Load items on mount
  useState(() => {
    loadTrashItems()
  })

  if (loading && trashItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-gray-400 animate-spin mb-3" />
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading trash...</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with stats */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Trash Bin</h3>
          {stats && stats.total_items > 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {stats.total_items} item{stats.total_items !== 1 ? 's' : ''} • Auto-delete after 30
              days
            </p>
          )}
        </div>

        {stats && stats.total_items > 0 && (
          <button
            onClick={handleEmptyTrash}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            <span>Empty Trash</span>
          </button>
        )}
      </div>

      {/* Warning banner */}
      {stats && stats.total_items > 0 && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-yellow-900 dark:text-yellow-100">
            <p className="font-medium mb-1">Items will be permanently deleted after 30 days</p>
            <p className="text-yellow-700 dark:text-yellow-300">
              Restore important items before they are automatically removed. Permanent deletion
              cannot be undone.
            </p>
          </div>
        </div>
      )}

      {/* Trash items list */}
      {trashItems.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
          <Trash2 className="w-12 h-12 mx-auto mb-3 text-gray-400 opacity-50" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Trash is empty</p>
        </div>
      ) : (
        <div className="space-y-2">
          {trashItems.map((item) => {
            const Icon = getItemIcon(item.item_type)
            const isRestoring = restoringIds.has(item.id)
            const isDeleting = deletingIds.has(item.id)
            const daysLeft = getDaysUntilDeletion(item.permanent_delete_at)

            return (
              <div
                key={item.id}
                className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
              >
                <div className="p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {item.item_name}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <span>Deleted {formatDate(item.deleted_at)}</span>
                    <span>•</span>
                    <span className={daysLeft <= 3 ? 'text-red-600 dark:text-red-400 font-medium' : ''}>
                      <Clock className="w-3 h-3 inline mr-1" />
                      {daysLeft} day{daysLeft !== 1 ? 's' : ''} left
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Restore button */}
                  <button
                    onClick={() => handleRestore(item)}
                    disabled={isRestoring || isDeleting}
                    className="p-2 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors disabled:opacity-50"
                    title="Restore"
                  >
                    {isRestoring ? (
                      <Loader2 className="w-4 h-4 text-green-600 animate-spin" />
                    ) : (
                      <RotateCcw className="w-4 h-4 text-green-600 dark:text-green-400" />
                    )}
                  </button>

                  {/* Permanent delete button */}
                  <button
                    onClick={() => handlePermanentDelete(item)}
                    disabled={isRestoring || isDeleting}
                    className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                    title="Permanently delete"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 text-red-600 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
