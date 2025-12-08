/**
 * Search API Client - Sprint 6 Theme B
 *
 * Client for session search endpoints
 */

import { authFetch } from './api'

export interface SearchResult {
  session_id: string
  title: string
  snippet: string
  ts: string
  model_name: string
  score: number
  match_count: number
  user_id?: string
  team_id?: string
  created_at?: string
}

export interface SearchResponse {
  query: string
  total_results: number
  results: SearchResult[]
}

export interface SearchFilters {
  teamId?: string
  model?: string
  fromDate?: string
  toDate?: string
  minTokens?: number
  maxTokens?: number
  limit?: number
}

/**
 * Search sessions by message content
 */
export async function searchSessions(
  query: string,
  filters?: SearchFilters
): Promise<SearchResponse> {
  if (!query || query.trim().length === 0) {
    return {
      query: '',
      total_results: 0,
      results: []
    }
  }

  const params = new URLSearchParams({ q: query })

  if (filters?.teamId) params.append('team_id', filters.teamId)
  if (filters?.model) params.append('model', filters.model)
  if (filters?.fromDate) params.append('from', filters.fromDate)
  if (filters?.toDate) params.append('to', filters.toDate)
  if (filters?.minTokens) params.append('min_tokens', filters.minTokens.toString())
  if (filters?.maxTokens) params.append('max_tokens', filters.maxTokens.toString())
  if (filters?.limit) params.append('limit', filters.limit.toString())

  const response = await authFetch(`/api/v1/search/sessions?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Search failed' }))
    throw new Error(error.detail || 'Search failed')
  }

  return response.json()
}

/**
 * Save recent search to local storage
 */
export function saveRecentSearch(query: string) {
  try {
    const recent = getRecentSearches()
    const updated = [query, ...recent.filter(q => q !== query)].slice(0, 10)
    localStorage.setItem('recent_searches', JSON.stringify(updated))
  } catch (error) {
    console.warn('Failed to save recent search:', error)
  }
}

/**
 * Get recent searches from local storage
 */
export function getRecentSearches(): string[] {
  try {
    const stored = localStorage.getItem('recent_searches')
    return stored ? JSON.parse(stored) : []
  } catch (error) {
    console.warn('Failed to load recent searches:', error)
    return []
  }
}

/**
 * Clear recent searches
 */
export function clearRecentSearches() {
  try {
    localStorage.removeItem('recent_searches')
  } catch (error) {
    console.warn('Failed to clear recent searches:', error)
  }
}

/**
 * Format date for API filter
 */
export function formatDateForApi(date: Date): string {
  return date.toISOString()
}

/**
 * Parse HTML snippet (contains <mark> tags for highlighting)
 */
export function parseSnippet(snippet: string): { text: string; html: string } {
  return {
    text: snippet.replace(/<\/?mark>/g, ''),
    html: snippet
  }
}
