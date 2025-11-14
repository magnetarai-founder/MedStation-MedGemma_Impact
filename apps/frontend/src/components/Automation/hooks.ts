import { useState, useMemo } from 'react'
import { WorkflowTemplate, SortOption } from './types'
import { TemplateCategory } from './shared/categories'
import { WORKFLOW_METADATA } from './shared/templates'
import { WORKFLOW_ICONS } from './shared/icons'

export function useAutomationTemplates() {
  const initialWorkflows: WorkflowTemplate[] = WORKFLOW_METADATA.map((meta, index) => ({
    ...meta,
    isFavorited: ['clinic-intake', 'worship-planning', 'visitor-followup', 'donation-tracker'].includes(meta.id),
    order: index + 1,
    deletedAt: null
  }))

  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>(initialWorkflows)
  const [deletedWorkflows, setDeletedWorkflows] = useState<WorkflowTemplate[]>([])

  const toggleFavorite = (id: string) => {
    setWorkflows(prev =>
      prev.map(wf =>
        wf.id === id ? { ...wf, isFavorited: !wf.isFavorited } : wf
      )
    )
  }

  const deleteWorkflow = (id: string) => {
    const workflow = workflows.find(wf => wf.id === id)
    if (!workflow) return

    const deletedWorkflow = { ...workflow, deletedAt: new Date().toISOString() }
    setDeletedWorkflows(prev => [...prev, deletedWorkflow])
    setWorkflows(prev => prev.filter(wf => wf.id !== id))
  }

  const restoreWorkflow = (id: string) => {
    const workflow = deletedWorkflows.find(wf => wf.id === id)
    if (!workflow) return

    setWorkflows(prev => [...prev, { ...workflow, deletedAt: null }])
    setDeletedWorkflows(prev => prev.filter(wf => wf.id !== id))
  }

  const updateWorkflow = (id: string, updates: Partial<WorkflowTemplate>) => {
    setWorkflows(prev =>
      prev.map(wf => (wf.id === id ? { ...wf, ...updates } : wf))
    )
  }

  const bulkDelete = (ids: string[]) => {
    const now = new Date().toISOString()
    const toDelete = workflows.filter(wf => ids.includes(wf.id))
    const deletedWithTimestamp = toDelete.map(wf => ({ ...wf, deletedAt: now }))

    setDeletedWorkflows(prev => [...prev, ...deletedWithTimestamp])
    setWorkflows(prev => prev.filter(wf => !ids.includes(wf.id)))
  }

  const emptyTrash = () => {
    setDeletedWorkflows([])
  }

  const reorderWorkflows = (newWorkflows: WorkflowTemplate[]) => {
    setWorkflows(newWorkflows)
  }

  return {
    workflows,
    deletedWorkflows,
    toggleFavorite,
    deleteWorkflow,
    restoreWorkflow,
    updateWorkflow,
    bulkDelete,
    emptyTrash,
    reorderWorkflows
  }
}

export function useAutomationFilters() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all')
  const [sortBy, setSortBy] = useState<SortOption>('recent')
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)

  const filterWorkflows = (workflows: WorkflowTemplate[]) => {
    let filtered = [...workflows]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(wf =>
        wf.name.toLowerCase().includes(query) ||
        wf.description.toLowerCase().includes(query)
      )
    }

    // Apply category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(wf => wf.category === selectedCategory)
    }

    // Apply favorites filter
    if (showFavoritesOnly) {
      filtered = filtered.filter(wf => wf.isFavorited)
    }

    // Apply sorting
    switch (sortBy) {
      case 'name':
        filtered.sort((a, b) => a.name.localeCompare(b.name))
        break
      case 'nodes':
        filtered.sort((a, b) => b.nodes - a.nodes)
        break
      case 'favorites':
        filtered.sort((a, b) => {
          if (a.isFavorited && !b.isFavorited) return -1
          if (!a.isFavorited && b.isFavorited) return 1
          return (a.order || 999) - (b.order || 999)
        })
        break
      case 'recent':
      default:
        filtered.sort((a, b) => {
          if (a.isFavorited && !b.isFavorited) return -1
          if (!a.isFavorited && b.isFavorited) return 1
          return (a.order || 999) - (b.order || 999)
        })
        break
    }

    return filtered
  }

  return {
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    sortBy,
    setSortBy,
    showFavoritesOnly,
    setShowFavoritesOnly,
    filterWorkflows
  }
}
