import { useState, useEffect } from 'react'
import { TeamChatSidebar } from './TeamChatSidebar'
import { TeamChatWindow } from './TeamChatWindow'

export function TeamChat() {
  // Default to solo mode
  const [mode, setMode] = useState<'solo' | 'p2p'>('solo')

  // Load saved mode preference
  useEffect(() => {
    const savedMode = localStorage.getItem('team_chat_mode')
    if (savedMode === 'p2p' || savedMode === 'solo') {
      setMode(savedMode)
    }
  }, [])

  // Save mode preference when it changes
  const handleModeChange = (newMode: 'solo' | 'p2p') => {
    setMode(newMode)
    localStorage.setItem('team_chat_mode', newMode)
  }

  return (
    <div className="h-full w-full flex">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 bg-gray-50/80 dark:bg-gray-800/50 backdrop-blur-xl border-r border-white/10 dark:border-gray-700/30">
        <TeamChatSidebar mode={mode} onModeChange={handleModeChange} />
      </div>

      {/* Main chat area */}
      <div className="flex-1">
        <TeamChatWindow mode={mode} />
      </div>
    </div>
  )
}
