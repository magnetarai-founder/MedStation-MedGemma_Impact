/**
 * Empty State Component
 * Shows when no files are present in the vault
 */

import { Upload, Folder } from 'lucide-react'

interface EmptyStateProps {
  onUploadClick: () => void
  onCreateFolderClick: () => void
}

export function EmptyState({ onUploadClick, onCreateFolderClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-24 h-24 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-6">
        <Folder className="w-12 h-12 text-gray-400 dark:text-gray-500" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        No files or folders yet
      </h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md">
        Start by uploading files or creating folders to organize your secure vault
      </p>
      <div className="flex items-center gap-3">
        <button
          onClick={onUploadClick}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          <Upload className="w-5 h-5" />
          Upload Files
        </button>
        <button
          onClick={onCreateFolderClick}
          className="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          <Folder className="w-5 h-5" />
          Create Folder
        </button>
      </div>
    </div>
  )
}
