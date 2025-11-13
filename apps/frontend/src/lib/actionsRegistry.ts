/**
 * Quick Actions Registry
 *
 * Defines available actions for the command palette (Cmd/Ctrl+K).
 * Sprint 5 Theme D: Quick Actions Panel
 */

export interface QuickAction {
  id: string
  label: string
  keywords: string[]
  category: 'sessions' | 'models' | 'permissions' | 'system'
  icon?: string
  run: () => void | Promise<void>
}

export interface ActionsContext {
  activeSessionId?: string
  activeSessionTitle?: string
  teams?: Array<{ id: string; name: string }>
  hasPermissions?: boolean
  // Callbacks for actions
  onNewSession?: () => void
  onOpenDownloads?: () => void
  onViewTimeline?: () => void
  onSwitchTeam?: () => void
  onExportPermissions?: () => void
  onSearchSessions?: () => void
}

/**
 * Get available quick actions based on context
 *
 * @param context - Current application context
 * @returns List of available actions
 */
export function getActions(context: ActionsContext): QuickAction[] {
  const actions: QuickAction[] = []

  // Session Actions
  if (context.onNewSession) {
    actions.push({
      id: 'new-session',
      label: 'New Session',
      keywords: ['create', 'start', 'chat', 'conversation'],
      category: 'sessions',
      icon: '💬',
      run: context.onNewSession
    })
  }

  if (context.onSearchSessions) {
    actions.push({
      id: 'search-sessions',
      label: 'Search Sessions',
      keywords: ['find', 'search', 'query', 'messages', 'history'],
      category: 'sessions',
      icon: '🔍',
      run: context.onSearchSessions
    })
  }

  if (context.activeSessionId && context.onViewTimeline) {
    actions.push({
      id: 'view-timeline',
      label: 'View Session Timeline',
      keywords: ['history', 'audit', 'events', 'logs'],
      category: 'sessions',
      icon: '📜',
      run: context.onViewTimeline
    })
  }

  // Model Actions
  if (context.onOpenDownloads) {
    actions.push({
      id: 'open-downloads',
      label: 'Open Downloads Manager',
      keywords: ['models', 'download', 'queue', 'install'],
      category: 'models',
      icon: '📥',
      run: context.onOpenDownloads
    })
  }

  // Permissions Actions
  if (context.onExportPermissions) {
    actions.push({
      id: 'export-permissions',
      label: 'Export Permissions',
      keywords: ['download', 'json', 'backup', 'roles'],
      category: 'permissions',
      icon: '🔐',
      run: context.onExportPermissions
    })
  }

  // Team Actions
  if (context.teams && context.teams.length > 0 && context.onSwitchTeam) {
    actions.push({
      id: 'switch-team',
      label: 'Switch Team',
      keywords: ['team', 'organization', 'context', 'change'],
      category: 'system',
      icon: '👥',
      run: context.onSwitchTeam
    })
  }

  return actions
}

/**
 * Fuzzy search actions by label and keywords
 *
 * @param actions - List of actions to search
 * @param query - Search query
 * @returns Filtered and sorted actions
 */
export function searchActions(actions: QuickAction[], query: string): QuickAction[] {
  if (!query.trim()) {
    return actions
  }

  const lowerQuery = query.toLowerCase()

  // Score each action
  const scored = actions.map(action => {
    const labelLower = action.label.toLowerCase()
    const keywordsLower = action.keywords.join(' ').toLowerCase()

    let score = 0

    // Exact prefix match on label (highest priority)
    if (labelLower.startsWith(lowerQuery)) {
      score = 1000
    }
    // Substring match on label
    else if (labelLower.includes(lowerQuery)) {
      score = 500
    }
    // Keyword match
    else if (keywordsLower.includes(lowerQuery)) {
      score = 250
    }
    // Fuzzy match (each query character appears in order)
    else if (fuzzyMatch(labelLower, lowerQuery)) {
      score = 100
    }

    return { action, score }
  })

  // Filter out non-matches and sort by score
  return scored
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .map(item => item.action)
}

/**
 * Simple fuzzy matching: check if query characters appear in order
 *
 * @param text - Text to search in
 * @param query - Query to search for
 * @returns True if all query characters appear in order
 */
function fuzzyMatch(text: string, query: string): boolean {
  let textIndex = 0
  let queryIndex = 0

  while (textIndex < text.length && queryIndex < query.length) {
    if (text[textIndex] === query[queryIndex]) {
      queryIndex++
    }
    textIndex++
  }

  return queryIndex === query.length
}

/**
 * Get category label for display
 *
 * @param category - Action category
 * @returns Human-readable label
 */
export function getCategoryLabel(category: QuickAction['category']): string {
  switch (category) {
    case 'sessions':
      return 'Sessions'
    case 'models':
      return 'Models'
    case 'permissions':
      return 'Permissions'
    case 'system':
      return 'System'
    default:
      return 'Other'
  }
}
