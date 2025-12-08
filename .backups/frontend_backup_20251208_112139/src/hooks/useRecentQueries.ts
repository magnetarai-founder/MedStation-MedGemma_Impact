import { useState, useEffect } from 'react'

export interface RecentQuery {
  id: number
  name: string
  query: string
  lastUsed: string
}

const STORAGE_KEY = 'neutron-star:recent-queries'
const MAX_RECENT = 5

/**
 * Hook to manage recently executed queries that are saved in library
 */
export function useRecentQueries() {
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([])

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored) as RecentQuery[]
        setRecentQueries(parsed)
      }
    } catch (error) {
      console.error('Failed to load recent queries:', error)
    }
  }, [])

  // Add query to recents
  const addRecent = (query: { id: number; name: string; query: string }) => {
    setRecentQueries(prev => {
      // Remove if already exists
      const filtered = prev.filter(q => q.id !== query.id)

      // Add to front with current timestamp
      const updated = [
        {
          ...query,
          lastUsed: new Date().toISOString()
        },
        ...filtered
      ].slice(0, MAX_RECENT) // Keep only top 5

      // Save to localStorage
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
      } catch (error) {
        console.error('Failed to save recent queries:', error)
      }

      return updated
    })
  }

  // Clear all recents
  const clearRecents = () => {
    setRecentQueries([])
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (error) {
      console.error('Failed to clear recent queries:', error)
    }
  }

  return {
    recentQueries,
    addRecent,
    clearRecents
  }
}
