/**
 * Workflow Templates List (Phase D)
 * Browse and instantiate workflow templates
 */

import { useState, useEffect, useMemo } from 'react'
import { Copy, Wand2, Zap, Users, Layers, AlertCircle, Loader2, Info, CheckCircle, X, Filter, Star } from 'lucide-react'
import { useWorkflowTemplates } from '@/hooks/useWorkflowQueue'
import type { Workflow, StageType, WorkflowVisibility } from '@/types/workflow'
import { InstantiateTemplateModal } from './InstantiateTemplateModal'
import VisibilityBadge from '../Automation/components/VisibilityBadge'
import { useUserStore } from '@/stores/userStore'

interface TemplatesListProps {
  automationType?: 'local' | 'team'
  onTemplateInstantiated?: (workflow: Workflow) => void
}

// T3-2: Scope filter type for templates
type ScopeFilter = 'all' | 'personal' | 'team' | 'global'

// AGENT-PHASE-2: System template names (seeded global templates)
const SYSTEM_TEMPLATE_NAMES = [
  'Standard Code Review',
  'Bug Fix + Test',
  'Release Notes & Docs'
]

// AGENT-PHASE-2: Check if a template is a system template
const isSystemTemplate = (template: Workflow): boolean => {
  return (
    template.is_template &&
    template.visibility === 'global' &&
    SYSTEM_TEMPLATE_NAMES.includes(template.name)
  )
}

export function TemplatesList({ automationType, onTemplateInstantiated }: TemplatesListProps) {
  const { data: templates = [], isLoading, error, refetch } = useWorkflowTemplates()
  const [selectedTemplate, setSelectedTemplate] = useState<Workflow | null>(null)
  const [showFirstRunHint, setShowFirstRunHint] = useState(() => {
    return !localStorage.getItem('elohim_workflow_templates_hint_dismissed')
  })
  const [successMessage, setSuccessMessage] = useState<{ workflowName: string } | null>(null)
  const user = useUserStore((state) => state.user)

  // T3-2: Scope filter state
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all')

  // Filter templates by automation type and visibility scope, then separate system templates
  const { systemTemplates, otherTemplates } = useMemo(() => {
    let filtered = automationType
      ? templates.filter(t => t.workflow_type === automationType)
      : templates

    // T3-2: Apply scope filter
    if (scopeFilter !== 'all') {
      filtered = filtered.filter(template => {
        const visibility = template.visibility || 'personal' // Default to personal for backward compatibility

        if (scopeFilter === 'personal') {
          return visibility === 'personal' && template.owner_user_id === user?.userId
        } else if (scopeFilter === 'team') {
          return visibility === 'team'
        } else if (scopeFilter === 'global') {
          return visibility === 'global'
        }
        return true
      })
    }

    // AGENT-PHASE-2: Separate system templates
    const system = filtered.filter(isSystemTemplate)
    const others = filtered.filter(t => !isSystemTemplate(t))

    return {
      systemTemplates: system,
      otherTemplates: others
    }
  }, [templates, automationType, scopeFilter, user?.userId])

  const filteredTemplates = useMemo(() => {
    return [...systemTemplates, ...otherTemplates]
  }, [systemTemplates, otherTemplates])

  const dismissFirstRunHint = () => {
    localStorage.setItem('elohim_workflow_templates_hint_dismissed', 'true')
    setShowFirstRunHint(false)
  }

  const handleInstantiateClick = (template: Workflow) => {
    setSelectedTemplate(template)
  }

  const handleInstantiateSuccess = (workflow: Workflow) => {
    setSelectedTemplate(null)
    setSuccessMessage({ workflowName: workflow.name })
    onTemplateInstantiated?.(workflow)
  }

  // Auto-dismiss success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null)
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [successMessage])

  const getStageTypeIcon = (type: StageType) => {
    switch (type) {
      case 'agent_assist':
      case 'code_review':
      case 'test_enrichment':
      case 'doc_update':
        return <Wand2 className="w-3 h-3" />
      case 'automation':
        return <Zap className="w-3 h-3" />
      case 'human':
        return <Users className="w-3 h-3" />
      default:
        return <Layers className="w-3 h-3" />
    }
  }

  const getStageTypeBadgeColor = (type: StageType) => {
    switch (type) {
      case 'agent_assist':
      case 'code_review':
      case 'test_enrichment':
      case 'doc_update':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300'
      case 'automation':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
      case 'human':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
  }

  const getTypeColor = (workflow_type?: string) => {
    return workflow_type === 'local' ? 'blue' : 'purple'
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary-600 dark:text-primary-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading templates...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Failed to load templates
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Empty state
  if (filteredTemplates.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <Layers className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            No templates yet
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {automationType
              ? `No ${automationType} workflow templates available.`
              : 'No workflow templates available. Create a workflow and mark it as a template to get started.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="h-full w-full p-6 overflow-y-auto">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Workflow Templates
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Templates are reusable workflow blueprints. Instantiating a template creates a new workflow you can edit freely.
            </p>

            {/* T3-2: Scope Filter */}
            {templates.length > 0 && (
              <div className="flex items-center gap-3 mb-4">
                <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                <label htmlFor="template-scope-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Scope:
                </label>
                <select
                  id="template-scope-filter"
                  value={scopeFilter}
                  onChange={(e) => setScopeFilter(e.target.value as ScopeFilter)}
                  className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  aria-label="Filter templates by scope"
                >
                  <option value="all">All Templates</option>
                  <option value="personal">Personal Templates</option>
                  <option value="team">Team Templates</option>
                  <option value="global">Global Templates</option>
                </select>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  ({filteredTemplates.length} {filteredTemplates.length === 1 ? 'template' : 'templates'})
                </span>
              </div>
            )}

            {/* Success Message */}
            {successMessage && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-green-900 dark:text-green-300 mb-1">
                        Workflow created successfully!
                      </h4>
                      <p className="text-sm text-green-800 dark:text-green-200/80">
                        <strong>{successMessage.workflowName}</strong> is now available. You can customize it in the Design view.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setSuccessMessage(null)}
                    className="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* First-Run Hint */}
            {showFirstRunHint && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-1 flex items-center gap-2">
                      <Info className="w-4 h-4" />
                      Start quickly with workflow templates
                    </h4>
                    <p className="text-sm text-blue-800 dark:text-blue-200/80">
                      Use templates as starting points instead of building workflows from scratch.
                    </p>
                  </div>
                  <button
                    onClick={dismissFirstRunHint}
                    className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium"
                  >
                    Got it
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Templates Grid */}
          <div className="space-y-8">
            {/* AGENT-PHASE-2: Recommended Templates Section */}
            {systemTemplates.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Star className="w-5 h-5 text-yellow-500" />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Recommended Templates
                  </h3>
                  <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 rounded">
                    AI-Assisted
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {systemTemplates.map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      isRecommended={true}
                      onInstantiateClick={handleInstantiateClick}
                      getTypeColor={getTypeColor}
                      getStageTypeIcon={getStageTypeIcon}
                      getStageTypeBadgeColor={getStageTypeBadgeColor}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Other Templates Section */}
            {otherTemplates.length > 0 && (
              <div>
                {systemTemplates.length > 0 && (
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Other Templates
                  </h3>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {otherTemplates.map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      isRecommended={false}
                      onInstantiateClick={handleInstantiateClick}
                      getTypeColor={getTypeColor}
                      getStageTypeIcon={getStageTypeIcon}
                      getStageTypeBadgeColor={getStageTypeBadgeColor}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Instantiate Modal */}
      {selectedTemplate && (
        <InstantiateTemplateModal
          template={selectedTemplate}
          isOpen={!!selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          onSuccess={handleInstantiateSuccess}
        />
      )}
    </>
  )
}

// AGENT-PHASE-2: Template Card Component (extracted for reuse)
interface TemplateCardProps {
  template: Workflow
  isRecommended: boolean
  onInstantiateClick: (template: Workflow) => void
  getTypeColor: (workflow_type?: string) => string
  getStageTypeIcon: (type: StageType) => JSX.Element
  getStageTypeBadgeColor: (type: StageType) => string
}

function TemplateCard({
  template,
  isRecommended,
  onInstantiateClick,
  getTypeColor,
  getStageTypeIcon,
  getStageTypeBadgeColor
}: TemplateCardProps) {
  const typeColor = getTypeColor(template.workflow_type)
  const agentAssistStages = template.stages?.filter(s =>
    s.stage_type === 'agent_assist' ||
    s.stage_type === 'code_review' ||
    s.stage_type === 'test_enrichment' ||
    s.stage_type === 'doc_update'
  ) || []

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all">
      {/* AGENT-PHASE-2: Recommended Badge */}
      {isRecommended && (
        <div className="flex items-center gap-1 mb-2">
          <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
          <span className="text-xs font-medium text-yellow-600 dark:text-yellow-400">
            Recommended
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1">
          {template.icon && (
            <span className="text-2xl">{template.icon}</span>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
              {template.name}
            </h3>
            {template.category && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {template.category}
              </p>
            )}
          </div>
        </div>

        {/* Type Badge */}
        <div className={`p-1.5 bg-${typeColor}-100 dark:bg-${typeColor}-900/30 rounded`}>
          {template.workflow_type === 'local' ? (
            <Zap className={`w-3 h-3 text-${typeColor}-600 dark:text-${typeColor}-400`} />
          ) : (
            <Users className={`w-3 h-3 text-${typeColor}-600 dark:text-${typeColor}-400`} />
          )}
        </div>
      </div>

      {/* Description */}
      {template.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
          {template.description}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 mb-3 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <Layers className="w-3 h-3" />
          <span>{template.stages?.length || 0} stages</span>
        </div>

        {agentAssistStages.length > 0 && (
          <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400">
            <Wand2 className="w-3 h-3" />
            <span>{agentAssistStages.length} AI</span>
          </div>
        )}
      </div>

      {/* Key Stages Preview */}
      {template.stages && template.stages.length > 0 && (
        <div className="mb-3 space-y-1">
          {template.stages.slice(0, 3).map((stage, idx) => (
            <div
              key={stage.id}
              className="flex items-center gap-2 text-xs"
            >
              <span className="text-gray-400">#{idx + 1}</span>
              <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${getStageTypeBadgeColor(stage.stage_type)}`}>
                {getStageTypeIcon(stage.stage_type)}
                <span className="truncate">{stage.name}</span>
              </div>
            </div>
          ))}
          {template.stages.length > 3 && (
            <p className="text-xs text-gray-400 pl-5">
              +{template.stages.length - 3} more...
            </p>
          )}
        </div>
      )}

      {/* Triggers Info */}
      {template.triggers && template.triggers.length > 0 && (
        <div className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">Triggers: </span>
          {template.triggers.map(t => t.trigger_type).join(', ')}
        </div>
      )}

      {/* T3-2: Visibility Badge & Explanation */}
      <div className="mb-3 space-y-1">
        <VisibilityBadge visibility={template.visibility} showIcon={true} showTooltip={false} />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {template.visibility === 'personal' && 'Only you can see this template.'}
          {template.visibility === 'team' && 'Shared with your team.'}
          {template.visibility === 'global' && 'System template available to all users.'}
          {!template.visibility && 'Only you can see this template.'}
        </p>
      </div>

      {/* Instantiate Button */}
      <button
        onClick={() => onInstantiateClick(template)}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
      >
        <Copy className="w-4 h-4" />
        Instantiate
      </button>
    </div>
  )
}
