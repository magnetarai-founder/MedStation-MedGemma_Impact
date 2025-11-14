import { useState, useEffect } from 'react'
import { Pin, PinOff, X, File } from 'lucide-react'
import axios from 'axios'
import { toast } from 'sonner'

interface PinnedFilesModalProps {
  isOpen: boolean
  vaultMode: string
  onClose: () => void
}

export function PinnedFilesModal({ isOpen, vaultMode, onClose }: PinnedFilesModalProps) {
  const [pinnedFiles, setPinnedFiles] = useState<Array<any>>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadPinnedFiles()
    }
  }, [isOpen])

  const loadPinnedFiles = async () => {
    setIsLoading(true)
    try {
      const response = await axios.get('/api/v1/vault/pinned-files', {
        params: { vault_type: vaultMode }
      })
      setPinnedFiles(response.data.pinned_files)
    } catch (error) {
      console.error('Failed to load pinned files:', error)
      toast.error('Failed to load pinned files')
    } finally {
      setIsLoading(false)
    }
  }

  const handleTogglePin = async (fileId: string, isPinned: boolean) => {
    try {
      if (isPinned) {
        await axios.delete(`/api/v1/vault/files/${fileId}/pin`, {
          params: { vault_type: vaultMode }
        })
        toast.success('File unpinned')
      } else {
        const formData = new FormData()
        formData.append('vault_type', vaultMode)
        formData.append('pin_order', '0')
        await axios.post(`/api/v1/vault/files/${fileId}/pin`, formData)
        toast.success('File pinned')
      }
      loadPinnedFiles()
    } catch (error) {
      toast.error('Failed to toggle pin')
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[700px] max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <Pin className="w-5 h-5" />
            Pinned Files
          </h3>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Pinned Files List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <Pin className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse" />
              <p>Loading pinned files...</p>
            </div>
          ) : pinnedFiles.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <Pin className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>No pinned files</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pinnedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-4 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 hover:border-gray-400 dark:hover:border-zinc-600"
                >
                  <File className="w-5 h-5 text-gray-500 dark:text-zinc-400" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-gray-100">{file.filename}</div>
                    <div className="text-sm text-gray-600 dark:text-zinc-500">
                      {(file.file_size / 1024).toFixed(2)} KB
                    </div>
                  </div>
                  <button
                    onClick={() => handleTogglePin(file.id, true)}
                    className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded text-gray-700 dark:text-gray-300"
                    title="Unpin"
                  >
                    <PinOff className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
