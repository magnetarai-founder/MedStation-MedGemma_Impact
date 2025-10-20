/**
 * Docs & Sheets Workspace
 *
 * Main workspace for collaborative documents:
 * - Documents (Quip-like word processor)
 * - Spreadsheets (lightweight collaborative sheets)
 * - Insights Lab (voice transcription + AI analysis)
 */

import { useDocsStore } from '@/stores/docsStore'
import { DocumentTypeSelector } from './DocumentTypeSelector'
import { DocumentEditor } from './DocumentEditor'
import { DocumentsSidebar } from './DocumentsSidebar'
import { Plus, Lock } from 'lucide-react'
import { useState } from 'react'

export function DocsWorkspace() {
  const {
    documents,
    activeDocumentId,
    setActiveDocument,
    createDocument,
  } = useDocsStore()

  const [showTypeSelector, setShowTypeSelector] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  const activeDocument = documents.find((doc) => doc.id === activeDocumentId)

  const handleCreateDocument = (type: 'doc' | 'sheet' | 'insight') => {
    createDocument(type)
    setShowTypeSelector(false)
  }

  return (
    <div className="h-full w-full flex">
      {/* Sidebar - Document list */}
      {!isSidebarCollapsed && (
        <div className="w-64 flex-shrink-0 bg-gray-50/80 dark:bg-gray-800/50 backdrop-blur-xl border-r border-white/10 dark:border-gray-700/30 flex flex-col">
        {/* Header with create button */}
        <div className="p-3 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setShowTypeSelector(!showTypeSelector)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-all font-medium text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>New Document</span>
          </button>
        </div>

        {/* Type selector dropdown */}
        {showTypeSelector && (
          <DocumentTypeSelector
            onSelect={handleCreateDocument}
            onClose={() => setShowTypeSelector(false)}
          />
        )}

        {/* Documents list */}
        <DocumentsSidebar />
      </div>
      )}

      {/* Main editor area */}
      <div className="flex-1 flex flex-col min-h-0">
        {activeDocument ? (
          <DocumentEditor document={activeDocument} onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)} isSidebarCollapsed={isSidebarCollapsed} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <Plus className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No document selected</p>
              <p className="text-sm mt-2">Create a new document to get started</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
