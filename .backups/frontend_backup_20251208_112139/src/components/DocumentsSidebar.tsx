/**
 * Documents Sidebar
 *
 * Shows list of all documents grouped by type
 */

import { useDocsStore } from '@/stores/docsStore'
import { FileText, Table2, Lightbulb, Lock, Trash2 } from 'lucide-react'
import type { DocumentType } from '@/stores/docsStore'

export function DocumentsSidebar() {
  const {
    documents,
    activeDocumentId,
    setActiveDocument,
    deleteDocument,
    lockedDocuments,
  } = useDocsStore()

  const getIcon = (type: DocumentType) => {
    switch (type) {
      case 'doc':
        return FileText
      case 'sheet':
        return Table2
      case 'insight':
        return Lightbulb
    }
  }

  const getIconColor = (type: DocumentType) => {
    switch (type) {
      case 'doc':
        return 'text-blue-600 dark:text-blue-400'
      case 'sheet':
        return 'text-green-600 dark:text-green-400'
      case 'insight':
        return 'text-amber-600 dark:text-amber-400'
    }
  }

  // Group documents by type
  const groupedDocs = {
    doc: documents.filter((d) => d.type === 'doc'),
    sheet: documents.filter((d) => d.type === 'sheet'),
    insight: documents.filter((d) => d.type === 'insight'),
  }

  const handleDelete = (e: React.MouseEvent, docId: string) => {
    e.stopPropagation()
    if (window.confirm('Delete this document? This cannot be undone.')) {
      deleteDocument(docId)
    }
  }

  const renderDocumentList = (docs: typeof documents, label: string) => {
    if (docs.length === 0) return null

    return (
      <div className="mb-4">
        <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {label}
        </div>
        <div className="space-y-1">
          {docs.map((doc) => {
            const Icon = getIcon(doc.type)
            const isLocked = lockedDocuments.has(doc.id)
            const isActive = doc.id === activeDocumentId

            return (
              <div
                key={doc.id}
                onClick={() => setActiveDocument(doc.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-all group cursor-pointer ${
                  isActive
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? '' : getIconColor(doc.type)}`} />
                <span className="flex-1 text-left text-sm truncate">{doc.title}</span>

                {isLocked && <Lock className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />}

                {!isLocked && (
                  <button
                    onClick={(e) => handleDelete(e, doc.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-2">
      {documents.length === 0 ? (
        <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
          No documents yet
        </div>
      ) : (
        <>
          {renderDocumentList(groupedDocs.doc, 'Documents')}
          {renderDocumentList(groupedDocs.sheet, 'Spreadsheets')}
          {renderDocumentList(groupedDocs.insight, 'Insights')}
        </>
      )}
    </div>
  )
}
