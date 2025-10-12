import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, Loader2, FileJson, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useJsonStore } from '@/stores/jsonStore'

interface JsonFileInfo {
  filename: string
  size_mb: number
  object_count: number
  depth: number
  columns: string[]
  preview: any[]
}

export function JsonFileUpload() {
  console.log('JsonFileUpload: Component mounted/rendered')
  const { sessionId } = useSessionStore()
  const { setJsonFileData, setJsonContent, setActualJsonContent } = useJsonStore()
  const [currentFile, setCurrentFile] = useState<JsonFileInfo | null>(null)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  console.log('JsonFileUpload: Current state', { sessionId, currentFile, uploadedFile })

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      console.log('JsonFileUpload: Starting upload', { file: file.name, sessionId })

      if (!sessionId) {
        console.error('JsonFileUpload: No session ID available')
        throw new Error('No session - please refresh the page')
      }

      // For large files, don't load entire content into editor
      const MAX_EDITOR_SIZE = 1 * 1024 * 1024 // 1MB
      let fileContent = ''

      if (file.size <= MAX_EDITOR_SIZE) {
        // Small file - load entire content
        fileContent = await file.text()
      } else {
        // Large file - load preview only
        const slice = file.slice(0, MAX_EDITOR_SIZE)
        const preview = await slice.text()

        // Try to find a good cut-off point
        const lastNewline = preview.lastIndexOf('\n')
        const truncated = lastNewline > 0 ? preview.substring(0, lastNewline) : preview

        fileContent = truncated + '\n\n// ... File truncated for preview (too large for editor) ...'
      }

      console.log('JsonFileUpload: Uploading to API', { sessionId, filename: file.name })

      // Upload to API
      const response = await api.uploadJson(sessionId, file)

      console.log('JsonFileUpload: Upload successful', response)

      return { response, fileContent }
    },
    onSuccess: async ({ response, fileContent }) => {
      setCurrentFile(response)
      
      // Update JSON store with file data and content
      setJsonFileData({
        filename: response.filename,
        columns: response.columns,
        preview: response.preview,
      })
      
      // Update the editor content with preview
      setJsonContent(fileContent)
      
      // Store the actual content for conversion (read the full file)
      if (uploadedFile) {
        const fullContent = await uploadedFile.text()
        setActualJsonContent(fullContent)
      }
    },
    onError: (error: any) => {
      const errorMsg = error.message || 'Upload failed'
      console.error('JsonFileUpload: Upload error:', errorMsg, error)
      alert(`Upload failed: ${errorMsg}`)
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    console.log('JsonFileUpload: onDrop called', { acceptedFiles })
    const file = acceptedFiles[0]
    if (!file) {
      console.warn('JsonFileUpload: No file in acceptedFiles')
      return
    }
    console.log('JsonFileUpload: File accepted, starting upload mutation', { filename: file.name, size: file.size })
    setUploadedFile(file)  // Store the file reference
    uploadMutation.mutate(file)
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
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
          <p>{currentFile.object_count.toLocaleString()} objects</p>
          <p>Max depth: {currentFile.depth}</p>
          <p>{currentFile.size_mb.toFixed(2)} MB</p>
        </div>
        <button
          onClick={() => { 
            if (window.confirm('Clear the loaded file?')) { 
              setCurrentFile(null)
              setJsonFileData(null)
              setUploadedFile(null)
              setActualJsonContent(`{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`)
            } 
          }}
          className="flex items-center space-x-1 text-xs text-primary-600 hover:text-primary-700"
          title="Clear loaded file"
        >
          <Trash2 className="w-3 h-3" />
          <span>Clear file</span>
        </button>
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
            <p className="text-sm text-gray-600 dark:text-gray-400">Loading JSON file...</p>
          </div>
        ) : (
          <div className="flex h-32">
            {/* JSON Files Section */}
            <div className="flex-1 flex flex-col items-center justify-center p-4">
              <FileJson className="w-6 h-6 text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">JSON Files</p>
              <p className="text-xs text-gray-500 mt-1">Drop or click to upload</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Overlay text when dragging */}
      {isDragActive && !uploadMutation.isPending && (
        <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-950 bg-opacity-90">
          <p className="text-sm font-medium text-primary-600">Drop your JSON file here</p>
        </div>
      )}
    </div>
  )
}