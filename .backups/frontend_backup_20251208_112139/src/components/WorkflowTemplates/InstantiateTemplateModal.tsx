/**
 * Instantiate Template Modal (Phase D)
 * Create a new workflow from a template
 */

import { useState } from 'react'
import { X, Copy, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { useInstantiateTemplate } from '@/hooks/useWorkflowQueue'
import type { Workflow } from '@/types/workflow'

interface InstantiateTemplateModalProps {
  template: Workflow
  isOpen: boolean
  onClose: () => void
  onSuccess: (workflow: Workflow) => void
}

export function InstantiateTemplateModal({
  template,
  isOpen,
  onClose,
  onSuccess,
}: InstantiateTemplateModalProps) {
  const [name, setName] = useState(`${template.name} (Copy)`)
  const [description, setDescription] = useState(template.description || '')
  const [error, setError] = useState<string | null>(null)

  const instantiateMutation = useInstantiateTemplate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Workflow name is required')
      return
    }

    try {
      const newWorkflow = await instantiateMutation.mutateAsync({
        templateId: template.id,
        name: name.trim(),
        description: description.trim() || undefined,
      })

      onSuccess(newWorkflow)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to instantiate template')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
              <Copy className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Instantiate Template
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Create a new workflow from: {template.name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Template Summary */}
          <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Template Summary
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Stages:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {template.stages?.length || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">Triggers:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {template.triggers?.length || 0}
                </span>
              </div>
              {template.stages?.some(s => s.stage_type === 'agent_assist') && (
                <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 text-xs mt-2">
                  <CheckCircle className="w-3 h-3" />
                  <span>Includes AI Agent Assist stages</span>
                </div>
              )}
            </div>
          </div>

          {/* Name Input */}
          <div>
            <label
              htmlFor="workflow-name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Workflow Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="workflow-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter workflow name"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={instantiateMutation.isPending}
              required
            />
          </div>

          {/* Description Input */}
          <div>
            <label
              htmlFor="workflow-description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Description (Optional)
            </label>
            <textarea
              id="workflow-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter workflow description"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              disabled={instantiateMutation.isPending}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-red-900 dark:text-red-100">
                    Failed to instantiate template
                  </h4>
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    {error}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              disabled={instantiateMutation.isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              disabled={instantiateMutation.isPending}
            >
              {instantiateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Create Workflow
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
