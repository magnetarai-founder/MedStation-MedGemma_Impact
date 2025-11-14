/**
 * File Context Menu
 */

import { Download, Edit2, FolderInput, Share2, History, MessageSquare, Trash2 } from 'lucide-react'

interface FileContextMenuProps {
  onDownload: () => void
  onRename: () => void
  onMove: () => void
  onShare: () => void
  onVersionHistory: () => void
  onComments: () => void
  onDelete: () => void
}

export function FileContextMenu({
  onDownload,
  onRename,
  onMove,
  onShare,
  onVersionHistory,
  onComments,
  onDelete
}: FileContextMenuProps) {
  return (
    <>
      <button
        onClick={onDownload}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <Download className="w-4 h-4" />
        Download
      </button>
      <button
        onClick={onRename}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <Edit2 className="w-4 h-4" />
        Rename
      </button>
      <button
        onClick={onMove}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <FolderInput className="w-4 h-4" />
        Move to...
      </button>
      <button
        onClick={onShare}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <Share2 className="w-4 h-4" />
        Share
      </button>
      <button
        onClick={onVersionHistory}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <History className="w-4 h-4" />
        Version History
      </button>
      <button
        onClick={onComments}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <MessageSquare className="w-4 h-4" />
        Comments
      </button>
      <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
      <button
        onClick={onDelete}
        className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3"
      >
        <Trash2 className="w-4 h-4" />
        Delete
      </button>
    </>
  )
}
