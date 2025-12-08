/**
 * Analytics API Client - Sprint 6 Theme A
 *
 * Client helpers for fetching analytics data
 */

import { authFetch } from './api'

export type DateRange = '7d' | '30d' | '90d'
export type ExportFormat = 'json' | 'csv'

export interface ModelUsage {
  model_name: string
  total_tokens: number
  calls: number
}

export interface TrendPoint {
  date: string
  tokens?: number
  sessions?: number
  errors?: number
}

export interface TopUser {
  user_id: string
  calls: number
  tokens: number
}

export interface TopTeam {
  team_id: string
  calls: number
  tokens: number
}

export interface AnalyticsSummary {
  model_usage: ModelUsage[]
  tokens_trend: TrendPoint[]
  sessions_trend: TrendPoint[]
  errors_trend: TrendPoint[]
  top_users: TopUser[]
  top_teams: TopTeam[]
}

export interface UsageResponse {
  range: DateRange
  days: number
  filters: {
    team_id?: string
    user_id?: string
  }
  data: AnalyticsSummary
}

/**
 * Fetch analytics usage summary
 */
export async function fetchAnalyticsUsage(
  range: DateRange = '7d',
  teamId?: string,
  userId?: string
): Promise<UsageResponse> {
  const params = new URLSearchParams({ range })
  if (teamId) params.append('team_id', teamId)
  if (userId) params.append('user_id', userId)

  const response = await authFetch(`/api/v1/analytics/usage?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch analytics' }))
    throw new Error(error.detail || 'Failed to fetch analytics')
  }

  return response.json()
}

/**
 * Export analytics data
 */
export async function exportAnalytics(
  format: ExportFormat = 'json',
  range: DateRange = '30d',
  teamId?: string,
  userId?: string
): Promise<Blob> {
  const params = new URLSearchParams({ format, range })
  if (teamId) params.append('team_id', teamId)
  if (userId) params.append('user_id', userId)

  const response = await authFetch(`/api/v1/analytics/export?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to export analytics' }))
    throw new Error(error.detail || 'Failed to export analytics')
  }

  return response.blob()
}

/**
 * Download exported analytics file
 */
export function downloadExportedFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * Format date range label for display
 */
export function formatDateRangeLabel(range: DateRange): string {
  const labels: Record<DateRange, string> = {
    '7d': 'Last 7 Days',
    '30d': 'Last 30 Days',
    '90d': 'Last 90 Days'
  }
  return labels[range]
}
