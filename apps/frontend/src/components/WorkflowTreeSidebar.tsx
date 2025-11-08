/**
 * Workflow Tree Sidebar - VS Code-style file tree for workflows
 *
 * Features:
 * - Folder organization with drag-drop
 * - Star up to 5 workflows per type
 * - My Team Workflows / My Local Automations
 * - My Work Queue (for Team Workflow mode)
 */

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronRight, Folder, Star, Plus, Briefcase, Zap, Users, ListChecks } from 'lucide-react'
import { useWorkflows } from '@/hooks/useWorkflowQueue'
import type { Workflow } from '@/types/workflow'
import type { AutomationType } from './AutomationWorkspace'

interface WorkflowTreeSidebarProps {
  automationType: AutomationType
  onAutomationTypeChange: (type: AutomationType) => void
  selectedWorkflowId?: string
  onWorkflowSelect: (workflow: Workflow) => void
  onViewQueue: () => void
}

export function WorkflowTreeSidebar({
  automationType,
  onAutomationTypeChange,
  selectedWorkflowId,
  onWorkflowSelect,
  onViewQueue
}: WorkflowTreeSidebarProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['workflows', 'queue']))
  const [queueCount, setQueueCount] = useState(0)
  const [queueFailures, setQueueFailures] = useState(0)
  const [queueCooldownUntil, setQueueCooldownUntil] = useState<number>(0)

  // Fetch workflows from backend filtered by type
  const { data: workflows = [], isLoading } = useWorkflows({ workflow_type: automationType })

  // Poll queue status with cooldown on 429
  useEffect(() => {
    const pollQueues = async () => {
      // Stop polling after 3 consecutive failures
      if (queueFailures >= 3) return

      // Respect cooldown after rate limit
      if (Date.now() < queueCooldownUntil) return

      // Get auth token
      const token = localStorage.getItem('auth_token')
      if (!token) return // Don't poll if not authenticated

      try {
        const response = await fetch('/api/v1/monitoring/metal4', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (!response.ok) {
          if ((response as any).status === 429) {
            setQueueCooldownUntil(Date.now() + 60_000)
          }
          setQueueFailures(prev => prev + 1)
          return
        }

        const data = await response.json()

        // Sum active_buffers across all queues
        let total = 0
        if (data.queues) {
          for (const queue of Object.values(data.queues)) {
            if (typeof queue === 'object' && queue !== null && 'active_buffers' in queue) {
              total += (queue as { active_buffers: number }).active_buffers || 0
            }
          }
        }

        setQueueCount(total)
        setQueueFailures(0) // Reset on success
      } catch {
        setQueueFailures(prev => prev + 1)
      }
    }

    pollQueues() // Initial poll
    const interval = setInterval(pollQueues, 10000) // Every 10 seconds
    return () => clearInterval(interval)
  }, [queueFailures, queueCooldownUntil])

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(folderId)) {
        next.delete(folderId)
      } else {
        next.add(folderId)
      }
      return next
    })
  }

  const isExpanded = (folderId: string) => expandedFolders.has(folderId)

  return (
    <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30 flex flex-col">
      {/* Tabs - Local vs Team */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="flex">
          <button
            onClick={() => onAutomationTypeChange('local')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
              automationType === 'local'
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <Zap className="w-4 h-4" />
              <span>Local</span>
            </div>
            {automationType === 'local' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
            )}
          </button>
          <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 self-center" />
          <button
            onClick={() => onAutomationTypeChange('team')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
              automationType === 'team'
                ? 'text-purple-600 dark:text-purple-400'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <Users className="w-4 h-4" />
              <span>Team</span>
            </div>
            {automationType === 'team' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 dark:bg-purple-400" />
            )}
          </button>
        </div>
      </div>

      {/* Workflows Section */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="mb-2">
          <button
            onClick={() => toggleFolder('workflows')}
            className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
          >
            {isExpanded('workflows') ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            {automationType === 'local' ? (
              <Zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            ) : (
              <Users className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            )}
            <span className="font-medium flex-1">
              {automationType === 'local' ? 'My Local Automations' : 'My Team Workflows'}
            </span>
          </button>

          {isExpanded('workflows') && (
            <div className="ml-6 mt-1 space-y-1">
              {isLoading ? (
                <div className="px-2 py-2 text-xs text-gray-500 dark:text-gray-400">
                  Loading workflows...
                </div>
              ) : workflows.length === 0 ? (
                <div className="px-2 py-2 text-xs text-gray-500 dark:text-gray-400">
                  No workflows yet
                </div>
              ) : (
                workflows.map(workflow => (
                  <button
                    key={workflow.id}
                    onClick={() => onWorkflowSelect(workflow)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-md transition-colors ${
                      selectedWorkflowId === workflow.id
                        ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                    }`}
                  >
                    <span className="flex-1 truncate">{workflow.name}</span>
                  </button>
                ))
              )}

              {/* Add New Folder */}
              <button className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors">
                <Plus className="w-3.5 h-3.5" />
                <span>New Folder</span>
              </button>
            </div>
          )}
        </div>

        {/* My Work Queue - Team Workflow Only */}
        {automationType === 'team' && (
          <div className="mt-2">
            <button
              onClick={() => toggleFolder('queue')}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
            >
              {isExpanded('queue') ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
              <ListChecks className="w-4 h-4 text-orange-600 dark:text-orange-400" />
              <span className="font-medium flex-1">My Work Queue</span>
              {queueCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs bg-orange-600 text-white rounded-full">
                  {queueCount}
                </span>
              )}
            </button>

            {isExpanded('queue') && (
              <div className="ml-6 mt-1 space-y-1">
                {queueCount === 0 ? (
                  <div className="px-2 py-2 text-xs text-gray-500 dark:text-gray-400">
                    No active work items
                  </div>
                ) : (
                  <button
                    onClick={onViewQueue}
                    className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
                  >
                    <Briefcase className="w-4 h-4" />
                    <span>View Queue</span>
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
