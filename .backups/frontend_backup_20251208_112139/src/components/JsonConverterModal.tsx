import { useState, useCallback, useEffect } from 'react'
import { X, FileJson, Loader2, Download, Trash2 } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import Editor from '@monaco-editor/react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'

interface JsonConverterModalProps {
  isOpen: boolean
  onClose: () => void
}

export function JsonConverterModal({ isOpen, onClose }: JsonConverterModalProps) {
  const { sessionId } = useSessionStore()
  const [jsonFile, setJsonFile] = useState<File | null>(null)
  const [jsonContent, setJsonContent] = useState<string>('')
  const [isConverting, setIsConverting] = useState(false)
  const [exportFormat, setExportFormat] = useState<'excel' | 'csv' | 'tsv' | 'parquet'>('excel')
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [objectCount, setObjectCount] = useState<number>(0)
  const [columnCount, setColumnCount] = useState<number>(0)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setJsonFile(file)
    const content = await file.text()
    setJsonContent(content)

    // Parse JSON to get stats
    try {
      const parsed = JSON.parse(content)
      if (Array.isArray(parsed)) {
        setObjectCount(parsed.length)
        // Get column count from first object
        if (parsed.length > 0 && typeof parsed[0] === 'object') {
          setColumnCount(Object.keys(parsed[0]).length)
        }
      } else if (typeof parsed === 'object') {
        setObjectCount(1)
        setColumnCount(Object.keys(parsed).length)
      }
      setStatusMessage(`📊 ${parsed.length || 1} objects • ${Object.keys(parsed[0] || parsed).length || 0} columns`)
    } catch (e) {
      setStatusMessage('⚠️ Invalid JSON format')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
    },
    maxFiles: 1,
    disabled: isConverting,
  })

  const handleConvert = async () => {
    if (!jsonFile || !sessionId) return

    setIsConverting(true)
    setStatusMessage('⚙️ Parsing JSON...')

    try {
      // Convert using settings from Settings page (smart defaults)
      const result = await api.convertJson(sessionId, jsonContent, {
        expand_arrays: true,
        max_depth: 5,
        auto_safe: true,
        include_summary: false,
      })

      setStatusMessage(`⚙️ Converting to ${exportFormat.toUpperCase()}...`)

      // Download the converted file
      const blob = await api.downloadJsonResult(sessionId, exportFormat)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url

      // Set appropriate file extension based on format
      const extensions = {
        excel: 'xlsx',
        csv: 'csv',
        tsv: 'tsv',
        parquet: 'parquet'
      }
      const ext = extensions[exportFormat]

      const filename = `${jsonFile.name.replace('.json', '')}_converted_${new Date().toISOString().slice(0, 10)}.${ext}`
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setStatusMessage(`✅ Processed and downloaded as "${filename}"`)

      // Clear success message after 3 seconds
      setTimeout(() => {
        setStatusMessage(`📊 ${objectCount} objects • ${columnCount} columns`)
      }, 3000)

      // Don't close modal - let user continue with more conversions
    } catch (error: any) {
      setStatusMessage(`❌ Conversion failed: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsConverting(false)
    }
  }

  const handleClear = () => {
    setJsonFile(null)
    setJsonContent('')
    setIsConverting(false)
    setStatusMessage('')
    setObjectCount(0)
    setColumnCount(0)
  }

  const handleClose = () => {
    setJsonFile(null)
    setJsonContent('')
    setIsConverting(false)
    setStatusMessage('')
    setObjectCount(0)
    setColumnCount(0)
    onClose()
  }

  // Handle ESC key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl h-[80vh] bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-800 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center space-x-2">
            <FileJson className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              JSON Converter
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            disabled={isConverting}
            title="Press ESC to close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content - 65/35 split */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {!jsonFile ? (
            // Upload zone (full height when no file)
            <div className="flex-1 p-4">
              <div
                {...getRootProps()}
                className={`
                  h-full border-2 border-dashed rounded-lg cursor-pointer
                  transition-colors duration-200 flex items-center justify-center
                  ${isDragActive
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
                    : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
                  }
                `}
              >
                <input {...getInputProps()} />
                <div className="text-center">
                  <FileJson className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {isDragActive ? 'Drop your JSON file here' : 'Upload JSON File'}
                  </p>
                  <p className="text-sm text-gray-500">
                    Drop a file or click to browse
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Preview - 65% height */}
              <div className="h-[65%] p-4 pb-2">
                <div className="mb-2">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Preview: <span className="font-medium text-gray-900 dark:text-gray-100">{jsonFile.name}</span>
                  </p>
                </div>
                <div className="h-full border border-gray-200 dark:border-gray-800 rounded overflow-hidden">
                  <Editor
                    height="100%"
                    language="json"
                    value={jsonContent}
                    theme="vs-dark"
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                      wordWrap: 'on',
                      unusualLineTerminators: 'auto',
                      unicodeHighlight: {
                        ambiguousCharacters: false,
                        invisibleCharacters: false,
                      },
                    }}
                  />
                </div>
              </div>

              {/* Status/Logs - 35% height */}
              <div className="h-[35%] px-4 pb-2 flex flex-col">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Status:
                </h3>
                <div className="flex-1 overflow-auto p-3 bg-gray-50 dark:bg-gray-800/50 rounded border border-gray-200 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 space-y-1">
                  {statusMessage || 'Ready to convert'}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer - Right-aligned controls */}
        <div className="flex items-center justify-end p-4 border-t border-gray-200 dark:border-gray-800">
          {jsonFile && (
            <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50 gap-1">
              {/* Export format dropdown */}
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as 'excel' | 'csv' | 'tsv' | 'parquet')}
                disabled={isConverting}
                className="px-2 py-1 text-sm rounded border-0 bg-transparent hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300"
              >
                <option value="excel">Excel</option>
                <option value="csv">CSV</option>
                <option value="tsv">TSV</option>
                <option value="parquet">Parquet</option>
              </select>

              {/* Download button */}
              <button
                onClick={handleConvert}
                disabled={isConverting}
                className={`p-1.5 rounded ${
                  isConverting
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                title="Download converted file"
              >
                {isConverting ? (
                  <Loader2 className="w-4 h-4 animate-spin text-gray-700 dark:text-gray-300" />
                ) : (
                  <Download className="w-4 h-4 text-gray-700 dark:text-gray-300" />
                )}
              </button>

              {/* Clear/Trash button */}
              <button
                onClick={handleClear}
                disabled={isConverting}
                className={`p-1.5 rounded ${
                  isConverting
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                title="Clear and upload new file"
              >
                <Trash2 className="w-4 h-4 text-gray-700 dark:text-gray-300" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
