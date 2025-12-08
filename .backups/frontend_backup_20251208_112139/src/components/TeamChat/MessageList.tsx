/**
 * MessageList Component
 * Displays chat messages with avatars, timestamps, and message actions
 */

import React from 'react'
import DOMPurify from 'dompurify'
import { Smile, Paperclip, Pencil, Trash2, Check, Hash } from 'lucide-react'
import { LocalMessage } from './types'

interface MessageListProps {
  messages: LocalMessage[]
  activeChannelName: string
  mode: 'solo' | 'p2p'
  editingMessageId: string | null
  editingContent: string
  onChangeEditingContent: (value: string) => void
  onSaveEdit: (messageId: string) => void
  onCancelEdit: () => void
  onDeleteMessage: (messageId: string) => void
  formatTimestamp: (timestamp: string) => string
  renderMarkdown: (text: string) => string
  onEditMessage: (messageId: string) => void
  messagesEndRef: React.RefObject<HTMLDivElement>
}

export function MessageList({
  messages,
  activeChannelName,
  mode,
  editingMessageId,
  editingContent,
  onChangeEditingContent,
  onSaveEdit,
  onCancelEdit,
  onDeleteMessage,
  formatTimestamp,
  renderMarkdown,
  onEditMessage,
  messagesEndRef
}: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mt-8">
          <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
            This is the very beginning of the <span className="text-gray-700 dark:text-gray-300">{activeChannelName}</span> channel
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {mode === 'solo'
              ? 'This channel is for you to organize your thoughts and files.'
              : 'This channel is for team-wide communication and collaboration.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      <div className="space-y-4">
        {messages.map((message, index) => {
          const showAvatar = index === 0 || messages[index - 1].sender_name !== message.sender_name

          return (
            <div
              key={message.id}
              className={`group flex gap-3 hover:bg-gray-50 dark:hover:bg-gray-900/30 -mx-2 px-2 py-1.5 rounded transition-colors ${
                showAvatar ? 'mt-3' : 'mt-0.5'
              }`}
            >
              <div className="flex-shrink-0 w-9">
                {showAvatar && (
                  <div className="w-9 h-9 rounded bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center text-white font-semibold text-sm">
                    {message.sender_name[0].toUpperCase()}
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                {showAvatar && (
                  <div className="flex items-baseline gap-2 mb-0.5">
                    <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                      {message.sender_name}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatTimestamp(message.timestamp)}
                    </span>
                  </div>
                )}

                <div className="text-gray-900 dark:text-gray-100 text-[15px] leading-relaxed">
                  {editingMessageId === message.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editingContent}
                        onChange={(e) => onChangeEditingContent(e.target.value)}
                        className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:border-primary-500 resize-none"
                        rows={3}
                        autoFocus
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => onSaveEdit(message.id)}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm flex items-center gap-1"
                        >
                          <Check size={14} />
                          Save
                        </button>
                        <button
                          onClick={onCancelEdit}
                          className="px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : message.type === 'file' && message.file ? (
                    <div className="space-y-2">
                      {message.content && (
                        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
                      )}
                      <a
                        href={message.file.url}
                        download={message.file.name}
                        className="flex items-center gap-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors max-w-sm"
                      >
                        <Paperclip size={16} className="text-gray-500 dark:text-gray-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {message.file.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {(message.file.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </a>
                    </div>
                  ) : (
                    <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
                  )}
                </div>
              </div>

              {/* Message hover actions (Slack-style) */}
              {editingMessageId !== message.id && (
                <div className="opacity-0 group-hover:opacity-100 flex items-start gap-0.5 transition-opacity">
                  <button
                    onClick={() => onEditMessage(message.id)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                    title="Edit message"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => onDeleteMessage(message.id)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                    title="Delete message"
                  >
                    <Trash2 size={14} />
                  </button>
                  <button
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                    title="Add reaction"
                  >
                    <Smile size={16} />
                  </button>
                </div>
              )}
            </div>
          )
        })}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
