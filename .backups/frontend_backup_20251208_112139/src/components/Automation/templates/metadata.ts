import { WorkflowTemplateMetadata } from './types'

// Workflow metadata for library display
export const WORKFLOW_METADATA: WorkflowTemplateMetadata[] = [
  {
    id: 'clinic-intake',
    name: 'Clinic Intake Form',
    description: 'Patient information collection and AI-powered summary',
    category: 'clinic',
    iconName: 'FileText',
    nodes: 4
  },
  {
    id: 'worship-planning',
    name: 'Worship Service Planner',
    description: 'Plan songs, scripture, announcements, and auto-generate bulletin',
    category: 'ministry',
    iconName: 'Users',
    nodes: 5
  },
  {
    id: 'visitor-followup',
    name: 'Visitor Follow-up',
    description: 'Personalized welcome emails and scheduled follow-up calls',
    category: 'ministry',
    iconName: 'UserPlus',
    nodes: 4
  },
  {
    id: 'small-group-coordinator',
    name: 'Small Group Coordinator',
    description: 'Manage sign-ups, balance groups, and send group info',
    category: 'ministry',
    iconName: 'Users',
    nodes: 5
  },
  {
    id: 'prayer-request-router',
    name: 'Prayer Request Router',
    description: 'Route prayer requests to care teams with follow-up reminders',
    category: 'ministry',
    iconName: 'Heart',
    nodes: 4
  },
  {
    id: 'event-manager',
    name: 'Event Manager',
    description: 'Auto-post events, email congregation, and track RSVPs',
    category: 'ministry',
    iconName: 'Calendar',
    nodes: 6
  },
  {
    id: 'donation-tracker',
    name: 'Donation Manager',
    description: 'Auto thank-you letters, update records, and generate tax receipts',
    category: 'admin',
    iconName: 'DollarSign',
    nodes: 5
  },
  {
    id: 'volunteer-scheduler',
    name: 'Volunteer Scheduler',
    description: 'Coordinate volunteers and send automated reminders',
    category: 'admin',
    iconName: 'Calendar',
    nodes: 4
  },
  {
    id: 'curriculum-builder',
    name: 'Curriculum Builder',
    description: 'Plan lessons and track student progress',
    category: 'education',
    iconName: 'BookOpen',
    nodes: 4
  },
  {
    id: 'sunday-school-coordinator',
    name: 'Sunday School Coordinator',
    description: 'Manage attendance, send parent updates, and track progress',
    category: 'education',
    iconName: 'BookOpen',
    nodes: 5
  },
  {
    id: 'trip-planner',
    name: 'Mission Trip Planner',
    description: 'Organize travel logistics, itinerary, and team communication',
    category: 'travel',
    iconName: 'Plane',
    nodes: 6
  },
]
