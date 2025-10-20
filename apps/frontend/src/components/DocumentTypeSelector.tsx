/**
 * Document Type Selector
 *
 * Allows users to choose between:
 * - Doc (Quip-like word processor)
 * - Sheet (lightweight spreadsheet)
 * - Insight (voice transcription + AI analysis)
 */

import { FileText, Table2, Lightbulb } from 'lucide-react'
import type { DocumentType } from '@/stores/docsStore'

interface DocumentTypeSelectorProps {
  onSelect: (type: DocumentType) => void
  onClose: () => void
}

export function DocumentTypeSelector({ onSelect, onClose }: DocumentTypeSelectorProps) {
  const documentTypes = [
    {
      type: 'doc' as DocumentType,
      icon: FileText,
      label: 'Document',
      description: 'Rich text collaborative document',
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      type: 'sheet' as DocumentType,
      icon: Table2,
      label: 'Spreadsheet',
      description: 'Lightweight collaborative spreadsheet',
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
    },
    {
      type: 'insight' as DocumentType,
      icon: Lightbulb,
      label: 'Insight',
      description: 'Voice transcription + AI analysis',
      color: 'text-amber-600 dark:text-amber-400',
      bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    },
  ]

  return (
    <div className="absolute top-16 left-3 right-3 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Options */}
        <div className="p-2">
          {documentTypes.map((docType) => {
            const Icon = docType.icon
            return (
              <button
                key={docType.type}
                onClick={() => onSelect(docType.type)}
                className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-all group"
              >
                <div className={`p-2 rounded-lg ${docType.bgColor}`}>
                  <Icon className={`w-5 h-5 ${docType.color}`} />
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                    {docType.label}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {docType.description}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            onClick={onClose}
            className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
