import { useState, useEffect } from 'react'
import { Plus, FileText, Users, DollarSign, Plane, BookOpen, Heart, Calendar, UserPlus, ChurchIcon as Church, Star, Pencil, Trash2, X, Save, AlertTriangle, Briefcase, BarChart } from 'lucide-react'
import { WorkflowBuilder } from './WorkflowBuilder'
import { WorkflowQueue } from './WorkflowQueue'
import { ActiveWorkItem } from './ActiveWorkItem'
import { WorkflowStatusTracker } from './WorkflowStatusTracker'
import { ReactFlowProvider } from 'reactflow'
import type { WorkItem } from '../types/workflow'

interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: 'clinic' | 'ministry' | 'admin' | 'education' | 'travel'
  icon: React.ComponentType<{ className?: string }>
  nodes: number
  isFavorited?: boolean
  order?: number
  deletedAt?: string | null
}

const INITIAL_WORKFLOWS: WorkflowTemplate[] = [
  // Field/Clinic
  {
    id: 'clinic-intake',
    name: 'Clinic Intake Form',
    description: 'Patient information collection and AI-powered summary',
    category: 'clinic',
    icon: FileText,
    nodes: 4,
    isFavorited: true,
    order: 1
  },

  // Ministry/Church
  {
    id: 'worship-planning',
    name: 'Worship Service Planner',
    description: 'Plan songs, scripture, announcements, and auto-generate bulletin',
    category: 'ministry',
    icon: Users,
    nodes: 5,
    isFavorited: true,
    order: 2
  },
  {
    id: 'visitor-followup',
    name: 'Visitor Follow-up',
    description: 'Personalized welcome emails and scheduled follow-up calls',
    category: 'ministry',
    icon: UserPlus,
    nodes: 4,
    isFavorited: true,
    order: 3
  },
  {
    id: 'small-group-coordinator',
    name: 'Small Group Coordinator',
    description: 'Manage sign-ups, balance groups, and send group info',
    category: 'ministry',
    icon: Users,
    nodes: 5
  },
  {
    id: 'prayer-request-router',
    name: 'Prayer Request Router',
    description: 'Route prayer requests to care teams with follow-up reminders',
    category: 'ministry',
    icon: Heart,
    nodes: 4
  },
  {
    id: 'event-manager',
    name: 'Event Manager',
    description: 'Auto-post events, email congregation, and track RSVPs',
    category: 'ministry',
    icon: Calendar,
    nodes: 6
  },

  // Admin/Finance
  {
    id: 'donation-tracker',
    name: 'Donation Manager',
    description: 'Auto thank-you letters, update records, and generate tax receipts',
    category: 'admin',
    icon: DollarSign,
    nodes: 5,
    isFavorited: true,
    order: 4
  },
  {
    id: 'volunteer-scheduler',
    name: 'Volunteer Scheduler',
    description: 'Coordinate volunteers and send automated reminders',
    category: 'admin',
    icon: Calendar,
    nodes: 4
  },

  // Education
  {
    id: 'curriculum-builder',
    name: 'Curriculum Builder',
    description: 'Plan lessons and track student progress',
    category: 'education',
    icon: BookOpen,
    nodes: 4
  },
  {
    id: 'sunday-school-coordinator',
    name: 'Sunday School Coordinator',
    description: 'Manage attendance, send parent updates, and track progress',
    category: 'education',
    icon: BookOpen,
    nodes: 5
  },

  // Travel/Logistics
  {
    id: 'trip-planner',
    name: 'Mission Trip Planner',
    description: 'Organize travel logistics, itinerary, and team communication',
    category: 'travel',
    icon: Plane,
    nodes: 6
  },
]

const CATEGORY_OPTIONS = [
  { value: 'clinic', label: 'Clinic', emoji: '🏥' },
  { value: 'ministry', label: 'Ministry', emoji: '⛪' },
  { value: 'admin', label: 'Admin', emoji: '💰' },
  { value: 'education', label: 'Education', emoji: '📚' },
  { value: 'travel', label: 'Travel', emoji: '✈️' }
]

const CATEGORY_INFO = {
  clinic: { label: 'Clinic', emoji: '🏥', color: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' },
  ministry: { label: 'Ministry', emoji: '⛪', color: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800' },
  admin: { label: 'Admin', emoji: '💰', color: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' },
  education: { label: 'Education', emoji: '📚', color: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' },
  travel: { label: 'Travel', emoji: '✈️', color: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' }
}

export function AutomationTab() {
  // View state
  const [currentView, setCurrentView] = useState<'library' | 'builder' | 'queue' | 'tracker'>('library')
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [selectedWorkItem, setSelectedWorkItem] = useState<WorkItem | null>(null)
  const [selectedWorkflowForQueue, setSelectedWorkflowForQueue] = useState<string | null>(null)

  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>(INITIAL_WORKFLOWS)
  const [deletedWorkflows, setDeletedWorkflows] = useState<WorkflowTemplate[]>([])

  // Edit states
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowTemplate | null>(null)
  const [deleteConfirmWorkflow, setDeleteConfirmWorkflow] = useState<WorkflowTemplate | null>(null)
  const [hoveredWorkflow, setHoveredWorkflow] = useState<string | null>(null)

  // Edit Library mode
  const [isEditMode, setIsEditMode] = useState(false)
  const [selectedForBulk, setSelectedForBulk] = useState<Set<string>>(new Set())

  // Drag state
  const [draggedWorkflow, setDraggedWorkflow] = useState<string | null>(null)
  const [dragOverWorkflow, setDragOverWorkflow] = useState<string | null>(null)

  // Custom category input
  const [customCategory, setCustomCategory] = useState('')
  const [showCustomInput, setShowCustomInput] = useState(false)

  // Mock user data (in production, get from auth context)
  const currentUser = {
    id: 'user_1',
    name: 'Current User',
    role: 'intake_worker',
  }

  // Auto-delete workflows older than 30 days
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date()
      setDeletedWorkflows(prev =>
        prev.filter(wf => {
          if (!wf.deletedAt) return true
          const deletedDate = new Date(wf.deletedAt)
          const daysDiff = (now.getTime() - deletedDate.getTime()) / (1000 * 60 * 60 * 24)
          return daysDiff < 30
        })
      )
    }, 1000 * 60 * 60) // Check every hour

    return () => clearInterval(interval)
  }, [])

  const handleCreateFromTemplate = (templateId: string) => {
    setSelectedTemplate(templateId)
    setCurrentView('builder')
  }

  const handleBackToTemplates = () => {
    setSelectedTemplate(null)
    setCurrentView('library')
  }

  const handleToggleFavorite = (workflowId: string) => {
    setWorkflows(prev =>
      prev.map(wf =>
        wf.id === workflowId
          ? { ...wf, isFavorited: !wf.isFavorited }
          : wf
      )
    )
  }

  const handleEditWorkflow = (workflow: WorkflowTemplate) => {
    setEditingWorkflow(workflow)
    setShowCustomInput(false)
    setCustomCategory('')
  }

  const handleSaveEdit = () => {
    if (!editingWorkflow) return

    setWorkflows(prev =>
      prev.map(wf =>
        wf.id === editingWorkflow.id
          ? editingWorkflow
          : wf
      )
    )
    setEditingWorkflow(null)
  }

  const handleDeleteWorkflow = (workflow: WorkflowTemplate) => {
    setDeleteConfirmWorkflow(workflow)
  }

  const confirmDelete = () => {
    if (!deleteConfirmWorkflow) return

    // Move to trash
    const deletedWorkflow = { ...deleteConfirmWorkflow, deletedAt: new Date().toISOString() }
    setDeletedWorkflows(prev => [...prev, deletedWorkflow])
    setWorkflows(prev => prev.filter(wf => wf.id !== deleteConfirmWorkflow.id))
    setDeleteConfirmWorkflow(null)
    setEditingWorkflow(null)
  }

  const handleRestoreWorkflow = (workflowId: string) => {
    const workflow = deletedWorkflows.find(wf => wf.id === workflowId)
    if (!workflow) return

    setWorkflows(prev => [...prev, { ...workflow, deletedAt: null }])
    setDeletedWorkflows(prev => prev.filter(wf => wf.id !== workflowId))
  }

  const handleEmptyTrash = () => {
    if (confirm('Are you sure you want to permanently delete all workflows in trash? This cannot be undone.')) {
      setDeletedWorkflows([])
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
      const now = new Date().toISOString()
      const toDelete = workflows.filter(wf => selectedForBulk.has(wf.id))
      const deletedWithTimestamp = toDelete.map(wf => ({ ...wf, deletedAt: now }))

      setDeletedWorkflows(prev => [...prev, ...deletedWithTimestamp])
      setWorkflows(prev => prev.filter(wf => !selectedForBulk.has(wf.id)))
      setSelectedForBulk(new Set())
    }
  }

  const handleQuickDelete = (workflow: WorkflowTemplate) => {
    setDeleteConfirmWorkflow(workflow)
  }

  const handleDragStart = (e: React.DragEvent, workflowId: string) => {
    if (e.metaKey || e.ctrlKey) {
      setDraggedWorkflow(workflowId)
    }
  }

  const handleDragOver = (e: React.DragEvent, workflowId: string) => {
    e.preventDefault()
    if (draggedWorkflow && draggedWorkflow !== workflowId) {
      setDragOverWorkflow(workflowId)
    }
  }

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault()
    if (!draggedWorkflow || draggedWorkflow === targetId) return

    const draggedIdx = workflows.findIndex(wf => wf.id === draggedWorkflow)
    const targetIdx = workflows.findIndex(wf => wf.id === targetId)

    if (draggedIdx === -1 || targetIdx === -1) return

    const draggedWf = workflows[draggedIdx]
    const targetWf = workflows[targetIdx]

    // Don't allow non-favorited above favorited
    if (!draggedWf.isFavorited && targetWf.isFavorited) return

    // Reorder
    const newWorkflows = [...workflows]
    newWorkflows.splice(draggedIdx, 1)
    newWorkflows.splice(targetIdx, 0, draggedWf)

    setWorkflows(newWorkflows)
    setDraggedWorkflow(null)
    setDragOverWorkflow(null)
  }

  // Sort workflows: favorited first, then by order
  const sortedWorkflows = [...workflows].sort((a, b) => {
    if (a.isFavorited && !b.isFavorited) return -1
    if (!a.isFavorited && b.isFavorited) return 1
    return (a.order || 999) - (b.order || 999)
  })

  // Show different views based on currentView
  if (currentView === 'builder' && selectedTemplate) {
    return (
      <ReactFlowProvider>
        <WorkflowBuilder
          templateId={selectedTemplate}
          onBack={() => {
            setCurrentView('library')
            setSelectedTemplate(null)
          }}
        />
      </ReactFlowProvider>
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
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Automation</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Equipping the global church to do more with less
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentView('queue')}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg font-medium transition-colors text-gray-700 dark:text-gray-300"
            >
              <Briefcase className="w-4 h-4" />
              My Work
            </button>
            <button
              onClick={() => setCurrentView('tracker')}
              disabled={!selectedWorkflowForQueue}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg font-medium transition-colors text-gray-700 dark:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <BarChart className="w-4 h-4" />
              Tracker
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
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg font-medium transition-colors text-gray-700 dark:text-gray-300"
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
            <button className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors">
              <Plus className="w-4 h-4" />
              New Workflow
            </button>
          </div>
        </div>

        {/* Bulk Actions Bar */}
        {isEditMode && selectedForBulk.size > 0 && (
          <div className="mt-4 flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
              {selectedForBulk.size} selected {selectedForBulk.size === 10 && '(max)'}
            </span>
            <button
              onClick={handleBulkDelete}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete Selected
            </button>
          </div>
        )}
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
                const category = CATEGORY_INFO[workflow.category]
                const Icon = workflow.icon

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
                        onClick={() => handleRestoreWorkflow(workflow.id)}
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

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedWorkflows.map((workflow) => {
              const category = CATEGORY_INFO[workflow.category]
              const Icon = workflow.icon
              const isHovered = hoveredWorkflow === workflow.id
              const isSelected = selectedForBulk.has(workflow.id)
              const isDragging = draggedWorkflow === workflow.id
              const isDragOver = dragOverWorkflow === workflow.id

              return (
                <div
                  key={workflow.id}
                  draggable={!isEditMode}
                  onDragStart={(e) => handleDragStart(e, workflow.id)}
                  onDragOver={(e) => handleDragOver(e, workflow.id)}
                  onDrop={(e) => handleDrop(e, workflow.id)}
                  onDragEnd={() => {
                    setDraggedWorkflow(null)
                    setDragOverWorkflow(null)
                  }}
                  onMouseEnter={() => setHoveredWorkflow(workflow.id)}
                  onMouseLeave={() => setHoveredWorkflow(null)}
                  onClick={() => {
                    if (isEditMode) {
                      handleToggleBulkSelect(workflow.id)
                    } else {
                      handleCreateFromTemplate(workflow.id)
                    }
                  }}
                  className={`
                    relative text-left p-4 bg-white dark:bg-gray-800 border rounded-lg transition-all cursor-pointer
                    ${isDragging ? 'opacity-50 scale-95' : ''}
                    ${isDragOver ? 'border-primary-500 ring-2 ring-primary-200' : 'border-gray-200 dark:border-gray-700'}
                    ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : ''}
                    ${isEditMode ? 'hover:scale-105' : 'hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600'}
                    ${isEditMode ? 'animate-wiggle' : ''}
                  `}
                >
                  {/* Quick Delete X (Edit Mode) */}
                  {isEditMode && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleQuickDelete(workflow)
                      }}
                      className="absolute -top-2 -left-2 w-6 h-6 bg-red-600 hover:bg-red-700 text-white rounded-full flex items-center justify-center shadow-lg z-10"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}

                  {/* Selection Checkbox (Edit Mode) */}
                  {isEditMode && (
                    <div className="absolute top-3 right-3 z-10">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected
                          ? 'bg-blue-600 border-blue-600'
                          : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600'
                      }`}>
                        {isSelected && <div className="w-2.5 h-2.5 bg-white rounded-sm" />}
                      </div>
                    </div>
                  )}

                  {/* Badges */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${category.color}`}>
                      <span>{category.emoji}</span>
                      <span className="text-gray-700 dark:text-gray-300">{category.label}</span>
                    </div>
                  </div>

                  {/* Template Info */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg group-hover:bg-primary-100 dark:group-hover:bg-primary-900/30 transition-colors">
                      <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:text-primary-600 dark:group-hover:text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                        {workflow.name}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {workflow.description}
                      </p>
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                        {workflow.nodes} steps
                      </div>
                    </div>
                  </div>

                  {/* Hover Actions (NOT in edit mode) */}
                  {!isEditMode && isHovered && (
                    <div className="absolute top-3 right-3 flex items-center gap-2">
                      {/* Star/Favorite */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleToggleFavorite(workflow.id)
                        }}
                        className="p-1.5 bg-white dark:bg-gray-700 rounded-lg shadow-lg hover:scale-110 transition-transform"
                      >
                        <Star
                          className={`w-4 h-4 ${
                            workflow.isFavorited
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-400'
                          }`}
                        />
                      </button>

                      {/* Edit Pencil */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEditWorkflow(workflow)
                        }}
                        className="p-1.5 bg-white dark:bg-gray-700 rounded-lg shadow-lg hover:scale-110 transition-transform"
                      >
                        <Pencil className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                      </button>
                    </div>
                  )}

                  {/* Favorited Star Badge (always visible) */}
                  {workflow.isFavorited && !isHovered && !isEditMode && (
                    <div className="absolute top-3 right-3">
                      <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
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
                      // Would add to categories here
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
