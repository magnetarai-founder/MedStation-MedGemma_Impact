/**
 * ShareDialogModal - Share files with external users
 * Create share links with optional password, expiry, and download limits
 */

import { X, Share2, Link2, Copy } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface ShareLink {
  id: string
  share_token: string
  download_count: number
  max_downloads: number | null
  expires_at: string | null
}

interface ShareDialogModalProps {
  isOpen: boolean
  onClose: () => void
  fileId?: string
  filename?: string
}

export function ShareDialogModal({ isOpen, onClose, fileId, filename }: ShareDialogModalProps) {
  const [shareLinks, setShareLinks] = useState<ShareLink[]>([])
  const [sharePassword, setSharePassword] = useState('')
  const [shareExpiry, setShareExpiry] = useState('')
  const [shareMaxDownloads, setShareMaxDownloads] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  async function handleCreateShareLink() {
    if (!fileId) return

    setIsCreating(true)
    try {
      const response = await fetch('/api/v1/vault/share/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          file_id: fileId,
          password: sharePassword || undefined,
          expires_at: shareExpiry || undefined,
          max_downloads: shareMaxDownloads ? parseInt(shareMaxDownloads) : undefined
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create share link')
      }

      const data = await response.json()
      const shareUrl = `${window.location.origin}/vault/share/${data.share_token}`

      await navigator.clipboard.writeText(shareUrl)
      toast.success('Share link created and copied to clipboard!')

      // Reset form
      setSharePassword('')
      setShareExpiry('')
      setShareMaxDownloads('')

      // Refresh share links
      fetchShareLinks()
    } catch (error) {
      console.error('Failed to create share link:', error)
      toast.error('Failed to create share link')
    } finally {
      setIsCreating(false)
    }
  }

  async function fetchShareLinks() {
    if (!fileId) return

    try {
      const response = await fetch(`/api/v1/vault/share/list/${fileId}`, {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch share links')
      }

      const data = await response.json()
      setShareLinks(data.shares || [])
    } catch (error) {
      console.error('Failed to fetch share links:', error)
    }
  }

  async function handleRevokeShare(shareId: string) {
    try {
      const response = await fetch(`/api/v1/vault/share/revoke/${shareId}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to revoke share')
      }

      toast.success('Share link revoked')
      fetchShareLinks()
    } catch (error) {
      console.error('Failed to revoke share:', error)
      toast.error('Failed to revoke share link')
    }
  }

  if (!isOpen || !fileId) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[600px] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <Share2 className="w-5 h-5" />
            Share "{filename}"
          </h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Create New Share */}
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900 dark:text-gray-100">Create Share Link</h4>

            <div>
              <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Password (optional)</label>
              <input
                type="password"
                value={sharePassword}
                onChange={(e) => setSharePassword(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Leave empty for no password"
              />
            </div>

            <div>
              <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Expires At (optional)</label>
              <input
                type="datetime-local"
                value={shareExpiry}
                onChange={(e) => setShareExpiry(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Max Downloads (optional)</label>
              <input
                type="number"
                value={shareMaxDownloads}
                onChange={(e) => setShareMaxDownloads(e.target.value)}
                className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Unlimited"
                min="1"
              />
            </div>

            <button
              onClick={handleCreateShareLink}
              disabled={isCreating}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Link2 className="w-4 h-4" />
              {isCreating ? 'Creating...' : 'Create & Copy Link'}
            </button>
          </div>

          {/* Existing Shares */}
          {shareLinks.length > 0 && (
            <div className="pt-4 border-t border-gray-300 dark:border-zinc-700">
              <h4 className="font-medium mb-2 text-gray-900 dark:text-gray-100">Active Share Links</h4>
              <div className="space-y-2">
                {shareLinks.map((share) => (
                  <div
                    key={share.id}
                    className="flex items-center gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded"
                  >
                    <div className="flex-1 text-sm min-w-0">
                      <div className="flex items-center gap-2">
                        <code className="text-xs text-gray-600 dark:text-zinc-400 truncate">
                          {share.share_token.substring(0, 20)}...
                        </code>
                        <button
                          onClick={() => {
                            const url = `${window.location.origin}/vault/share/${share.share_token}`
                            navigator.clipboard.writeText(url)
                            toast.success('Copied!')
                          }}
                          className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded flex-shrink-0"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                      <div className="text-gray-600 dark:text-zinc-500 mt-1">
                        Downloads: {share.download_count}/{share.max_downloads || '∞'}
                        {share.expires_at && ` • Expires: ${new Date(share.expires_at).toLocaleDateString()}`}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRevokeShare(share.id)}
                      className="p-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors flex-shrink-0"
                      title="Revoke share"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
