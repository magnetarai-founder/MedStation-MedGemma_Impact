import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, Loader2, FileSpreadsheet, FileText, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'

export function FileUpload() {
  const { sessionId, currentFile, setCurrentFile, setCurrentQuery, setIsExecuting } = useSessionStore()
  const [sqlContent, setSqlContent] = useState<string>('')

  const handleSqlFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const content = ev.target?.result as string
      setSqlContent(content)
      window.dispatchEvent(new CustomEvent('sql-file-loaded', { detail: content }))
      // SQL file loaded into editor successfully
    }
    reader.onerror = () => console.error('Failed to read SQL file')
    reader.readAsText(file)
    // reset input so selecting the same file again works
    e.currentTarget.value = ''
  }, [])

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      if (!sessionId) throw new Error('No session')
      return api.uploadFile(sessionId, file)
    },
    onSuccess: async (data) => {
      setCurrentFile(data)
      // Successfully loaded file
      // Auto-run a quick preview so Results are immediately populated
      try {
        if (sessionId) {
          setIsExecuting(true)
          const preview = await api.executeQuery(sessionId, 'SELECT * FROM excel_file', { limit: 100 })
          setCurrentQuery(preview)
        }
      } catch (e) {
        console.warn('Auto-preview failed:', e)
      } finally {
        setIsExecuting(false)
      }
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Upload failed'
      console.error('Upload error:', errorMsg, error)
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // Check if it's a SQL file
    if (file.name.endsWith('.sql')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        setSqlContent(content)
        // Emit event to update SQL editor
        window.dispatchEvent(new CustomEvent('sql-file-loaded', { detail: content }))
        // SQL file loaded into editor successfully
      }
      reader.onerror = () => {
        console.error('Failed to read SQL file')
      }
      reader.readAsText(file)
    } else {
      // Handle Excel/CSV files
      uploadMutation.mutate(file)
    }
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
      'text/csv': ['.csv'],
      'text/plain': ['.sql'],
    },
    maxFiles: 1,
    disabled: uploadMutation.isPending,
  })

  if (currentFile) {
    return (
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <File className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium truncate">{currentFile.filename}</span>
        </div>
        <div className="text-xs text-gray-500 space-y-1">
          <p>{currentFile.row_count.toLocaleString()} rows × {currentFile.column_count} columns</p>
          <p>{currentFile.size_mb.toFixed(2)} MB</p>
        </div>
        <div className="flex items-center space-x-3">
          {/* Load a .sql file into the editor without clearing the data file */}
          <label className="flex items-center space-x-1 text-xs text-primary-600 hover:text-primary-700 cursor-pointer">
            <Upload className="w-3 h-3" />
            <span>Load .sql into editor</span>
            <input
              type="file"
              accept=".sql,text/plain"
              className="hidden"
              onChange={handleSqlFileInput}
            />
          </label>
          <button
            onClick={() => { if (window.confirm('Clear the loaded file and results?')) { setCurrentFile(null); setCurrentQuery(null) } }}
            className="flex items-center space-x-1 text-xs text-primary-600 hover:text-primary-700"
            title="Clear loaded file"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear file</span>
          </button>
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
          transition-colors duration-200 overflow-hidden
          ${isDragActive 
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-950' 
            : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
          }
          ${uploadMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        {uploadMutation.isPending ? (
          <div className="p-6 space-y-2">
            <Loader2 className="w-8 h-8 mx-auto text-primary-600 animate-spin" />
            <p className="text-sm text-gray-600 dark:text-gray-400">Loading file...</p>
          </div>
        ) : (
          <div className="flex h-32">
            {/* Data Files Section */}
            <div className="flex-1 flex flex-col items-center justify-center p-4 border-r border-gray-200 dark:border-gray-700">
              <FileSpreadsheet className="w-6 h-6 text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Data Files</p>
              <p className="text-xs text-gray-500 mt-1">Excel • CSV</p>
            </div>
            
            {/* SQL Files Section */}
            <div className="flex-1 flex flex-col items-center justify-center p-4">
              <FileText className="w-6 h-6 text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">SQL Queries</p>
              <p className="text-xs text-gray-500 mt-1">.sql files</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Overlay text when dragging */}
      {isDragActive && !uploadMutation.isPending && (
        <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-950 bg-opacity-90">
          <p className="text-sm font-medium text-primary-600">Drop your file here</p>
        </div>
      )}
    </div>
  )
}
