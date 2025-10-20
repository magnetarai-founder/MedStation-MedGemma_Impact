import { useState } from 'react'
import { Plus, FileText, Users, DollarSign, Plane, BookOpen, Heart, Calendar, Mail, UserPlus, ChurchIcon as Church } from 'lucide-react'
import { WorkflowBuilder } from './WorkflowBuilder'
import { ReactFlowProvider } from 'reactflow'

interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: 'clinic' | 'ministry' | 'admin' | 'education' | 'travel'
  icon: React.ComponentType<{ className?: string }>
  nodes: number
  popular?: boolean
}

const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  // Field/Clinic
  {
    id: 'clinic-intake',
    name: 'Clinic Intake Form',
    description: 'Patient information collection and AI-powered summary',
    category: 'clinic',
    icon: FileText,
    nodes: 4,
    popular: true
  },

  // Ministry/Church
  {
    id: 'worship-planning',
    name: 'Worship Service Planner',
    description: 'Plan songs, scripture, announcements, and auto-generate bulletin',
    category: 'ministry',
    icon: Users,
    nodes: 5,
    popular: true
  },
  {
    id: 'visitor-followup',
    name: 'Visitor Follow-up',
    description: 'Personalized welcome emails and scheduled follow-up calls',
    category: 'ministry',
    icon: UserPlus,
    nodes: 4,
    popular: true
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
    popular: true
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

const CATEGORY_INFO = {
  clinic: { label: 'Clinic', emoji: '🏥', color: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' },
  ministry: { label: 'Ministry', emoji: '⛪', color: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800' },
  admin: { label: 'Admin', emoji: '💰', color: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' },
  education: { label: 'Education', emoji: '📚', color: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' },
  travel: { label: 'Travel', emoji: '✈️', color: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' }
}

export function AutomationTab() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [myWorkflows, setMyWorkflows] = useState<any[]>([])

  const handleCreateFromTemplate = (templateId: string) => {
    setSelectedTemplate(templateId)
  }

  const handleBackToTemplates = () => {
    setSelectedTemplate(null)
  }

  // Show workflow builder if template selected
  if (selectedTemplate) {
    return (
      <ReactFlowProvider>
        <WorkflowBuilder templateId={selectedTemplate} onBack={handleBackToTemplates} />
      </ReactFlowProvider>
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
          <button className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg font-medium transition-colors">
            <Plus className="w-4 h-4" />
            New Workflow
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* My Workflows Section */}
        {myWorkflows.length > 0 && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              My Workflows ({myWorkflows.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Will show user's workflows here */}
            </div>
          </div>
        )}

        {/* Templates Section */}
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Templates
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Start with a pre-built workflow and customize it to your needs
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {WORKFLOW_TEMPLATES.map((template) => {
              const category = CATEGORY_INFO[template.category]
              const Icon = template.icon

              return (
                <button
                  key={template.id}
                  onClick={() => handleCreateFromTemplate(template.id)}
                  className="text-left p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-lg hover:border-primary-300 dark:hover:border-primary-600 transition-all group"
                >
                  {/* Badges */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${category.color}`}>
                      <span>{category.emoji}</span>
                      <span className="text-gray-700 dark:text-gray-300">{category.label}</span>
                    </div>
                    {template.popular && (
                      <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300">
                        ⭐ Popular
                      </div>
                    )}
                  </div>

                  {/* Template Info */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg group-hover:bg-primary-100 dark:group-hover:bg-primary-900/30 transition-colors">
                      <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:text-primary-600 dark:group-hover:text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                        {template.name}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                        {template.description}
                      </p>
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
                        {template.nodes} steps
                      </div>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
