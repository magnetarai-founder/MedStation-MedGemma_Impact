/**
 * Model Recommendations API Client - Sprint 6 Theme C
 *
 * Client for fetching intelligent model recommendations
 */

import { authFetch } from './api'

export type TaskType = 'code' | 'chat' | 'analysis' | 'general'

export interface ModelRecommendation {
  model_name: string
  score: number
  reason: string
  metrics: {
    avg_latency_ms?: number
    p95_latency_ms?: number
    satisfaction?: number
    tokens_per_message?: number
    total_messages: number
  }
}

export interface RecommendationsResponse {
  task: TaskType
  recommendations: ModelRecommendation[]
  count: number
  error?: string
}

/**
 * Get model recommendations for a specific task type
 */
export async function getModelRecommendations(
  task: TaskType = 'general',
  limit: number = 3
): Promise<ModelRecommendation[]> {
  try {
    const response = await authFetch(
      `/api/v1/models/recommendations?task=${task}&limit=${limit}`
    )

    if (!response.ok) {
      console.warn('Failed to fetch model recommendations')
      return []
    }

    const data: RecommendationsResponse = await response.json()
    return data.recommendations || []
  } catch (error) {
    console.warn('Error fetching model recommendations:', error)
    return []
  }
}

/**
 * Detect task type from context (message content, settings, etc.)
 */
export function detectTaskType(context: {
  messageContent?: string
  previousMessages?: string[]
}): TaskType {
  const { messageContent = '', previousMessages = [] } = context

  const allContent = [messageContent, ...previousMessages].join(' ').toLowerCase()

  // Code-related keywords
  const codeKeywords = ['code', 'function', 'debug', 'error', 'implement', 'algorithm', 'class', 'method', 'api', 'bug', 'refactor']
  const codeCount = codeKeywords.filter(kw => allContent.includes(kw)).length

  // Analysis-related keywords
  const analysisKeywords = ['analyze', 'explain', 'compare', 'evaluate', 'assess', 'research', 'investigate', 'review', 'study']
  const analysisCount = analysisKeywords.filter(kw => allContent.includes(kw)).length

  // Choose task type based on keyword matches
  if (codeCount > 2) return 'code'
  if (analysisCount > 2) return 'analysis'
  if (messageContent || previousMessages.length > 0) return 'chat'

  return 'general'
}
