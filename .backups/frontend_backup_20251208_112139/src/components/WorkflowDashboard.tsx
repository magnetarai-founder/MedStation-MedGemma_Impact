/**
 * Workflow Dashboard - Initial view when opening Automation
 *
 * Layout:
 * - Starred workflows (up to 5, horizontal)
 * - Recent workflows (horizontal)
 * - Centered Create button
 */

import { Plus, Star, Clock, Zap, Users, Layers, Wand2, Info, Filter } from 'lucide-react'
import { useWorkflows, useStarredWorkflows, useStarWorkflow, useUnstarWorkflow } from '@/hooks/useWorkflowQueue'
import type { Workflow, WorkflowVisibility } from '@/types/workflow'
import type { AutomationType } from './AutomationWorkspace'
import { useState, useMemo } from 'react'
import VisibilityBadge from './Automation/components/VisibilityBadge'
import { useUserStore } from '@/stores/userStore'

interface WorkflowDashboardProps {
  automationType: AutomationType
  onWorkflowSelect: (workflow: Workflow) => void
  onCreateWorkflow: () => void
  onViewTemplates?: () => void
}

// T3-2: Scope filter type
type ScopeFilter = 'all' | 'personal' | 'team' | 'global'

export function WorkflowDashboard({
  automationType,
  onWorkflowSelect,
  onCreateWorkflow,
  onViewTemplates
}: WorkflowDashboardProps) {
  // Fetch workflows from backend filtered by type
  const { data: workflows = [], isLoading } = useWorkflows({ workflow_type: automationType })
  const { data: starredIds = [] } = useStarredWorkflows(automationType)
  const starMutation = useStarWorkflow()
  const unstarMutation = useUnstarWorkflow()
  const user = useUserStore((state) => state.user)

  // T3-2: Scope filter state
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all')
  const [showAgentLearnMore, setShowAgentLearnMore] = useState(false)

  // T3-2: Apply scope filter
  const filteredWorkflows = useMemo(() => {
    if (scopeFilter === 'all') return workflows

    return workflows.filter(workflow => {
      const visibility = workflow.visibility || 'personal' // Default to personal for backward compatibility

      if (scopeFilter === 'personal') {
        return visibility === 'personal' && workflow.owner_user_id === user?.userId
      } else if (scopeFilter === 'team') {
        return visibility === 'team'
      } else if (scopeFilter === 'global') {
        return visibility === 'global'
      }
      return true
    })
  }, [workflows, scopeFilter, user?.userId])

  // Filter starred and recent workflows from filtered set
  const starredWorkflows: Workflow[] = filteredWorkflows.filter(w => starredIds.includes(w.id))
  const recentWorkflows: Workflow[] = filteredWorkflows.filter(w => !starredIds.includes(w.id)).slice(0, 10)

  // Check if user has any agent-enabled workflows
  const agentWorkflows = workflows.filter(w =>
    !w.is_template && w.stages?.some(s => s.stage_type === 'agent_assist')
  )
  const hasNoAgentWorkflows = workflows.length > 0 && agentWorkflows.length === 0

  const handleToggleStar = async (e: React.MouseEvent, workflowId: string) => {
    e.stopPropagation()

    const isStarred = starredIds.includes(workflowId)

    try {
      if (isStarred) {
        await unstarMutation.mutateAsync(workflowId)
      } else {
        await starMutation.mutateAsync(workflowId)
      }
    } catch (error) {
      console.error('Failed to toggle star:', error)
      alert(error instanceof Error ? error.message : 'Failed to update star status')
    }
  }

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
        {/* T3-2: Scope Filter */}
        {workflows.length > 0 && (
          <div className="flex items-center gap-3 pb-2">
            <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <label htmlFor="scope-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Scope:
            </label>
            <select
              id="scope-filter"
              value={scopeFilter}
              onChange={(e) => setScopeFilter(e.target.value as ScopeFilter)}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
              aria-label="Filter workflows by scope"
            >
              <option value="all">All Workflows</option>
              <option value="personal">My Workflows</option>
              <option value="team">Team Workflows</option>
              <option value="global">Global Workflows</option>
            </select>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ({filteredWorkflows.length} {filteredWorkflows.length === 1 ? 'workflow' : 'workflows'})
            </span>
          </div>
        )}

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
                  className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all text-left relative group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className={`p-2 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded-lg`}>
                      {automationType === 'local' ? (
                        <Zap className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      ) : (
                        <Users className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      )}
                    </div>
                    <button
                      onClick={(e) => handleToggleStar(e, workflow.id)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                      disabled={starMutation.isPending || unstarMutation.isPending}
                    >
                      <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate flex-1">
                      {workflow.name}
                    </h3>
                    {workflow.is_template && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 text-[10px] font-medium rounded">
                        <Layers className="w-2.5 h-2.5" />
                        TEMPLATE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-2">
                    {workflow.description}
                  </p>
                  {/* T3-2: Visibility Badge */}
                  <div className="mt-auto">
                    <VisibilityBadge visibility={workflow.visibility} />
                  </div>
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
                  className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all text-left relative group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className={`p-2 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded-lg`}>
                      {automationType === 'local' ? (
                        <Zap className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      ) : (
                        <Users className={`w-4 h-4 text-${typeColor}-600 dark:text-${typeColor}-400`} />
                      )}
                    </div>
                    <button
                      onClick={(e) => handleToggleStar(e, workflow.id)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors opacity-0 group-hover:opacity-100"
                      disabled={starMutation.isPending || unstarMutation.isPending}
                    >
                      <Star className="w-4 h-4 text-gray-400 hover:text-yellow-400" />
                    </button>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate flex-1">
                      {workflow.name}
                    </h3>
                    {workflow.is_template && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 text-[10px] font-medium rounded">
                        <Layers className="w-2.5 h-2.5" />
                        TEMPLATE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-2">
                    {workflow.description}
                  </p>
                  {/* T3-2: Visibility Badge */}
                  <div className="mt-auto">
                    <VisibilityBadge visibility={workflow.visibility} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Agent Workflow CTA */}
        {hasNoAgentWorkflows && onViewTemplates && (
          <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-2 border-purple-200 dark:border-purple-800 rounded-xl p-6 shadow-lg">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/40 rounded-lg">
                <Wand2 className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
                  Create your first Agent-enabled workflow
                </h3>
                <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
                  Pick a template with Agent Assist, then customize it. Agent Assist stages let AI propose code changes while you stay in control.
                </p>

                {showAgentLearnMore && (
                  <div className="mb-4 p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-purple-200 dark:border-purple-700">
                    <p className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                      <span className="block">• <strong>Agent Assist stages</strong> ask AI to propose plans or patches for work items</span>
                      <span className="block">• <strong>You review and approve</strong> all changes before they're applied</span>
                      <span className="block">• <strong>Auto-apply mode</strong> can be enabled per-stage for trusted workflows</span>
                    </p>
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <button
                    onClick={onViewTemplates}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg shadow hover:shadow-lg transition-all font-medium"
                  >
                    <Layers className="w-4 h-4" />
                    Browse templates
                  </button>
                  <button
                    onClick={() => setShowAgentLearnMore(!showAgentLearnMore)}
                    className="flex items-center gap-2 px-4 py-2 border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors text-sm"
                  >
                    <Info className="w-4 h-4" />
                    {showAgentLearnMore ? 'Hide details' : 'Learn about Agent Assist'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons - Centered */}
        <div className="flex items-center justify-center gap-4 pt-8">
          <button
            onClick={onCreateWorkflow}
            className={`flex items-center gap-3 px-6 py-4 bg-${typeColor}-600 hover:bg-${typeColor}-700 text-white rounded-xl shadow-lg hover:shadow-xl transition-all font-medium text-lg`}
          >
            <Plus className="w-6 h-6" />
            <span>Create {automationType === 'local' ? 'Automation' : 'Workflow'}</span>
          </button>

          {onViewTemplates && (
            <button
              onClick={onViewTemplates}
              className="flex items-center gap-3 px-6 py-4 border-2 border-amber-500 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-xl shadow-lg hover:shadow-xl transition-all font-medium text-lg"
            >
              <Layers className="w-6 h-6" />
              <span>Browse Templates</span>
            </button>
          )}
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
