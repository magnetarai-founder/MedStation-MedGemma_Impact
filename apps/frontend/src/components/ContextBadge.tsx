/**
 * Context Badge Component
 *
 * Displays current context (Local or Team: {name})
 * Reads from teamStore to determine badge text and style
 */

import { useTeamStore } from '../stores/teamStore'

interface ContextBadgeProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function ContextBadge({ className = '', size = 'md' }: ContextBadgeProps) {
  const { currentTeam, isOnTeam } = useTeamStore()

  // Size classes
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  }

  // Determine badge content and style
  const isTeamMode = isOnTeam()
  const badgeText = isTeamMode && currentTeam
    ? `Team: ${currentTeam.team_name}`
    : 'Local'

  const badgeClasses = isTeamMode
    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 border-primary-300 dark:border-primary-700'
    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-700'

  return (
    <span
      className={`
        inline-flex items-center gap-1
        ${sizeClasses[size]}
        ${badgeClasses}
        border rounded-full font-medium
        ${className}
      `}
      title={isTeamMode ? `Team context: ${currentTeam?.team_name}` : 'Local context (no team)'}
    >
      {/* Icon indicator */}
      <span className={`w-1.5 h-1.5 rounded-full ${isTeamMode ? 'bg-primary-600 dark:bg-primary-400' : 'bg-gray-400 dark:bg-gray-600'}`} />
      {badgeText}
    </span>
  )
}
