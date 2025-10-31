/**
 * Mention Input Component
 *
 * Text input with @ mentions support for tagging team members
 * Uses react-mentions library for autocomplete functionality
 */

import { useState, useEffect } from 'react'
import { Mention, MentionsInput, SuggestionDataItem } from 'react-mentions'
import { useQuery } from '@tanstack/react-query'
import { User, AtSign } from 'lucide-react'

interface TeamMember {
  user_id: string
  display_name: string
  device_name?: string
  role?: string
}

interface MentionInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  minRows?: number
  maxRows?: number
  disabled?: boolean
}

export function MentionInput({
  value,
  onChange,
  placeholder = 'Add a comment... Use @ to mention someone',
  className = '',
  minRows = 3,
  maxRows = 10,
  disabled = false,
}: MentionInputProps) {
  const [focused, setFocused] = useState(false)

  // Fetch team members
  const { data: teamMembers = [] } = useQuery<TeamMember[]>({
    queryKey: ['team-members'],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/v1/teams/members')
      // return await response.json()

      // Mock data
      return [
        {
          user_id: 'user_1',
          display_name: 'Field Worker',
          device_name: 'MacBook Pro',
          role: 'super_admin',
        },
        {
          user_id: 'user_2',
          display_name: 'Sarah Chen',
          device_name: 'iPhone 14',
          role: 'admin',
        },
        {
          user_id: 'user_3',
          display_name: 'Mike Rodriguez',
          device_name: 'iPad Pro',
          role: 'member',
        },
        {
          user_id: 'user_4',
          display_name: 'Emily Johnson',
          device_name: 'Android Phone',
          role: 'viewer',
        },
      ]
    },
  })

  // Convert team members to mention suggestions format
  const mentionData: SuggestionDataItem[] = teamMembers.map((member) => ({
    id: member.user_id,
    display: member.display_name,
  }))

  // Custom styles for MentionsInput
  const mentionStyle = {
    control: {
      backgroundColor: 'transparent',
      fontSize: 14,
      fontWeight: 'normal',
      minHeight: `${minRows * 1.5}rem`,
    },
    '&multiLine': {
      control: {
        fontFamily: 'inherit',
        minHeight: `${minRows * 1.5}rem`,
      },
      highlighter: {
        padding: '0.75rem',
        border: '1px solid transparent',
      },
      input: {
        padding: '0.75rem',
        border: '1px solid transparent',
        outline: 'none',
        minHeight: `${minRows * 1.5}rem`,
        maxHeight: `${maxRows * 1.5}rem`,
        overflowY: 'auto',
      },
    },
    suggestions: {
      list: {
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '0.5rem',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        fontSize: 14,
        maxHeight: '200px',
        overflowY: 'auto',
      },
      item: {
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid #f3f4f6',
        cursor: 'pointer',
        '&focused': {
          backgroundColor: '#eff6ff',
        },
      },
    },
  }

  // Dark mode styles
  const darkModeStyle = {
    ...mentionStyle,
    suggestions: {
      list: {
        ...mentionStyle.suggestions.list,
        backgroundColor: '#1f2937',
        borderColor: '#374151',
      },
      item: {
        ...mentionStyle.suggestions.item,
        borderBottomColor: '#374151',
        '&focused': {
          backgroundColor: '#1e3a8a',
        },
      },
    },
  }

  return (
    <div className={`relative ${className}`}>
      <div
        className={`rounded-lg border transition-colors ${
          focused
            ? 'border-blue-500 ring-2 ring-blue-500/20'
            : 'border-gray-300 dark:border-gray-600'
        } ${
          disabled
            ? 'opacity-50 cursor-not-allowed bg-gray-100 dark:bg-gray-800'
            : 'bg-white dark:bg-gray-700'
        }`}
      >
        <MentionsInput
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={mentionStyle}
          className="mentions-input text-gray-900 dark:text-gray-100"
          allowSpaceInQuery
        >
          <Mention
            trigger="@"
            data={mentionData}
            renderSuggestion={(suggestion, search, highlightedDisplay) => (
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {highlightedDisplay}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {teamMembers.find((m) => m.user_id === suggestion.id)?.device_name}
                  </div>
                </div>
              </div>
            )}
            markup="@[__display__](__id__)"
            displayTransform={(id, display) => `@${display}`}
            className="mentions__mention"
            style={{
              backgroundColor: '#dbeafe',
              borderRadius: '0.25rem',
              padding: '0.125rem 0.25rem',
              color: '#1e40af',
              fontWeight: 500,
            }}
          />
        </MentionsInput>
      </div>

      {/* Helper Text */}
      {!disabled && (
        <div className="flex items-center gap-1 mt-1 text-xs text-gray-500 dark:text-gray-400">
          <AtSign className="w-3 h-3" />
          <span>Type @ to mention team members</span>
        </div>
      )}
    </div>
  )
}

/**
 * Extract mentions from text
 *
 * Extracts user IDs of mentioned users from text with @ mentions
 */
export function extractMentions(text: string): string[] {
  const mentionRegex = /@\[([^\]]+)\]\(([^)]+)\)/g
  const mentions: string[] = []
  let match

  while ((match = mentionRegex.exec(text)) !== null) {
    mentions.push(match[2]) // match[2] is the user ID
  }

  return mentions
}

/**
 * Convert mentions markup to display format
 *
 * Converts @[Display Name](user_id) to @Display Name for display
 */
export function convertMentionsToDisplay(text: string): string {
  return text.replace(/@\[([^\]]+)\]\(([^)]+)\)/g, '@$1')
}

/**
 * Check if text contains mentions
 */
export function hasMentions(text: string): boolean {
  return /@\[([^\]]+)\]\(([^)]+)\)/.test(text)
}
