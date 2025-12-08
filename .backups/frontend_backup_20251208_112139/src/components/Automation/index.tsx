import { useState, useEffect } from 'react'
import { Briefcase, BarChart, Pencil, Save, Workflow as WorkflowIcon, Trash2, X, AlertTriangle } from 'lucide-react'
import { WorkflowBuilder } from '../WorkflowBuilder'
import { WorkflowQueue } from '../WorkflowQueue'
import { ActiveWorkItem } from '../ActiveWorkItem'
import { WorkflowStatusTracker } from '../WorkflowStatusTracker'
import { WorkflowDesigner } from '../WorkflowDesigner'
import { AutomationToolbar } from './components/AutomationToolbar'
import { CategoryFilter } from './components/CategoryFilter'
import { TemplateGallery } from './components/TemplateGallery'
import { useAutomationTemplates, useAutomationFilters } from './hooks'
import { CATEGORY_OPTIONS } from './shared/categories'
import type { WorkItem, Workflow } from '../../types/workflow'
import type { ViewMode, ViewLayout, WorkflowTemplate } from './types'
import { showToast, showUndoToast } from '@/lib/toast'
import { useUserStore } from '@/stores/userStore'
import { env } from '@/config/env'

export function AutomationTab() {
  // View state
  const [currentView, setCurrentView] = useState<ViewMode>('library')
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [selectedWorkItem, setSelectedWorkItem] = useState<WorkItem | null>(null)
  const [selectedWorkflowForQueue, setSelectedWorkflowForQueue] = useState<string | null>(null)

  // UI state
  const [viewLayout, setViewLayout] = useState<ViewLayout>('grid')
  const [isEditMode, setIsEditMode] = useState(false)
  const [selectedForBulk, setSelectedForBulk] = useState<Set<string>>(new Set())

  // Edit states
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowTemplate | null>(null)
  const [deleteConfirmWorkflow, setDeleteConfirmWorkflow] = useState<WorkflowTemplate | null>(null)
  const [customCategory, setCustomCategory] = useState('')
  const [showCustomInput, setShowCustomInput] = useState(false)

  // Hooks
  const {
    workflows,
    deletedWorkflows,
    toggleFavorite,
    deleteWorkflow,
    restoreWorkflow,
    updateWorkflow,
    bulkDelete,
    emptyTrash,
    reorderWorkflows
  } = useAutomationTemplates()

  const {
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    sortBy,
    setSortBy,
    showFavoritesOnly,
    setShowFavoritesOnly,
    filterWorkflows
  } = useAutomationFilters()

  // Get real user from store
  const { user } = useUserStore()
  const currentUser = {
    id: user?.user_id || 'unknown',
    name: user?.display_name || 'User',
    role: user?.job_role || user?.role || 'member',
  }

  // Auto-delete workflows older than 30 days
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date()
      const stillValid = deletedWorkflows.filter(wf => {
        if (!wf.deletedAt) return true
        const deletedDate = new Date(wf.deletedAt)
        const daysDiff = (now.getTime() - deletedDate.getTime()) / (1000 * 60 * 60 * 24)
        return daysDiff < 30
      })
      if (stillValid.length !== deletedWorkflows.length) {
        // Would update state here if we had access to setDeletedWorkflows
        // This is handled in the hook
      }
    }, 1000 * 60 * 60) // Check every hour

    return () => clearInterval(interval)
  }, [deletedWorkflows])

  const handleCreateFromTemplate = (templateId: string) => {
    const template = workflows.find(w => w.id === templateId)
    setSelectedTemplate(templateId)
    setCurrentView('builder')

    if (template) {
      showToast.success(`Opening ${template.name}`)
    }
  }

  const handleEditWorkflow = (workflow: WorkflowTemplate) => {
    setEditingWorkflow(workflow)
    setShowCustomInput(false)
    setCustomCategory('')
  }

  const handleSaveEdit = () => {
    if (!editingWorkflow) return

    updateWorkflow(editingWorkflow.id, editingWorkflow)
    setEditingWorkflow(null)
  }

  const handleDeleteWorkflow = (workflow: WorkflowTemplate) => {
    setDeleteConfirmWorkflow(workflow)
  }

  const confirmDelete = () => {
    if (!deleteConfirmWorkflow) return

    const workflowToDelete = deleteConfirmWorkflow
    deleteWorkflow(workflowToDelete.id)
    setDeleteConfirmWorkflow(null)
    setEditingWorkflow(null)

    // Show undo toast
    showUndoToast(
      `"${workflowToDelete.name}" moved to trash`,
      () => {
        restoreWorkflow(workflowToDelete.id)
        showToast.success('Workflow restored')
      },
      { duration: 7000 }
    )
  }

  const handleEmptyTrash = () => {
    if (confirm('Are you sure you want to permanently delete all workflows in trash? This cannot be undone.')) {
      emptyTrash()
    }
  }

  const handleToggleBulkSelect = (workflowId: string) => {
    setSelectedForBulk(prev => {
      const newSet = new Set(prev)
      if (newSet.has(workflowId)) {
        newSet.delete(workflowId)
      } else {
        if (newSet.size < 10) {
          newSet.add(workflowId)
        }
      }
      return newSet
    })
  }

  const handleBulkDelete = () => {
    if (selectedForBulk.size === 0) return

    if (confirm(`Delete ${selectedForBulk.size} selected workflows?`)) {
      bulkDelete(Array.from(selectedForBulk))
      setSelectedForBulk(new Set())
    }
  }

  // Apply filters
  const filteredWorkflows = filterWorkflows(workflows)

  // Show different views based on currentView
  if (currentView === 'designer') {
    return (
      <WorkflowDesigner
        onSave={(workflow: Workflow) => {
          console.log('Workflow saved:', workflow)
          setSelectedWorkflowForQueue(workflow.id)
          showToast.success(`Workflow "${workflow.name}" saved! Switching to queue view...`)
          setCurrentView('queue')
        }}
        onCancel={() => {
          setCurrentView('library')
        }}
      />
    )
  }

  if (currentView === 'builder' && selectedTemplate) {
    return (
      <WorkflowBuilder
        templateId={selectedTemplate}
        onBack={() => {
          setCurrentView('library')
          setSelectedTemplate(null)
        }}
      />
    )
  }

  if (currentView === 'queue') {
    if (selectedWorkItem) {
      return (
        <ActiveWorkItem
          workItemId={selectedWorkItem.id}
          userId={currentUser.id}
          onClose={() => setSelectedWorkItem(null)}
          onCompleted={() => {
            setSelectedWorkItem(null)
          }}
        />
      )
    }

    return (
      <WorkflowQueue
        userId={currentUser.id}
        userName={currentUser.name}
        role={currentUser.role}
        workflowId={selectedWorkflowForQueue || undefined}
        onSelectWorkItem={(item) => setSelectedWorkItem(item)}
      />
    )
  }

  if (currentView === 'tracker' && selectedWorkflowForQueue) {
    return (
      <WorkflowStatusTracker
        workflowId={selectedWorkflowForQueue}
        onSelectWorkItem={(item) => {
          setSelectedWorkItem(item)
          setCurrentView('queue')
        }}
      />
    )
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Automation</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Equipping the global church to do more with less
              </p>
            </div>
            {/* Dev Mode Status Pill - Only shown in development */}
            {env.isDev && (
              <div className="flex items-center gap-2 px-2 py-1 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-xs">
                <span className="text-blue-700 dark:text-blue-300 font-medium">
                  {user?.user_id || 'No User'} | {user?.role || 'No Role'}
                  {selectedWorkflowForQueue && ` | Workflow: ${selectedWorkflowForQueue.slice(0, 8)}`}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentView('tracker')}
              disabled={!selectedWorkflowForQueue}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-700 dark:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <BarChart className="w-4 h-4" />
              Tracker
            </button>
            <button
              onClick={() => setCurrentView('queue')}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-700 dark:text-gray-300"
            >
              <Briefcase className="w-4 h-4" />
              My Work
            </button>
            <button
              onClick={() => {
                if (isEditMode) {
                  setIsEditMode(false)
                  setSelectedForBulk(new Set())
                } else {
                  setIsEditMode(true)
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-700 dark:text-gray-300"
            >
              {isEditMode ? (
                <>
                  <Save className="w-4 h-4" />
                  Save
                </>
              ) : (
                <>
                  <Pencil className="w-4 h-4" />
                  Edit Library
                </>
              )}
            </button>
            <button
              onClick={() => setCurrentView('designer')}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <WorkflowIcon className="w-4 h-4" />
              Create Workflow
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Deleted Workflows (Trash) */}
        {deletedWorkflows.length > 0 && (
          <div className="mb-8 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-red-900 dark:text-red-100 flex items-center gap-2">
                <Trash2 className="w-5 h-5" />
                Deleted Workflows ({deletedWorkflows.length})
              </h2>
              <button
                onClick={handleEmptyTrash}
                className="text-sm text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 font-medium"
              >
                Empty Trash
              </button>
            </div>
            <p className="text-xs text-red-700 dark:text-red-300 mb-3">
              Auto-deletes after 30 days
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {deletedWorkflows.map(workflow => {
                const Icon = require('./shared/icons').WORKFLOW_ICONS[workflow.id]
                const category = require('./shared/categories').CATEGORY_INFO[workflow.category]

                return (
                  <div
                    key={workflow.id}
                    className="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg opacity-60"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <div className="p-1.5 bg-gray-100 dark:bg-gray-700 rounded">
                          <Icon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
                            {workflow.name}
                          </h3>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {category.label}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => restoreWorkflow(workflow.id)}
                        className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
                      >
                        Restore
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Library Section */}
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Library
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {isEditMode
                ? 'Click tiles to select (max 10). Cmd+Click and drag to reorder.'
                : 'Start with a pre-built workflow and customize it to your needs'
              }
            </p>
          </div>

          {/* Toolbar */}
          <div className="mb-4">
            <AutomationToolbar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              sortBy={sortBy}
              onSortChange={setSortBy}
              viewLayout={viewLayout}
              onViewLayoutChange={setViewLayout}
              showFavoritesOnly={showFavoritesOnly}
              onToggleFavorites={() => setShowFavoritesOnly(!showFavoritesOnly)}
              isEditMode={isEditMode}
              selectedCount={selectedForBulk.size}
              onBulkDelete={handleBulkDelete}
            />
          </div>

          {/* Category Filter */}
          <div className="mb-6">
            <CategoryFilter
              selectedCategory={selectedCategory}
              onCategoryChange={setSelectedCategory}
            />
          </div>

          {/* Gallery */}
          <TemplateGallery
            workflows={filteredWorkflows}
            viewLayout={viewLayout}
            isEditMode={isEditMode}
            selectedForBulk={selectedForBulk}
            onSelectWorkflow={handleCreateFromTemplate}
            onToggleFavorite={toggleFavorite}
            onEditWorkflow={handleEditWorkflow}
            onUseInQueue={(id) => {
              setSelectedWorkflowForQueue(id)
              setCurrentView('queue')
              const workflow = workflows.find(w => w.id === id)
              if (workflow) {
                showToast.success(`Using "${workflow.name}" in queue view`)
              }
            }}
            onQuickDelete={handleDeleteWorkflow}
            onToggleBulkSelect={handleToggleBulkSelect}
            onReorder={reorderWorkflows}
            onCreateCustom={() => setCurrentView('designer')}
          />
        </div>
      </div>

      {/* Edit Modal */}
      {editingWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Edit Workflow
            </h3>

            {/* Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Name
              </label>
              <input
                type="text"
                value={editingWorkflow.name}
                onChange={(e) => setEditingWorkflow({ ...editingWorkflow, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>

            {/* Category */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category
              </label>
              <select
                value={editingWorkflow.category}
                onChange={(e) => {
                  if (e.target.value === 'custom') {
                    setShowCustomInput(true)
                  } else {
                    setEditingWorkflow({ ...editingWorkflow, category: e.target.value as any })
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              >
                {CATEGORY_OPTIONS.map(cat => (
                  <option key={cat.value} value={cat.value}>
                    {cat.emoji} {cat.label}
                  </option>
                ))}
                <option value="custom">+ Add Custom</option>
              </select>
            </div>

            {/* Custom Category Input */}
            {showCustomInput && (
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Enter custom category name"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && customCategory.trim()) {
                      setShowCustomInput(false)
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  autoFocus
                />
              </div>
            )}

            {/* Description */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Description
              </label>
              <textarea
                value={editingWorkflow.description}
                onChange={(e) => setEditingWorkflow({ ...editingWorkflow, description: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between">
              {/* Delete */}
              <button
                onClick={() => handleDeleteWorkflow(editingWorkflow)}
                className="flex items-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg font-medium transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>

              {/* Save & Cancel */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setEditingWorkflow(null)}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Delete Workflow?
              </h3>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              You are about to delete <span className="font-semibold">"{deleteConfirmWorkflow.name}"</span> automation workflow.
              It will be moved to trash and auto-deleted after 30 days. Are you sure?
            </p>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteConfirmWorkflow(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg font-medium transition-colors"
              >
                No, Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Wiggle Animation CSS */}
      <style>{`
        @keyframes wiggle {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-1deg); }
          75% { transform: rotate(1deg); }
        }
        .animate-wiggle {
          animation: wiggle 0.3s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}
