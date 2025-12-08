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
