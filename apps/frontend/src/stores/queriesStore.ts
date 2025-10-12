import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type QueryNodeType = 'query' | 'folder'

export interface QueryNode {
  id: string
  name: string
  type: QueryNodeType
  query?: string // Only for query nodes
  queryType?: 'sql' | 'json' // Only for query nodes
  children?: QueryNode[] // Only for folder nodes
  parentId?: string | null
  createdAt: number
  updatedAt: number
}

interface QueriesStore {
  queries: QueryNode[]
  addQuery: (name: string, query: string, queryType: 'sql' | 'json', parentId?: string | null) => void
  addFolder: (name: string, parentId?: string | null) => void
  updateQuery: (id: string, updates: Partial<Omit<QueryNode, 'id' | 'createdAt'>>) => void
  deleteNode: (id: string) => void
  moveNode: (nodeId: string, newParentId: string | null) => void
  findNodeById: (id: string) => QueryNode | null
}

// Get max saved queries from settings or default to 100
const getMaxSavedQueries = () => {
  try {
    const stored = localStorage.getItem('ns.maxSavedQueries')
    return stored ? JSON.parse(stored) : 100
  } catch {
    return 100
  }
}

export const useQueriesStore = create<QueriesStore>()(
  persist(
    (set, get) => ({
      queries: [],

      addQuery: (name, query, queryType, parentId = null) => set((state) => {
        const newQuery: QueryNode = {
          id: `query_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name,
          type: 'query',
          query,
          queryType,
          parentId,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }

        let updatedQueries: QueryNode[]
        if (parentId) {
          // Add to parent folder
          updatedQueries = addToParent(state.queries, parentId, newQuery)
        } else {
          // Add to root
          updatedQueries = [...state.queries, newQuery]
        }

        // Enforce max limit: keep most recently created queries (from settings)
        const maxQueries = getMaxSavedQueries()
        const totalQueries = countQueries(updatedQueries)
        if (totalQueries > maxQueries) {
          updatedQueries = trimOldestQueries(updatedQueries, maxQueries)
        }

        return { queries: updatedQueries }
      }),

      addFolder: (name, parentId = null) => set((state) => {
        const newFolder: QueryNode = {
          id: `folder_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name,
          type: 'folder',
          children: [],
          parentId,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }

        if (parentId) {
          const updatedQueries = addToParent(state.queries, parentId, newFolder)
          return { queries: updatedQueries }
        } else {
          return { queries: [...state.queries, newFolder] }
        }
      }),

      updateQuery: (id, updates) => set((state) => ({
        queries: updateNodeRecursive(state.queries, id, { ...updates, updatedAt: Date.now() })
      })),

      deleteNode: (id) => set((state) => ({
        queries: deleteNodeRecursive(state.queries, id)
      })),

      moveNode: (nodeId, newParentId) => set((state) => {
        // Find the node
        const node = findNodeRecursive(state.queries, nodeId)
        if (!node) return state

        // Remove from current location
        let updatedQueries = deleteNodeRecursive(state.queries, nodeId)

        // Update parent ID
        const movedNode = { ...node, parentId: newParentId, updatedAt: Date.now() }

        // Add to new location
        if (newParentId) {
          updatedQueries = addToParent(updatedQueries, newParentId, movedNode)
        } else {
          updatedQueries = [...updatedQueries, movedNode]
        }

        return { queries: updatedQueries }
      }),

      findNodeById: (id) => {
        return findNodeRecursive(get().queries, id)
      },
    }),
    {
      name: 'ns.savedQueries',
    }
  )
)

// Helper functions
function findNodeRecursive(nodes: QueryNode[], id: string): QueryNode | null {
  for (const node of nodes) {
    if (node.id === id) return node
    if (node.type === 'folder' && node.children) {
      const found = findNodeRecursive(node.children, id)
      if (found) return found
    }
  }
  return null
}

function addToParent(nodes: QueryNode[], parentId: string, newNode: QueryNode): QueryNode[] {
  return nodes.map(node => {
    if (node.id === parentId && node.type === 'folder') {
      return {
        ...node,
        children: [...(node.children || []), newNode],
        updatedAt: Date.now(),
      }
    }
    if (node.type === 'folder' && node.children) {
      return {
        ...node,
        children: addToParent(node.children, parentId, newNode)
      }
    }
    return node
  })
}

function updateNodeRecursive(nodes: QueryNode[], id: string, updates: Partial<QueryNode>): QueryNode[] {
  return nodes.map(node => {
    if (node.id === id) {
      return { ...node, ...updates }
    }
    if (node.type === 'folder' && node.children) {
      return {
        ...node,
        children: updateNodeRecursive(node.children, id, updates)
      }
    }
    return node
  })
}

function deleteNodeRecursive(nodes: QueryNode[], id: string): QueryNode[] {
  return nodes
    .filter(node => node.id !== id)
    .map(node => {
      if (node.type === 'folder' && node.children) {
        return {
          ...node,
          children: deleteNodeRecursive(node.children, id)
        }
      }
      return node
    })
}

function countQueries(nodes: QueryNode[]): number {
  let count = 0
  for (const node of nodes) {
    if (node.type === 'query') {
      count++
    } else if (node.type === 'folder' && node.children) {
      count += countQueries(node.children)
    }
  }
  return count
}

function trimOldestQueries(nodes: QueryNode[], maxQueries: number): QueryNode[] {
  // Collect all queries with their paths
  const allQueries: Array<{ node: QueryNode; path: string[] }> = []

  function collectQueries(nodeList: QueryNode[], path: string[] = []) {
    for (const node of nodeList) {
      if (node.type === 'query') {
        allQueries.push({ node, path })
      } else if (node.type === 'folder' && node.children) {
        collectQueries(node.children, [...path, node.id])
      }
    }
  }

  collectQueries(nodes)

  // Sort by creation date (newest first)
  allQueries.sort((a, b) => b.node.createdAt - a.node.createdAt)

  // Keep only the newest maxQueries
  const queriesToKeep = new Set(
    allQueries.slice(0, maxQueries).map(q => q.node.id)
  )

  // Remove old queries
  function filterOldQueries(nodeList: QueryNode[]): QueryNode[] {
    return nodeList
      .filter(node => node.type === 'folder' || queriesToKeep.has(node.id))
      .map(node => {
        if (node.type === 'folder' && node.children) {
          return {
            ...node,
            children: filterOldQueries(node.children)
          }
        }
        return node
      })
      .filter(node => {
        // Remove empty folders
        if (node.type === 'folder' && node.children?.length === 0) {
          return false
        }
        return true
      })
  }

  return filterOldQueries(nodes)
}
