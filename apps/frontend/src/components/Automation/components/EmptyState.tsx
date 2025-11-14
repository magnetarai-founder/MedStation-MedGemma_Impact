import { Workflow as WorkflowIcon } from 'lucide-react'

interface EmptyStateProps {
  onCreateCustom?: () => void
}

export function EmptyState({ onCreateCustom }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
        <WorkflowIcon className="w-8 h-8 text-gray-400 dark:text-gray-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        No workflows found
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 text-center max-w-sm">
        Try adjusting your filters or search query to find what you're looking for
      </p>
      {onCreateCustom && (
        <button
          onClick={onCreateCustom}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
        >
          <WorkflowIcon className="w-4 h-4" />
          Create Custom Workflow
        </button>
      )}
    </div>
  )
}
