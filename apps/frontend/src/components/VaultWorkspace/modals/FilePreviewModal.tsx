import { useState, useEffect } from 'react'
import { Eye, X, Download, ZoomIn, ZoomOut } from 'lucide-react'
import axios from 'axios'
import { toast } from 'sonner'

interface FilePreviewModalProps {
  isOpen: boolean
  file: any
  vaultMode: string
  vaultPassphrase: string
  onClose: () => void
  onDownload: (file: any) => void
}

export function FilePreviewModal({ isOpen, file, vaultMode, vaultPassphrase, onClose, onDownload }: FilePreviewModalProps) {
  const [previewContent, setPreviewContent] = useState<string | null>(null)
  const [previewZoom, setPreviewZoom] = useState(1)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen && file) {
      loadPreview()
    }

    // Cleanup URL objects on unmount
    return () => {
      if (previewContent && (file?.mime_type?.startsWith('image/') || file?.mime_type === 'application/pdf' || file?.mime_type?.startsWith('audio/') || file?.mime_type?.startsWith('video/'))) {
        URL.revokeObjectURL(previewContent)
      }
    }
  }, [isOpen, file])

  const loadPreview = async () => {
    if (!file) return

    setIsLoading(true)
    setPreviewZoom(1)

    try {
      const response = await axios.get(`/api/v1/vault/files/${file.id}/download`, {
        params: {
          vault_type: vaultMode,
          vault_passphrase: vaultPassphrase
        },
        responseType: 'blob'
      })

      const mimeType = file.mime_type
      if (mimeType.startsWith('image/')) {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else if (mimeType.startsWith('text/') || mimeType === 'application/json') {
        const text = await response.data.text()
        setPreviewContent(text)
      } else if (mimeType === 'application/pdf') {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else if (mimeType.startsWith('audio/') || mimeType.startsWith('video/')) {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else {
        toast.error('Preview not available for this file type')
        setPreviewContent(null)
      }
    } catch (error: any) {
      console.error('Preview error:', error)
      toast.error('Failed to load file preview')
      setPreviewContent(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    if (previewContent && (file?.mime_type?.startsWith('image/') || file?.mime_type === 'application/pdf' || file?.mime_type?.startsWith('audio/') || file?.mime_type?.startsWith('video/'))) {
      URL.revokeObjectURL(previewContent)
    }
    onClose()
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (!isOpen || !file) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={handleClose}
    >
      <div
        className="bg-white dark:bg-gray-900 rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Eye className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {file.filename}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {file.mime_type} • {formatBytes(file.file_size)}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Preview Content */}
        <div className="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-800">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Eye className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse text-gray-500" />
                <p className="text-gray-500 dark:text-gray-400">Loading preview...</p>
              </div>
            </div>
          ) : previewContent ? (
            <>
              {/* Image Preview */}
              {file.mime_type.startsWith('image/') && (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPreviewZoom(Math.max(0.25, previewZoom - 0.25))}
                      className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
                    >
                      <ZoomOut className="w-4 h-4" />
                      Zoom Out
                    </button>
                    <button
                      onClick={() => setPreviewZoom(1)}
                      className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                    >
                      Reset
                    </button>
                    <button
                      onClick={() => setPreviewZoom(previewZoom + 0.25)}
                      className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
                    >
                      <ZoomIn className="w-4 h-4" />
                      Zoom In
                    </button>
                  </div>
                  <img
                    src={previewContent}
                    alt={file.filename}
                    style={{ transform: `scale(${previewZoom})`, transition: 'transform 0.2s' }}
                    className="max-w-full"
                  />
                </div>
              )}

              {/* PDF Preview */}
              {file.mime_type === 'application/pdf' && (
                <iframe
                  src={previewContent}
                  className="w-full h-[600px] rounded-lg"
                  title={file.filename}
                />
              )}

              {/* Text/Code Preview */}
              {(file.mime_type.startsWith('text/') || file.mime_type === 'application/json') && (
                <pre className="bg-white dark:bg-gray-900 p-4 rounded-lg overflow-auto text-sm font-mono">
                  <code>{previewContent}</code>
                </pre>
              )}

              {/* Audio Preview */}
              {file.mime_type.startsWith('audio/') && (
                <div className="flex items-center justify-center h-full">
                  <audio controls className="w-full max-w-2xl">
                    <source src={previewContent} type={file.mime_type} />
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}

              {/* Video Preview */}
              {file.mime_type.startsWith('video/') && (
                <div className="flex items-center justify-center">
                  <video controls className="w-full max-w-4xl rounded-lg">
                    <source src={previewContent} type={file.mime_type} />
                    Your browser does not support the video element.
                  </video>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-64">
              <Eye className="w-16 h-16 mx-auto mb-4 opacity-20 text-gray-500" />
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Preview not available for this file type
              </p>
              <button
                onClick={() => onDownload(file)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download to View
              </button>
            </div>
          )}
        </div>

        {/* Footer with Actions */}
        <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => onDownload(file)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>
    </div>
  )
}
