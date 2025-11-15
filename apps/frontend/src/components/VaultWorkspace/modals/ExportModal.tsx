import { useEffect } from 'react'
import { Archive, X, Download } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface ExportModalProps {
  isOpen: boolean
  vaultMode: string
  onClose: () => void
}

export function ExportModal({ isOpen, vaultMode, onClose }: ExportModalProps) {
  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const handleExportVault = async () => {
    try {
      const response = await axios.get('/api/v1/vault/export', {
        params: { vault_type: vaultMode }
      })

      const dataStr = JSON.stringify(response.data, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `vault_export_${new Date().toISOString()}.json`
      link.click()
      URL.revokeObjectURL(url)

      toast.success('Vault data exported successfully')
      onClose()
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('Failed to export vault data')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[500px] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <Archive className="w-5 h-5" />
            Export Vault Data
          </h3>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-gray-700 dark:text-gray-300 mb-6">
            Export your vault metadata including file information, folders, tags, and more.
            Note: Actual file contents are not included in the export.
          </p>

          <div className="flex gap-3">
            <button
              onClick={handleExportVault}
              className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center justify-center gap-2 font-medium"
            >
              <Download className="w-5 h-5" />
              Export as JSON
            </button>
            <button
              onClick={onClose}
              className="px-4 py-3 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 text-gray-900 dark:text-gray-100 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
