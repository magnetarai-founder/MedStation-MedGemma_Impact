/**
 * Agent Sessions Panel (Phase C)
 * Main container for managing agent workspace sessions
 */

import { useEffect, useState } from 'react'
import { Plus, X, AlertCircle, Loader2, FolderOpen, CheckCircle2, Info, HelpCircle, ExternalLink } from 'lucide-react'
import { useAgentSessionsStore } from '@/stores/agentSessionsStore'
import type { AgentSession } from '@/types/agentSession'

export function AgentSessionsPanel() {
  const {
    sessions,
    activeSessionId,
    isLoading,
    error,
    activeSession,
    activeSessions,
    archivedSessions,
    loadSessions,
    createSession,
    setActiveSession,
    closeSession,
    clearError
  } = useAgentSessionsStore()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [repoRoot, setRepoRoot] = useState('')
  const [workItemId, setWorkItemId] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [showFirstRunHint, setShowFirstRunHint] = useState(() => {
    return !localStorage.getItem('elohim_agent_sessions_hint_dismissed')
  })
  const [showLearnMore, setShowLearnMore] = useState(false)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const dismissFirstRunHint = () => {
    localStorage.setItem('elohim_agent_sessions_hint_dismissed', 'true')
    setShowFirstRunHint(false)
  }

  const handleCreate = async () => {
    if (!repoRoot.trim()) {
      return
    }

    const session = await createSession({
      repo_root: repoRoot.trim(),
      attached_work_item_id: workItemId.trim() || undefined
    }, true)

    if (session) {
      setRepoRoot('')
      setWorkItemId('')
      setShowCreateForm(false)
    }
  }

  const handleClose = async (id: string) => {
    if (confirm('Close this session? It will be archived and can no longer be used.')) {
      await closeSession(id)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return `${Math.floor(diffMins / 1440)}d ago`
  }

  const SessionItem = ({ session }: { session: AgentSession }) => {
    const isActive = session.id === activeSessionId
    const shortId = session.id.substring(0, 12)

    return (
      <div
        className={`p-3 rounded-lg border cursor-pointer transition-all ${
          isActive
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
        }`}
        onClick={() => setActiveSession(session.id)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FolderOpen className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <span className="text-sm font-mono text-gray-900 dark:text-gray-100 truncate">
                {session.repo_root.split('/').pop() || session.repo_root}
              </span>
              {isActive && (
                <CheckCircle2 className="w-4 h-4 text-primary-600 flex-shrink-0" />
              )}
            </div>

            <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
              <span className="font-mono">{shortId}</span>
              <span>•</span>
              <span>{formatDate(session.last_activity_at)}</span>
            </div>

            {session.current_plan && session.current_plan.steps && (
              <div className="mt-2 text-xs text-gray-600 dark:text-gray-300">
                Plan: {session.current_plan.steps.length} step(s)
              </div>
            )}

            {session.attached_work_item_id && (
              <div className="mt-2 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                <ExternalLink className="w-3 h-3" />
                <span className="font-medium">Linked Work Item: {session.attached_work_item_id.substring(0, 12)}</span>
              </div>
            )}
          </div>

          {session.status === 'active' && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleClose(session.id)
              }}
              className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              title="Close session"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Agent Sessions
          </h2>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-3 py-1.5 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors flex items-center gap-1.5 text-sm"
          >
            <Plus className="w-4 h-4" />
            New
          </button>
        </div>

        {activeSession() && (
          <div className="text-xs text-gray-600 dark:text-gray-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-1 rounded">
            Active: {activeSession()!.repo_root.split('/').pop()}
          </div>
        )}
      </div>

      {/* T3-2: Per-User Scope Banner */}
      <div className="mx-4 mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-1">
              Your agent sessions
            </h4>
            <p className="text-xs text-blue-800 dark:text-blue-200/80 mb-2">
              Sessions are tied to your account and are not shared with your team.
            </p>
            <div className="text-xs text-blue-700 dark:text-blue-300/80 font-medium">
              Active sessions: {activeSessions().length} · Archived: {archivedSessions().length}
            </div>
          </div>
        </div>
      </div>

      {/* First-Run Hint Banner */}
      {showFirstRunHint && (
        <div className="mx-4 mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-1 flex items-center gap-2">
                <Info className="w-4 h-4" />
                New: Agent Sessions keep your coding context alive
              </h4>
              <p className="text-sm text-blue-800 dark:text-blue-200/80 mb-2">
                Sessions remember your repo and plans across multiple agent actions. You can safely use the agent without a session, but sessions improve continuity.
              </p>
              {showLearnMore && (
                <div className="mt-2 text-xs text-blue-700 dark:text-blue-300/70 space-y-1">
                  <p>• Sessions preserve context between agent requests</p>
                  <p>• Attach to workflow work items for tracking</p>
                  <p>• Close when done to archive and free resources</p>
                </div>
              )}
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={dismissFirstRunHint}
                  className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                >
                  Got it
                </button>
                <button
                  onClick={() => setShowLearnMore(!showLearnMore)}
                  className="px-3 py-1 text-blue-600 dark:text-blue-400 text-sm hover:underline"
                >
                  {showLearnMore ? 'Show less' : 'Learn more'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
          <button
            onClick={clearError}
            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreateForm && (
        <div className="mx-4 mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Create New Session
          </h3>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                Repository Root *
                <span className="relative group">
                  <HelpCircle className="w-3 h-3 text-gray-400 cursor-help" />
                  <span className="absolute left-0 bottom-full mb-1 hidden group-hover:block w-48 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg z-10">
                    Path to your project root. The agent will use this to analyze files and context.
                  </span>
                </span>
              </label>
              <input
                type="text"
                value={repoRoot}
                onChange={(e) => setRepoRoot(e.target.value)}
                placeholder="/path/to/repo"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1">
                Work Item ID (optional)
                <span className="relative group">
                  <HelpCircle className="w-3 h-3 text-gray-400 cursor-help" />
                  <span className="absolute left-0 bottom-full mb-1 hidden group-hover:block w-48 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg z-10">
                    Link this session to a workflow work item for tracking and context.
                  </span>
                </span>
              </label>
              <input
                type="text"
                value={workItemId}
                onChange={(e) => setWorkItemId(e.target.value)}
                placeholder="work_item_abc123"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={!repoRoot.trim() || isLoading}
                className="flex-1 px-3 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                Create
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && sessions.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      )}

      {/* Sessions list */}
      {!isLoading && sessions.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400 p-8 text-center">
          <FolderOpen className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-sm mb-1">No sessions yet</p>
          <p className="text-xs">Create a session to get started</p>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {/* Active sessions */}
          {activeSessions().length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Active
              </h3>
              <div className="space-y-2">
                {activeSessions().map(session => (
                  <SessionItem key={session.id} session={session} />
                ))}
              </div>
            </div>
          )}

          {/* Archived sessions (collapsible) */}
          {archivedSessions().length > 0 && (
            <div>
              <button
                onClick={() => setShowArchived(!showArchived)}
                className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Archived ({archivedSessions().length}) {showArchived ? '▼' : '▶'}
              </button>
              {showArchived && (
                <div className="space-y-2">
                  {archivedSessions().map(session => (
                    <SessionItem key={session.id} session={session} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
