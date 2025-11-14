/**
 * FileGrid Component
 * Displays vault files with selection, favorites, tags
 */

import {
  MoreVertical, Clock, Shield, Star, Eye, Download, Tag, Check, Square
} from 'lucide-react'
import { formatDate, formatBytes, getFileIcon, getFileIconColor } from './helpers'
import type { VaultFile, FileTag } from './types'

interface FileGridProps {
  files: VaultFile[]
  isMultiSelectMode: boolean
  selectedFiles: Set<string>
  favoriteFiles: Set<string>
  fileTags: Map<string, FileTag[]>
  currentVaultMode: string
  vaultPassphrase: string | null
  onFileClick: (file: VaultFile) => void
  onFileContextMenu: (e: React.MouseEvent, file: VaultFile) => void
  onFileDragStart: (e: React.DragEvent, file: VaultFile) => void
  onFileDragEnd: () => void
  onToggleSelection: (fileId: string) => void
  onToggleFavorite: (fileId: string) => void
  onPreviewFile: (file: VaultFile) => void
  onDownloadFile: (file: VaultFile) => void
  onOpenTagModal: (file: VaultFile) => void
}

export function FileGrid({
  files,
  isMultiSelectMode,
  selectedFiles,
  favoriteFiles,
  fileTags,
  currentVaultMode,
  vaultPassphrase,
  onFileClick,
  onFileContextMenu,
  onFileDragStart,
  onFileDragEnd,
  onToggleSelection,
  onToggleFavorite,
  onPreviewFile,
  onDownloadFile,
  onOpenTagModal
}: FileGridProps) {
  if (files.length === 0) return null

  return (
    <>
      {files.map((file) => {
        const FileIcon = getFileIcon(file.mime_type)
        const iconColorClass = getFileIconColor(file.mime_type)
        const isSelected = selectedFiles.has(file.id)
        const isFavorite = favoriteFiles.has(file.id)
        const tags = fileTags.get(file.id) || []

        return (
          <div
            key={file.id}
            draggable={!isMultiSelectMode}
            onDragStart={(e) => onFileDragStart(e, file)}
            onDragEnd={onFileDragEnd}
            onClick={() => isMultiSelectMode ? onToggleSelection(file.id) : onFileClick(file)}
            onContextMenu={(e) => onFileContextMenu(e, file)}
            className={`group relative p-4 bg-white dark:bg-gray-800 border-2 rounded-lg transition-all ${
              isMultiSelectMode ? 'cursor-pointer' : 'cursor-move'
            } ${
              isSelected
                ? 'border-purple-500 dark:border-purple-400 shadow-lg'
                : 'border-gray-200 dark:border-gray-700 hover:border-purple-500 dark:hover:border-purple-400 hover:shadow-lg'
            }`}
          >
            {/* Multi-select Checkbox */}
            {isMultiSelectMode && (
              <div className="absolute top-2 left-2 z-10">
                <div className={`w-6 h-6 rounded flex items-center justify-center ${
                  isSelected ? 'bg-purple-600 text-white' : 'bg-gray-200 dark:bg-gray-700'
                }`}>
                  {isSelected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4 text-gray-500" />}
                </div>
              </div>
            )}

            <div className="flex items-start justify-between mb-3">
              {/* Thumbnail or Icon */}
              {file.mime_type?.startsWith('image/') ? (
                <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                  <img
                    src={`/api/v1/vault/files/${file.id}/thumbnail?vault_type=${currentVaultMode}&vault_passphrase=${encodeURIComponent(vaultPassphrase || '')}`}
                    alt={file.filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // Fallback to icon if thumbnail fails
                      (e.target as HTMLElement).style.display = 'none'
                      const parent = (e.target as HTMLElement).parentElement
                      if (parent) {
                        parent.innerHTML = `<div class="w-full h-full flex items-center justify-center ${iconColorClass}"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>`
                      }
                    }}
                  />
                </div>
              ) : (
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconColorClass}`}>
                  <FileIcon className="w-6 h-6" />
                </div>
              )}

              {/* Action Buttons */}
              <div className="opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                {/* Favorite Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggleFavorite(file.id)
                  }}
                  className={`p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded ${
                    isFavorite ? 'text-yellow-500' : 'text-gray-500'
                  }`}
                  title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                >
                  <Star className="w-4 h-4" fill={isFavorite ? 'currentColor' : 'none'} />
                </button>
                {/* Preview Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onPreviewFile(file)
                  }}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="Preview file"
                >
                  <Eye className="w-4 h-4 text-gray-500" />
                </button>
                {/* Download Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDownloadFile(file)
                  }}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="Download file"
                >
                  <Download className="w-4 h-4 text-gray-500" />
                </button>
                {/* Tag Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onOpenTagModal(file)
                  }}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="Manage tags"
                >
                  <Tag className="w-4 h-4 text-gray-500" />
                </button>
                {/* More Options */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onFileContextMenu(e as any, file)
                  }}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="More options"
                >
                  <MoreVertical className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Filename */}
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate" title={file.filename}>
              {file.filename}
              {isFavorite && <Star className="inline w-3 h-3 ml-1 text-yellow-500" fill="currentColor" />}
            </h3>

            {/* Metadata */}
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3 text-green-600 dark:text-green-400" />
                <span>Encrypted</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{formatDate(file.created_at)}</span>
              </div>
            </div>

            {/* File Size */}
            <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
              {formatBytes(file.file_size)}
            </div>

            {/* Tags Display */}
            {tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {tags.map((tag) => (
                  <span
                    key={tag.tag_name}
                    className="px-2 py-0.5 text-xs rounded-full text-white"
                    style={{ backgroundColor: tag.tag_color }}
                  >
                    {tag.tag_name}
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </>
  )
}
