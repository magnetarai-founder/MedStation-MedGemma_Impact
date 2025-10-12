import { useEffect, useState } from 'react'
import { MessageSquarePlus, MessageSquare, Trash2, Settings } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

export function ChatSidebar() {
  const [showSettings, setShowSettings] = useState(false)
  const {
    sessions,
    activeChatId,
    settings,
    availableModels,
    setAvailableModels,
    setSessions,
    setActiveChat,
    setMessages,
    updateSettings
  } = useChatStore()

  // Ensure settings have all required fields with defaults
  const safeSettings = {
    tone: settings.tone || 'balanced',
    temperature: settings.temperature ?? 0.7,
    topP: settings.topP ?? 0.9,
    topK: settings.topK ?? 40,
    repeatPenalty: settings.repeatPenalty ?? 1.1,
    systemPrompt: settings.systemPrompt || '',
    ...settings
  }

  // Load sessions and models on mount
  useEffect(() => {
    loadSessions()
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      const response = await fetch(`/api/v1/chat/models`)
      if (response.ok) {
        const models = await response.json()
        setAvailableModels(models)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadSessions = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions`)
      if (response.ok) {
        const data = await response.json()
        setSessions(data)

        // If there's a stored active chat ID (from current session), try to restore it
        if (activeChatId) {
          const storedChatExists = data.find((s: any) => s.id === activeChatId)
          if (storedChatExists) {
            selectChat(activeChatId)
          } else {
            // Stored chat doesn't exist anymore, clear it
            setActiveChat(null)
          }
        }

        // Don't auto-create or auto-select - let user choose
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }
  }

  const createNewChat = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New Chat',
          model: 'qwen2.5-coder:7b-instruct'
        })
      })

      if (response.ok) {
        const newSession = await response.json()
        setSessions([newSession, ...sessions])
        selectChat(newSession.id)
      }
    } catch (error) {
      console.error('Failed to create chat:', error)
    }
  }

  const selectChat = async (chatId: string) => {
    setActiveChat(chatId)

    // Load messages for this chat
    try {
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const deleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (!confirm('Delete this chat?')) return

    try {
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const updatedSessions = sessions.filter(s => s.id !== chatId)
        setSessions(updatedSessions)

        // If deleted active chat, select another
        if (activeChatId === chatId) {
          if (updatedSessions.length > 0) {
            selectChat(updatedSessions[0].id)
          } else {
            setActiveChat(null)
            setMessages([])
          }
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10 dark:border-gray-700/30 flex gap-2">
        <button
          onClick={createNewChat}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-2xl hover:shadow-md transition-all font-medium"
        >
          <MessageSquarePlus size={18} />
          <span>New Chat</span>
        </button>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center justify-center w-11 h-11 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-2xl transition-all"
          title="Chat Settings"
        >
          <Settings size={18} />
        </button>
      </div>

      {/* Chat Settings Panel */}
      {showSettings && (
        <div className="p-4 border-b border-white/10 dark:border-gray-700/30 space-y-4 bg-gray-50/50 dark:bg-gray-800/50 max-h-[70vh] overflow-y-auto">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Chat Settings</h3>

          <div className="space-y-4">
            {/* Model Selection */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Default Model
              </label>
              <select
                value={settings.defaultModel}
                onChange={(e) => updateSettings({ defaultModel: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              >
                {availableModels.length === 0 ? (
                  <option value="">Loading models...</option>
                ) : (
                  availableModels.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name} ({model.size})
                    </option>
                  ))
                )}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Pre-loaded on app start</p>
            </div>

            {/* Tone Presets */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tone Preset
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['creative', 'balanced', 'precise', 'custom'] as const).map((tone) => (
                  <button
                    key={tone}
                    onClick={() => updateSettings({ tone })}
                    className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                      safeSettings.tone === tone
                        ? 'bg-primary-100 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                        : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-primary-300'
                    }`}
                  >
                    {tone.charAt(0).toUpperCase() + tone.slice(1)}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {safeSettings.tone === 'creative' && 'Higher temp, more creative & varied'}
                {safeSettings.tone === 'balanced' && 'Balanced creativity & accuracy'}
                {safeSettings.tone === 'precise' && 'Lower temp, more focused & deterministic'}
                {safeSettings.tone === 'custom' && 'Use custom parameters below'}
              </p>
            </div>

            {/* Temperature */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Temperature
                </label>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {safeSettings.temperature.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="2"
                step="0.05"
                value={safeSettings.temperature}
                onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value), tone: 'custom' })}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                disabled={safeSettings.tone !== 'custom'}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Controls randomness (0 = deterministic, 2 = very creative)</p>
            </div>

            {/* Top P */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Top P (Nucleus Sampling)
                </label>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {safeSettings.topP.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={safeSettings.topP}
                onChange={(e) => updateSettings({ topP: parseFloat(e.target.value), tone: 'custom' })}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                disabled={safeSettings.tone !== 'custom'}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Cumulative probability cutoff for token selection</p>
            </div>

            {/* Top K */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Top K
                </label>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {safeSettings.topK}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                step="1"
                value={safeSettings.topK}
                onChange={(e) => updateSettings({ topK: parseInt(e.target.value), tone: 'custom' })}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                disabled={safeSettings.tone !== 'custom'}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Limits sampling to top K most likely tokens</p>
            </div>

            {/* Repeat Penalty */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Repeat Penalty
                </label>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {safeSettings.repeatPenalty.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="2"
                step="0.05"
                value={safeSettings.repeatPenalty}
                onChange={(e) => updateSettings({ repeatPenalty: parseFloat(e.target.value), tone: 'custom' })}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                disabled={safeSettings.tone !== 'custom'}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Penalizes repetition (1.0 = no penalty, higher = less repetition)</p>
            </div>

            {/* System Prompt */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                System Prompt
              </label>
              <textarea
                value={safeSettings.systemPrompt}
                onChange={(e) => updateSettings({ systemPrompt: e.target.value })}
                placeholder="You are a helpful AI assistant..."
                rows={3}
                className="w-full px-3 py-2 text-sm rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Instructions sent with every message</p>
            </div>

            {/* Auto-generate titles */}
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Auto-generate titles</label>
                <p className="text-xs text-gray-500 dark:text-gray-400">Name chats from first message</p>
              </div>
              <input
                type="checkbox"
                checked={settings.autoGenerateTitles}
                onChange={(e) => updateSettings({ autoGenerateTitles: e.target.checked })}
                className="w-4 h-4 rounded text-primary-600"
              />
            </div>

            {/* Context Window (locked) */}
            <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <p className="text-xs font-medium text-gray-900 dark:text-gray-100">Context Window: 200k tokens</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Full conversation history sent to model for optimal context preservation</p>
            </div>
          </div>
        </div>
      )}

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-sm">No chats yet</p>
            <p className="text-xs mt-2">Create a new chat to get started</p>
          </div>
        ) : (
          <div className="p-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => selectChat(session.id)}
                className={`w-full text-left p-3 rounded-2xl mb-2 group transition-all ${
                  activeChatId === session.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 shadow-sm'
                    : 'hover:bg-white/50 dark:hover:bg-gray-700/50 border border-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare size={14} className="text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {session.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{session.message_count} messages</span>
                      <span>•</span>
                      <span>{formatDate(session.updated_at)}</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => deleteChat(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-opacity"
                    title="Delete chat"
                  >
                    <Trash2 size={14} className="text-red-600 dark:text-red-400" />
                  </button>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
