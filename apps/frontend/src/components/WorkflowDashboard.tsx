/**
 * Workflow Dashboard - Initial view when opening Automation
 *
 * Layout:
 * - Starred workflows (up to 5, horizontal)
 * - Recent workflows (horizontal)
 * - Centered Create button
 */

import { Plus, Star, Clock, Zap, Users } from 'lucide-react'
import { useWorkflows } from '@/hooks/useWorkflowQueue'
import type { Workflow } from '@/types/workflow'
import type { AutomationType } from './AutomationWorkspace'

interface WorkflowDashboardProps {
  automationType: AutomationType
  onWorkflowSelect: (workflow: Workflow) => void
  onCreateWorkflow: () => void
}

export function WorkflowDashboard({
  automationType,
  onWorkflowSelect,
  onCreateWorkflow
}: WorkflowDashboardProps) {
  // Fetch workflows from backend filtered by type
  const { data: workflows = [], isLoading } = useWorkflows({ workflow_type: automationType })

  // TODO: Add starred filtering once starring functionality is implemented
  const starredWorkflows: Workflow[] = []
  const recentWorkflows: Workflow[] = workflows.slice(0, 10) // Show most recent 10

  const typeColor = automationType === 'local'
    ? 'blue'
    : 'purple'

  const typeIcon = automationType === 'local' ? Zap : Users

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-gray-50/30 dark:bg-gray-900/30">
        <div className="text-center">
          <div className="inline-flex p-4 bg-gray-100 dark:bg-gray-800 rounded-full mb-4">
            {automationType === 'local' ? (
              <Zap className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-pulse" />
            ) : (
              <Users className="w-8 h-8 text-purple-600 dark:text-purple-400 animate-pulse" />
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading workflows...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full flex flex-col items-center justify-center p-8 bg-gray-50/30 dark:bg-gray-900/30">
      <div className="w-full max-w-4xl space-y-8">
        {/* Starred Section */}
        {starredWorkflows.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Star className="w-5 h-5 text-yellow-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Starred</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {starredWorkflows.map(workflow => (
                <button
                  key={workflow.id}
                  onClick={() => onWorkflowSelect(workflow)}
                  className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all text-left"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className={`p-2 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded-lg`}>
                      {automationType === 'local' ? (
                        <Zap className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      ) : (
                        <Users className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      )}
                    </div>
                    <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  </div>
                  <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 mb-1 truncate">
                    {workflow.name}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                    {workflow.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Recent Section */}
        {recentWorkflows.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Recent</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {recentWorkflows.map(workflow => (
                <button
                  key={workflow.id}
                  onClick={() => onWorkflowSelect(workflow)}
                  className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all text-left"
                >
                  <div className={`p-2 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded-lg mb-2`}>
                    {automationType === 'local' ? (
                      <Zap className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                    ) : (
                      <Users className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                    )}
                  </div>
                  <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 mb-1 truncate">
                    {workflow.name}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                    {workflow.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Create Button - Centered */}
        <div className="flex items-center justify-center pt-8">
          <button
            onClick={onCreateWorkflow}
            className={`flex items-center gap-3 px-6 py-4 bg-${typeColor}-600 hover:bg-${typeColor}-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all font-medium text-lg`}
          >
            <Plus className="w-6 h-6" />
            <span>Create {automationType === 'local' ? 'Automation' : 'Workflow'}</span>
          </button>
        </div>

        {/* Empty State */}
        {starredWorkflows.length === 0 && recentWorkflows.length === 0 && (
          <div className="text-center py-12">
            <div className={`inline-flex p-4 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded-full mb-4`}>
              {automationType === 'local' ? (
                <Zap className={`w-12 h-12 text-${typeColor}-600 dark:text-${typeColor}-400`} />
              ) : (
                <Users className={`w-12 h-12 text-${typeColor}-600 dark:text-${typeColor}-400`} />
              )}
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              No {automationType === 'local' ? 'Automations' : 'Workflows'} Yet
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
              {automationType === 'local'
                ? 'Create your first automation to streamline background tasks and processes.'
                : 'Create your first team workflow to route work items through stages with your team.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
