/**
 * Automation Workspace - Unified workflow and automation management
 *
 * Provides two automation types:
 * - Local Automation: n8n-style visual workflow builder for background processes
 * - Team Workflow: Stage-based workflows with queue system for human tasks
 */

import { useState } from 'react'
import { Zap, Users } from 'lucide-react'
import { WorkflowTreeSidebar } from './WorkflowTreeSidebar'
import { WorkflowDashboard } from './WorkflowDashboard'
import { WorkflowBuilder } from './WorkflowBuilder'
import { WorkflowDesigner } from './WorkflowDesigner'
import { WorkflowQueue } from './WorkflowQueue'
import { ActiveWorkItem } from './ActiveWorkItem'
import { WorkflowStatusTracker } from './WorkflowStatusTracker'
import { useUserStore } from '@/stores/userStore'
import type { Workflow, WorkItem } from '@/types/workflow'

export type AutomationType = 'local' | 'team'

export function AutomationWorkspace() {
  // Load persisted automation type from localStorage
  const [automationType, setAutomationType] = useState<AutomationType>(() => {
    const stored = localStorage.getItem('automation_type')
    return (stored === 'local' || stored === 'team') ? stored : 'local'
  })

  // Current view state
  const [currentView, setCurrentView] = useState<'dashboard' | 'builder' | 'designer' | 'queue' | 'tracker'>('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [selectedWorkItem, setSelectedWorkItem] = useState<WorkItem | null>(null)

  const { user } = useUserStore()

  // Persist automation type selection
  const handleTypeChange = (type: AutomationType) => {
    setAutomationType(type)
    localStorage.setItem('automation_type', type)
    // Reset to dashboard when switching types
    setCurrentView('dashboard')
    setSelectedWorkflow(null)
  }

  // Handle workflow selection from tree
  const handleWorkflowSelect = (workflow: Workflow) => {
    setSelectedWorkflow(workflow)
    if (workflow.workflow_type === 'local') {
      setCurrentView('builder')
    } else {
      setCurrentView('designer')
    }
  }

  // Handle new workflow creation
  const handleCreateWorkflow = () => {
    setSelectedWorkflow(null)
    if (automationType === 'local') {
      setCurrentView('builder')
    } else {
      setCurrentView('designer')
    }
  }

  // Render builder based on view
  const renderContent = () => {
    // Dashboard view (default)
    if (currentView === 'dashboard') {
      return (
        <WorkflowDashboard
          automationType={automationType}
          onWorkflowSelect={handleWorkflowSelect}
          onCreateWorkflow={handleCreateWorkflow}
        />
      )
    }

    // Local Automation Builder (n8n-style)
    if (currentView === 'builder') {
      return (
        <WorkflowBuilder
          templateId={selectedWorkflow?.id}
          onBack={() => {
            setCurrentView('dashboard')
            setSelectedWorkflow(null)
          }}
        />
      )
    }

    // Team Workflow Designer (stage-based)
    if (currentView === 'designer') {
      return (
        <WorkflowDesigner
          onSave={(workflow: Workflow) => {
            setSelectedWorkflow(workflow)
            setCurrentView('queue')
          }}
          onCancel={() => {
            setCurrentView('dashboard')
            setSelectedWorkflow(null)
          }}
        />
      )
    }

    // Queue view (Team Workflow only)
    if (currentView === 'queue') {
      if (selectedWorkItem) {
        return (
          <ActiveWorkItem
            workItemId={selectedWorkItem.id}
            userId={user?.user_id || ''}
            onClose={() => setSelectedWorkItem(null)}
            onCompleted={() => {
              setSelectedWorkItem(null)
            }}
          />
        )
      }

      return (
        <WorkflowQueue
          userId={user?.user_id || ''}
          userName={user?.display_name || 'User'}
          role={user?.job_role || user?.role || 'member'}
          workflowId={selectedWorkflow?.id}
          onSelectWorkItem={(item) => setSelectedWorkItem(item)}
        />
      )
    }

    // Tracker view (Team Workflow only)
    if (currentView === 'tracker' && selectedWorkflow) {
      return (
        <WorkflowStatusTracker
          workflowId={selectedWorkflow.id}
          onSelectWorkItem={(item) => {
            setSelectedWorkItem(item)
            setCurrentView('queue')
          }}
        />
      )
    }

    return null
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* View Actions - Only show for Team Workflow when not on dashboard */}
      {automationType === 'team' && currentView !== 'dashboard' && (
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
            >
              Dashboard
            </button>
            <button
              onClick={() => setCurrentView('queue')}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
            >
              My Work
            </button>
            {selectedWorkflow && (
              <button
                onClick={() => setCurrentView('tracker')}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50 rounded-md transition-colors"
              >
                Tracker
              </button>
            )}
          </div>
        </div>
      )}

      {/* Two-pane layout */}
      <div className="flex-1 flex min-h-0">
        {/* Left Pane - Workflow Tree */}
        <WorkflowTreeSidebar
          automationType={automationType}
          onAutomationTypeChange={handleTypeChange}
          selectedWorkflowId={selectedWorkflow?.id}
          onWorkflowSelect={handleWorkflowSelect}
          onViewQueue={() => setCurrentView('queue')}
        />

        {/* Right Pane - Content Area */}
        <div className="flex-1 min-w-0">
          {renderContent()}
        </div>
      </div>
    </div>
  )
}
