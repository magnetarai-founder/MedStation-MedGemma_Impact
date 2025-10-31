/**
 * Context Manager for AI Conversations
 *
 * Builds optimized context for AI queries to improve response quality
 * and conversation continuity while respecting token limits.
 */

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface Document {
  id: string
  title: string
  content: string
  relevance_score?: number
  created_at: string
}

export interface UserPreferences {
  ai_model?: string
  response_style?: 'concise' | 'detailed' | 'technical'
  language?: string
  custom_instructions?: string
}

export interface SessionMetadata {
  session_id: string
  started_at: string
  total_messages: number
  current_topic?: string
}

export interface ConversationContext {
  userId: string
  conversationId: string
  messageHistory: Message[]
  relevantDocuments?: Document[]
  userPreferences?: UserPreferences
  sessionMetadata?: SessionMetadata
}

export class ContextManager {
  private maxContextTokens: number = 8000

  constructor(maxTokens: number = 8000) {
    this.maxContextTokens = maxTokens
  }

  /**
   * Build optimized context for AI queries
   */
  buildContext(conversation: ConversationContext): string {
    const parts: string[] = []

    // 1. User preferences (if available)
    if (conversation.userPreferences) {
      parts.push(this.formatPreferences(conversation.userPreferences))
    }

    // 2. Session metadata (provides conversation context)
    if (conversation.sessionMetadata) {
      parts.push(this.formatSessionMetadata(conversation.sessionMetadata))
    }

    // 3. Relevant documents (semantic context from vault/docs)
    if (conversation.relevantDocuments && conversation.relevantDocuments.length > 0) {
      const topDocs = this.rankRelevantDocuments(
        conversation.relevantDocuments,
        conversation.messageHistory
      )
      parts.push(this.formatDocuments(topDocs.slice(0, 3)))
    }

    // 4. Recent message history (prioritize recent messages)
    const recentMessages = this.selectRecentMessages(conversation.messageHistory)
    parts.push(this.formatMessages(recentMessages))

    // 5. Truncate to token limit
    const fullContext = parts.join('\n\n')
    return this.truncateToTokenLimit(fullContext, this.maxContextTokens)
  }

  /**
   * Format user preferences for context
   */
  private formatPreferences(prefs: UserPreferences): string {
    const lines: string[] = ['# User Preferences']

    if (prefs.response_style) {
      lines.push(`- Response Style: ${prefs.response_style}`)
    }

    if (prefs.language) {
      lines.push(`- Language: ${prefs.language}`)
    }

    if (prefs.custom_instructions) {
      lines.push(`- Custom Instructions: ${prefs.custom_instructions}`)
    }

    return lines.join('\n')
  }

  /**
   * Format session metadata for context
   */
  private formatSessionMetadata(metadata: SessionMetadata): string {
    const lines: string[] = ['# Session Context']

    lines.push(`- Total Messages: ${metadata.total_messages}`)

    if (metadata.current_topic) {
      lines.push(`- Current Topic: ${metadata.current_topic}`)
    }

    const duration = this.getSessionDuration(metadata.started_at)
    if (duration) {
      lines.push(`- Session Duration: ${duration}`)
    }

    return lines.join('\n')
  }

  /**
   * Format messages for context
   */
  private formatMessages(messages: Message[]): string {
    const lines: string[] = ['# Conversation History']

    for (const msg of messages) {
      const roleLabel = msg.role === 'user' ? 'User' : msg.role === 'assistant' ? 'Assistant' : 'System'
      lines.push(`\n**${roleLabel}:** ${msg.content}`)
    }

    return lines.join('\n')
  }

  /**
   * Format documents for context
   */
  private formatDocuments(docs: Document[]): string {
    if (docs.length === 0) return ''

    const lines: string[] = ['# Relevant Documents']

    for (const doc of docs) {
      lines.push(`\n## ${doc.title}`)

      // Truncate long documents
      const contentPreview = doc.content.length > 500
        ? doc.content.slice(0, 500) + '...'
        : doc.content

      lines.push(contentPreview)

      if (doc.relevance_score) {
        lines.push(`\n*Relevance: ${(doc.relevance_score * 100).toFixed(0)}%*`)
      }
    }

    return lines.join('\n')
  }

  /**
   * Select most recent messages, prioritizing recent over old
   */
  private selectRecentMessages(messages: Message[], maxMessages: number = 10): Message[] {
    // Always include system messages
    const systemMessages = messages.filter(m => m.role === 'system')

    // Get recent non-system messages
    const nonSystemMessages = messages.filter(m => m.role !== 'system')
    const recentMessages = nonSystemMessages.slice(-maxMessages)

    return [...systemMessages, ...recentMessages]
  }

  /**
   * Rank documents by relevance to conversation
   */
  private rankRelevantDocuments(docs: Document[], history: Message[]): Document[] {
    // If documents already have relevance scores, use them
    if (docs.some(d => d.relevance_score !== undefined)) {
      return [...docs].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    }

    // Simple keyword-based ranking
    const recentMessages = history.slice(-5).map(m => m.content.toLowerCase()).join(' ')

    const scoredDocs = docs.map(doc => {
      const docText = (doc.title + ' ' + doc.content).toLowerCase()
      const keywords = this.extractKeywords(recentMessages)

      let score = 0
      for (const keyword of keywords) {
        const occurrences = (docText.match(new RegExp(keyword, 'gi')) || []).length
        score += occurrences
      }

      return { ...doc, relevance_score: score }
    })

    return scoredDocs.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
  }

  /**
   * Extract keywords from text for relevance matching
   */
  private extractKeywords(text: string): string[] {
    // Remove common stop words
    const stopWords = new Set([
      'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
      'in', 'with', 'to', 'for', 'of', 'as', 'by', 'this', 'that',
      'it', 'from', 'be', 'are', 'was', 'were', 'been', 'have', 'has', 'had'
    ])

    const words = text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3 && !stopWords.has(word))

    // Return unique keywords
    return [...new Set(words)]
  }

  /**
   * Truncate context to token limit
   */
  private truncateToTokenLimit(text: string, maxTokens: number): string {
    // Rough estimation: 1 token ≈ 4 characters
    const maxChars = maxTokens * 4

    if (text.length <= maxChars) {
      return text
    }

    // Truncate and add marker
    const truncated = text.slice(0, maxChars)

    // Try to cut at a sentence boundary
    const lastPeriod = truncated.lastIndexOf('.')
    const lastNewline = truncated.lastIndexOf('\n')
    const cutPoint = Math.max(lastPeriod, lastNewline)

    if (cutPoint > maxChars * 0.8) {
      // Good cut point found
      return truncated.slice(0, cutPoint + 1) + '\n\n[Context truncated due to length]'
    }

    // No good cut point, just truncate
    return truncated + '...\n\n[Context truncated due to length]'
  }

  /**
   * Get session duration in human-readable format
   */
  private getSessionDuration(startedAt: string): string | null {
    try {
      const start = new Date(startedAt)
      const now = new Date()
      const diffMs = now.getTime() - start.getTime()
      const diffMins = Math.floor(diffMs / 60000)

      if (diffMins < 60) {
        return `${diffMins} minutes`
      }

      const diffHours = Math.floor(diffMins / 60)
      const remainingMins = diffMins % 60

      if (diffHours < 24) {
        return remainingMins > 0
          ? `${diffHours} hours, ${remainingMins} minutes`
          : `${diffHours} hours`
      }

      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays} days`
    } catch {
      return null
    }
  }

  /**
   * Estimate token count for text
   */
  estimateTokens(text: string): number {
    // Rough estimation: 1 token ≈ 4 characters
    return Math.ceil(text.length / 4)
  }

  /**
   * Get context stats for debugging
   */
  getContextStats(context: string): {
    estimatedTokens: number
    characterCount: number
    percentOfLimit: number
  } {
    const tokens = this.estimateTokens(context)

    return {
      estimatedTokens: tokens,
      characterCount: context.length,
      percentOfLimit: (tokens / this.maxContextTokens) * 100
    }
  }
}

/**
 * Create a singleton instance for easy import
 */
export const contextManager = new ContextManager()
