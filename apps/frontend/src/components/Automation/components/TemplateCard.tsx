import { Star, Pencil, Briefcase, X } from 'lucide-react'
import { WORKFLOW_ICONS } from '../shared/icons'
import { CATEGORY_INFO } from '../shared/categories'
import type { WorkflowTemplate } from '../types'

interface TemplateCardProps {
  workflow: WorkflowTemplate
  isEditMode: boolean
  isHovered: boolean
  isSelected: boolean
  isDragging: boolean
  isDragOver: boolean
  onMouseEnter: () => void
  onMouseLeave: () => void
  onClick: () => void
  onToggleFavorite: (e: React.MouseEvent) => void
  onEdit: (e: React.MouseEvent) => void
  onUseInQueue: (e: React.MouseEvent) => void
  onQuickDelete: (e: React.MouseEvent) => void
  onDragStart: (e: React.DragEvent) => void
  onDragOver: (e: React.DragEvent) => void
  onDrop: (e: React.DragEvent) => void
  onDragEnd: () => void
}

export function TemplateCard({
  workflow,
  isEditMode,
  isHovered,
  isSelected,
  isDragging,
  isDragOver,
  onMouseEnter,
  onMouseLeave,
  onClick,
  onToggleFavorite,
  onEdit,
  onUseInQueue,
  onQuickDelete,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd
}: TemplateCardProps) {
  const category = CATEGORY_INFO[workflow.category]
  const Icon = WORKFLOW_ICONS[workflow.id]

  return (
    <div
      draggable={!isEditMode}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={onClick}
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
          onClick={onQuickDelete}
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
            onClick={onToggleFavorite}
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
            onClick={onEdit}
            className="p-1.5 bg-white dark:bg-gray-700 rounded-lg shadow-lg hover:scale-110 transition-transform"
          >
            <Pencil className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Use in Queue */}
          <button
            onClick={onUseInQueue}
            className="p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg hover:scale-110 transition-transform"
          >
            <Briefcase className="w-4 h-4" />
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
}
