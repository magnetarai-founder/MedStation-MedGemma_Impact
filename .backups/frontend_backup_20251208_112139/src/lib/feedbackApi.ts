/**
 * Feedback API Client - Sprint 6 Theme C
 *
 * Client for submitting and retrieving message feedback
 */

import { authFetch } from './api'

export interface MessageFeedback {
  message_id: string
  score: 1 | -1
  timestamp?: string
}

/**
 * Submit feedback for a message
 */
export async function submitMessageFeedback(
  messageId: string,
  score: 1 | -1
): Promise<void> {
  const response = await authFetch(`/api/v1/feedback/messages/${messageId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ score })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to submit feedback' }))
    throw new Error(error.detail || 'Failed to submit feedback')
  }

  return response.json()
}

/**
 * Get feedback for a message
 */
export async function getMessageFeedback(
  messageId: string
): Promise<MessageFeedback | null> {
  const response = await authFetch(`/api/v1/feedback/messages/${messageId}`)

  if (!response.ok) {
    return null
  }

  const data = await response.json()
  return data.score ? data : null
}
