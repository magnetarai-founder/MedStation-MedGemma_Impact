import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, Loader2, FileSpreadsheet, FileJson, Trash2, X } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useEditorStore } from '@/stores/editorStore'

export function FileUpload() {
  const { sessionId, currentFile, setCurrentFile, setCurrentQuery, setIsExecuting, isUploading, setIsUploading, setSessionId } = useSessionStore()
  const { setContentType, setHasExecuted, setCode } = useEditorStore()

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      console.log('🔵 FileUpload mutation started:', file.name, 'SessionID:', sessionId)
      if (!sessionId) {
        console.error('❌ No session ID!')
        throw new Error('No session')
      }
      setIsUploading(true)

      // Route to appropriate upload endpoint based on file type
      if (file.name.endsWith('.json')) {
        console.log('📤 Uploading as JSON to:', `/sessions/${sessionId}/json/upload`)
        return api.uploadJson(sessionId, file)
      } else {
        console.log('📤 Uploading as Excel/CSV to:', `/sessions/${sessionId}/upload`)
        return api.uploadFile(sessionId, file)
      }
    },
    onSuccess: async (data, file) => {
      console.log('✅ Upload successful!', data)
      // Transform JSON upload response to match FileUploadResponse format
      if (file.name.endsWith('.json')) {
        const jsonData = data as any
        const transformedData = {
          filename: jsonData.filename,
          size_mb: jsonData.size_mb,
          row_count: jsonData.object_count || 0,
          column_count: jsonData.columns?.length || 0,
          columns: jsonData.columns?.map((col: string) => ({
            original_name: col,
            clean_name: col,
            dtype: 'string',
            non_null_count: 0,
            null_count: 0
          })) || []
        }
        setCurrentFile(transformedData)

        // Load content into editor
        const reader = new FileReader()
        reader.onload = (e) => {
          const content = e.target?.result as string
          setContentType('json')
          setHasExecuted(false)
          window.dispatchEvent(new CustomEvent('code-file-loaded', { detail: { content, type: 'json' } }))
        }
        reader.readAsText(file)
      } else {
        // For Excel/CSV
        setCurrentFile(data)
        setContentType('sql')

        // Auto-run SQL preview
        try {
          if (sessionId) {
            setIsExecuting(true)
            const preview = await api.executeQuery(sessionId, 'SELECT * FROM excel_file', { limit: 10 })
            setCurrentQuery(preview)
          }
        } catch (e) {
          console.warn('Auto-preview failed:', e)
        } finally {
          setIsExecuting(false)
        }
      }
      setIsUploading(false)
    },
    onError: (error: any) => {
      setIsUploading(false)
      const errorMsg = error.response?.data?.detail || error.message || 'Upload failed'
      console.error('❌ Upload error:', errorMsg, error)
      alert(`Upload failed: ${errorMsg}`)
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    console.log('📥 File dropped:', acceptedFiles.length, 'files')
    const file = acceptedFiles[0]
    if (!file) {
      console.warn('⚠️ No file in acceptedFiles')
      return
    }

    console.log('📁 File details:', {
      name: file.name,
      size: `${(file.size / 1024).toFixed(2)} KB`,
      type: file.type
    })
    console.log('🚀 Starting upload mutation...')
    // Upload all file types through mutation (handles both JSON and Excel/CSV)
    uploadMutation.mutate(file)
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
    disabled: isUploading,
  })

  if (currentFile) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            <File className="w-4 h-4 text-primary-600 flex-shrink-0" />
            <span className="text-sm font-medium truncate">{currentFile.filename}</span>
          </div>
          <button
            onClick={async () => {
              // Direct clear without dialog - fast workflow
              if (isUploading) return

              setIsUploading(true)
              try {
                // Delete session on backend
                if (sessionId) {
                  await api.deleteSession(sessionId)
                }

                // Clear everything except logs
                setCurrentFile(null)
                setCurrentQuery(null)
                setCode('')
                setHasExecuted(false)

                // Clear the code editor
                window.dispatchEvent(new CustomEvent('clear-code-editor'))

                // Create fresh session
                const s = await api.createSession()
                setSessionId(s.session_id)
              } catch (e) {
                console.error('Clear failed', e)
              } finally {
                setIsUploading(false)
              }
            }}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex-shrink-0"
            title="Clear file and reset workspace"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
        <div className="text-xs text-gray-500 space-y-0.5">
          <p>{currentFile.row_count.toLocaleString()} rows × {currentFile.column_count} columns</p>
          <p>{currentFile.size_mb.toFixed(2)} MB</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg cursor-pointer
          transition-colors duration-200 p-6
          ${isDragActive
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
            : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="flex flex-col items-center space-y-2">
            <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
            <p className="text-sm text-gray-600 dark:text-gray-400">Loading file...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-3">
            <Upload className="w-8 h-8 text-gray-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {isDragActive ? 'Drop your file here' : 'Drop file or click to upload'}
              </p>
              <div className="flex items-center justify-center space-x-2 mt-2">
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  <FileSpreadsheet className="w-3 h-3" />
                  <span>Excel</span>
                </span>
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  <FileSpreadsheet className="w-3 h-3" />
                  <span>CSV</span>
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
