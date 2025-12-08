/**
 * Context Manager Integration Examples
 *
 * This file demonstrates how to integrate the ContextManager
 * with ElohimOS's AI chat system for improved conversation quality.
 */

import { contextManager, type ConversationContext, type Message } from './contextManager'

/**
 * Example 1: Basic context building for AI chat
 */
export function buildChatContext(
  userId: string,
  conversationId: string,
  messages: Message[],
  userPreferences?: any
): string {
  const context: ConversationContext = {
    userId,
    conversationId,
    messageHistory: messages,
    userPreferences: userPreferences
      ? {
          response_style: userPreferences.responseStyle || 'concise',
          language: userPreferences.language || 'en',
          custom_instructions: userPreferences.customInstructions,
        }
      : undefined,
    sessionMetadata: {
      session_id: conversationId,
      started_at: messages[0]?.timestamp || new Date().toISOString(),
      total_messages: messages.length,
    },
  }

  return contextManager.buildContext(context)
}

/**
 * Example 2: Context building with vault documents
 */
export function buildChatContextWithDocuments(
  userId: string,
  conversationId: string,
  messages: Message[],
  vaultDocuments: any[],
  userPreferences?: any
): string {
  const context: ConversationContext = {
    userId,
    conversationId,
    messageHistory: messages,
    relevantDocuments: vaultDocuments.map((doc) => ({
      id: doc.id,
      title: doc.title,
      content: doc.content || doc.encrypted_content || '',
      created_at: doc.created_at,
      relevance_score: doc.relevance_score,
    })),
    userPreferences: userPreferences
      ? {
          response_style: userPreferences.responseStyle || 'concise',
          language: userPreferences.language || 'en',
          custom_instructions: userPreferences.customInstructions,
        }
      : undefined,
    sessionMetadata: {
      session_id: conversationId,
      started_at: messages[0]?.timestamp || new Date().toISOString(),
      total_messages: messages.length,
      current_topic: extractTopic(messages),
    },
  }

  return contextManager.buildContext(context)
}

/**
 * Example 3: Integration with backend chat service
 */
export async function sendMessageWithContext(
  conversationId: string,
  userMessage: string,
  messages: Message[],
  options?: {
    userId?: string
    vaultDocuments?: any[]
    userPreferences?: any
  }
) {
  const userId = options?.userId || 'default_user'

  // Build optimized context
  const contextString = options?.vaultDocuments
    ? buildChatContextWithDocuments(
        userId,
        conversationId,
        messages,
        options.vaultDocuments,
        options.userPreferences
      )
    : buildChatContext(userId, conversationId, messages, options.userPreferences)

  // Get context stats for monitoring
  const stats = contextManager.getContextStats(contextString)
  console.log(`Context stats: ${stats.estimatedTokens} tokens (${stats.percentOfLimit.toFixed(1)}% of limit)`)

  // Send to backend with context
  const response = await fetch(`/api/v1/chat/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content: userMessage,
      context: contextString, // Include built context
      model: options?.userPreferences?.model || 'qwen2.5-coder:7b-instruct',
    }),
  })

  return response.json()
}

/**
 * Example 4: Monitoring context token usage
 */
export function getContextMetrics(messages: Message[], vaultDocuments?: any[]): {
  estimatedTokens: number
  percentOfLimit: number
  characterCount: number
  recommendation: string
} {
  const context = buildChatContext('user', 'session', messages)
  const stats = contextManager.getContextStats(context)

  let recommendation = 'Context size is optimal'
  if (stats.percentOfLimit > 90) {
    recommendation = 'Warning: Context near token limit. Consider summarizing older messages.'
  } else if (stats.percentOfLimit > 75) {
    recommendation = 'Context size is high. May want to prune older messages soon.'
  }

  return {
    estimatedTokens: stats.estimatedTokens,
    percentOfLimit: stats.percentOfLimit,
    characterCount: stats.characterCount,
    recommendation,
  }
}

/**
 * Example 5: Smart document selection based on conversation
 */
export function selectRelevantDocuments(
  vaultDocuments: any[],
  messages: Message[],
  maxDocuments: number = 3
): any[] {
  // Extract recent conversation content
  const recentContent = messages
    .slice(-5)
    .map((m) => m.content)
    .join(' ')
    .toLowerCase()

  // Simple keyword-based relevance scoring
  const scoredDocs = vaultDocuments.map((doc) => {
    const docText = (doc.title + ' ' + (doc.content || '')).toLowerCase()
    const keywords = extractKeywords(recentContent)

    let score = 0
    for (const keyword of keywords) {
      const occurrences = (docText.match(new RegExp(keyword, 'gi')) || []).length
      score += occurrences
    }

    return { ...doc, relevance_score: score / keywords.length }
  })

  // Return top N most relevant documents
  return scoredDocs.sort((a, b) => b.relevance_score - a.relevance_score).slice(0, maxDocuments)
}

/**
 * Helper: Extract topic from conversation
 */
function extractTopic(messages: Message[]): string | undefined {
  if (messages.length === 0) return undefined

  // Use first user message as topic indicator
  const firstUserMessage = messages.find((m) => m.role === 'user')
  if (!firstUserMessage) return undefined

  // Extract first sentence or first 50 chars
  const content = firstUserMessage.content
  const firstSentence = content.split(/[.!?]/)[0]
  return firstSentence.length > 50 ? firstSentence.slice(0, 50) + '...' : firstSentence
}

/**
 * Helper: Extract keywords from text
 */
function extractKeywords(text: string): string[] {
  const stopWords = new Set([
    'the',
    'is',
    'at',
    'which',
    'on',
    'a',
    'an',
    'and',
    'or',
    'but',
    'in',
    'with',
    'to',
    'for',
    'of',
    'as',
    'by',
  ])

  const words = text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter((word) => word.length > 3 && !stopWords.has(word))

  return [...new Set(words)]
}

/**
 * Example 6: Context pruning for long conversations
 */
export function pruneMessagesForContext(
  messages: Message[],
  maxMessages: number = 20
): Message[] {
  // Keep system messages + recent user/assistant messages
  const systemMessages = messages.filter((m) => m.role === 'system')
  const conversationMessages = messages.filter((m) => m.role !== 'system')

  // Take most recent conversation messages
  const recentMessages = conversationMessages.slice(-maxMessages)

  return [...systemMessages, ...recentMessages]
}
