import { WorkflowTemplateMetadata } from './templates'
import { TemplateCategory } from './shared/categories'

export type ViewMode = 'library' | 'builder' | 'queue' | 'tracker' | 'designer'
export type SortOption = 'recent' | 'name' | 'nodes' | 'favorites'
export type ViewLayout = 'grid' | 'list'

export interface WorkflowTemplate extends WorkflowTemplateMetadata {
  isFavorited?: boolean
  order?: number
  deletedAt?: string | null
}

export interface AutomationState {
  workflows: WorkflowTemplate[]
  deletedWorkflows: WorkflowTemplate[]
  selectedForBulk: Set<string>
  isEditMode: boolean
}
