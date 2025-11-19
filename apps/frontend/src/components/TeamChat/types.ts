/**
 * TeamChat Types
 * Shared type definitions for Team Chat UI components
 */

export interface LocalMessage {
  id: string
  channel_id: string
  sender_name: string
  content: string
  timestamp: string
  type: 'text' | 'file'
  file?: {
    name: string
    size: number
    type: string
    url: string
  }
}
