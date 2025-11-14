import { useState } from 'react'
import { TemplateCard } from './TemplateCard'
import { EmptyState } from './EmptyState'
import type { WorkflowTemplate, ViewLayout } from '../types'

interface TemplateGalleryProps {
  workflows: WorkflowTemplate[]
  viewLayout: ViewLayout
  isEditMode: boolean
  selectedForBulk: Set<string>
  onSelectWorkflow: (id: string) => void
  onToggleFavorite: (id: string) => void
  onEditWorkflow: (workflow: WorkflowTemplate) => void
  onUseInQueue: (id: string) => void
  onQuickDelete: (workflow: WorkflowTemplate) => void
  onToggleBulkSelect: (id: string) => void
  onReorder: (workflows: WorkflowTemplate[]) => void
  onCreateCustom?: () => void
}

export function TemplateGallery({
  workflows,
  viewLayout,
  isEditMode,
  selectedForBulk,
  onSelectWorkflow,
  onToggleFavorite,
  onEditWorkflow,
  onUseInQueue,
  onQuickDelete,
  onToggleBulkSelect,
  onReorder,
  onCreateCustom
}: TemplateGalleryProps) {
  const [hoveredWorkflow, setHoveredWorkflow] = useState<string | null>(null)
  const [draggedWorkflow, setDraggedWorkflow] = useState<string | null>(null)
  const [dragOverWorkflow, setDragOverWorkflow] = useState<string | null>(null)

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

    onReorder(newWorkflows)
    setDraggedWorkflow(null)
    setDragOverWorkflow(null)
  }

  const handleDragEnd = () => {
    setDraggedWorkflow(null)
    setDragOverWorkflow(null)
  }

  if (workflows.length === 0) {
    return <EmptyState onCreateCustom={onCreateCustom} />
  }

  return (
    <div className={viewLayout === 'grid'
      ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
      : 'space-y-3'
    }>
      {workflows.map((workflow) => (
        <TemplateCard
          key={workflow.id}
          workflow={workflow}
          isEditMode={isEditMode}
          isHovered={hoveredWorkflow === workflow.id}
          isSelected={selectedForBulk.has(workflow.id)}
          isDragging={draggedWorkflow === workflow.id}
          isDragOver={dragOverWorkflow === workflow.id}
          onMouseEnter={() => setHoveredWorkflow(workflow.id)}
          onMouseLeave={() => setHoveredWorkflow(null)}
          onClick={() => {
            if (isEditMode) {
              onToggleBulkSelect(workflow.id)
            } else {
              onSelectWorkflow(workflow.id)
            }
          }}
          onToggleFavorite={(e) => {
            e.stopPropagation()
            onToggleFavorite(workflow.id)
          }}
          onEdit={(e) => {
            e.stopPropagation()
            onEditWorkflow(workflow)
          }}
          onUseInQueue={(e) => {
            e.stopPropagation()
            onUseInQueue(workflow.id)
          }}
          onQuickDelete={(e) => {
            e.stopPropagation()
            onQuickDelete(workflow)
          }}
          onDragStart={(e) => handleDragStart(e, workflow.id)}
          onDragOver={(e) => handleDragOver(e, workflow.id)}
          onDrop={(e) => handleDrop(e, workflow.id)}
          onDragEnd={handleDragEnd}
        />
      ))}
    </div>
  )
}
