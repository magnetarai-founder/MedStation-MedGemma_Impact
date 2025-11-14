import { Node, Edge } from 'reactflow'

export interface WorkflowTemplateMetadata {
  id: string
  name: string
  description: string
  category: 'clinic' | 'ministry' | 'admin' | 'education' | 'travel'
  iconName: string
  nodes: number
}

export interface WorkflowTemplateDefinition {
  id: string
  name: string
  nodes: Node[]
  edges: Edge[]
}

// Node styles for ReactFlow
const nodeStyles = {
  trigger: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    border: '2px solid #059669',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '200px',
  },
  action: {
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    color: 'white',
    border: '2px solid #2563eb',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '200px',
  },
  ai: {
    background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    color: 'white',
    border: '2px solid #7c3aed',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '200px',
  },
  output: {
    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    color: 'white',
    border: '2px solid #d97706',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '200px',
  },
  condition: {
    background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
    color: 'white',
    border: '2px solid #db2777',
    borderRadius: '12px',
    padding: '16px',
    minWidth: '200px',
  },
}

// Full workflow definitions with nodes and edges
export const WORKFLOW_DEFINITIONS: Record<string, WorkflowTemplateDefinition> = {
  'clinic-intake': {
    id: 'clinic-intake',
    name: 'Clinic Intake Form',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📁 File Upload</div><div className="text-xs opacity-90">Patient uploads intake form</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">📝 Extract Data</div><div className="text-xs opacity-90">Read form fields and text</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">🤖 AI Summary</div><div className="text-xs opacity-90">Generate patient summary</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">💾 Save Document</div><div className="text-xs opacity-90">Create patient record</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'worship-planning': {
    id: 'worship-planning',
    name: 'Worship Service Planner',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📅 Schedule Trigger</div><div className="text-xs opacity-90">Weekly on Monday</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🎵 Song Selection</div><div className="text-xs opacity-90">Pull worship songs from library</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📖 Scripture Reading</div><div className="text-xs opacity-90">Select relevant passages</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">🤖 AI Bulletin</div><div className="text-xs opacity-90">Generate service bulletin</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 250, y: 570 },
        data: { label: <div><div className="font-semibold mb-1">📧 Email Team</div><div className="text-xs opacity-90">Send to worship team</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'visitor-followup': {
    id: 'visitor-followup',
    name: 'Visitor Follow-up',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">👤 New Visitor</div><div className="text-xs opacity-90">Visitor card submitted</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🤖 Personalize Email</div><div className="text-xs opacity-90">AI-generated welcome message</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Send Welcome</div><div className="text-xs opacity-90">Email visitor immediately</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">⏰ Schedule Follow-up</div><div className="text-xs opacity-90">Call in 3 days</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'small-group-coordinator': {
    id: 'small-group-coordinator',
    name: 'Small Group Coordinator',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 150, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📝 Sign-up Form</div><div className="text-xs opacity-90">Member submits interest</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 150, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">⚖️ Balance Groups</div><div className="text-xs opacity-90">Assign to optimal group</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 150, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Send Info</div><div className="text-xs opacity-90">Email group details</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 400, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">👥 Notify Leader</div><div className="text-xs opacity-90">Alert group leader</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 275, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">💾 Update Database</div><div className="text-xs opacity-90">Save group assignment</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e2-4', source: '2', target: '4', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e3-5', source: '3', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'prayer-request-router': {
    id: 'prayer-request-router',
    name: 'Prayer Request Router',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">🙏 Prayer Request</div><div className="text-xs opacity-90">Form submission</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🤖 Categorize</div><div className="text-xs opacity-90">AI assigns care category</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Route to Team</div><div className="text-xs opacity-90">Send to appropriate care team</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">⏰ Set Reminder</div><div className="text-xs opacity-90">Follow-up in 1 week</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'event-manager': {
    id: 'event-manager',
    name: 'Event Manager',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📅 New Event</div><div className="text-xs opacity-90">Event created in calendar</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">📱 Post to Social</div><div className="text-xs opacity-90">Auto-post to platforms</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Email Congregation</div><div className="text-xs opacity-90">Send announcement</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">📝 RSVP Tracker</div><div className="text-xs opacity-90">Create signup form</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 250, y: 570 },
        data: { label: <div><div className="font-semibold mb-1">⏰ Reminder</div><div className="text-xs opacity-90">Send day-before reminder</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '6',
        type: 'default',
        position: { x: 250, y: 700 },
        data: { label: <div><div className="font-semibold mb-1">📊 Save Results</div><div className="text-xs opacity-90">Track attendance data</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e5-6', source: '5', target: '6', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'donation-tracker': {
    id: 'donation-tracker',
    name: 'Donation Manager',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 150, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">💰 Donation Received</div><div className="text-xs opacity-90">Payment notification</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 150, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🤖 Generate Letter</div><div className="text-xs opacity-90">AI thank-you letter</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 150, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Send Thanks</div><div className="text-xs opacity-90">Email donor</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 400, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">💾 Update Records</div><div className="text-xs opacity-90">Log donation</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 400, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📄 Tax Receipt</div><div className="text-xs opacity-90">Generate receipt</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e1-4', source: '1', target: '4', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'volunteer-scheduler': {
    id: 'volunteer-scheduler',
    name: 'Volunteer Scheduler',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📅 Schedule Created</div><div className="text-xs opacity-90">Monthly schedule ready</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">👥 Assign Volunteers</div><div className="text-xs opacity-90">Match volunteers to slots</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Send Assignments</div><div className="text-xs opacity-90">Email each volunteer</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">⏰ Reminder</div><div className="text-xs opacity-90">Send day-before reminder</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'curriculum-builder': {
    id: 'curriculum-builder',
    name: 'Curriculum Builder',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">📚 Topic Selected</div><div className="text-xs opacity-90">Choose curriculum topic</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🤖 Generate Lessons</div><div className="text-xs opacity-90">AI creates lesson plans</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📊 Track Progress</div><div className="text-xs opacity-90">Monitor student completion</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">💾 Save Curriculum</div><div className="text-xs opacity-90">Store in library</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'sunday-school-coordinator': {
    id: 'sunday-school-coordinator',
    name: 'Sunday School Coordinator',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 250, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">✅ Attendance Taken</div><div className="text-xs opacity-90">Teacher logs attendance</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 250, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🤖 Generate Update</div><div className="text-xs opacity-90">AI creates parent update</div></div> },
        style: nodeStyles.ai,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 250, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📧 Email Parents</div><div className="text-xs opacity-90">Send weekly summary</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 250, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">📊 Track Progress</div><div className="text-xs opacity-90">Update student records</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 250, y: 570 },
        data: { label: <div><div className="font-semibold mb-1">💾 Save Data</div><div className="text-xs opacity-90">Store in database</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#8b5cf6', strokeWidth: 2 } },
      { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
  'trip-planner': {
    id: 'trip-planner',
    name: 'Mission Trip Planner',
    nodes: [
      {
        id: '1',
        type: 'default',
        position: { x: 150, y: 50 },
        data: { label: <div><div className="font-semibold mb-1">✈️ Trip Created</div><div className="text-xs opacity-90">New mission trip</div></div> },
        style: nodeStyles.trigger,
      },
      {
        id: '2',
        type: 'default',
        position: { x: 150, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">🗓️ Build Itinerary</div><div className="text-xs opacity-90">Plan daily schedule</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '3',
        type: 'default',
        position: { x: 150, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">🎫 Book Travel</div><div className="text-xs opacity-90">Coordinate flights/transport</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '4',
        type: 'default',
        position: { x: 400, y: 180 },
        data: { label: <div><div className="font-semibold mb-1">👥 Team Communication</div><div className="text-xs opacity-90">Send team updates</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '5',
        type: 'default',
        position: { x: 400, y: 310 },
        data: { label: <div><div className="font-semibold mb-1">📝 Task Assignments</div><div className="text-xs opacity-90">Assign team roles</div></div> },
        style: nodeStyles.action,
      },
      {
        id: '6',
        type: 'default',
        position: { x: 275, y: 440 },
        data: { label: <div><div className="font-semibold mb-1">💾 Save Trip</div><div className="text-xs opacity-90">Store logistics data</div></div> },
        style: nodeStyles.output,
      },
    ] as Node[],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e1-4', source: '1', target: '4', animated: true, style: { stroke: '#10b981', strokeWidth: 2 } },
      { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e3-6', source: '3', target: '6', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
      { id: 'e5-6', source: '5', target: '6', animated: true, style: { stroke: '#3b82f6', strokeWidth: 2 } },
    ] as Edge[]
  },
}

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
