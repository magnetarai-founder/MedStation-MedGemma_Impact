import { useEffect, useState, useRef } from 'react'
import { Hash, Lock, Plus, ChevronDown, Wifi, WifiOff, User } from 'lucide-react'
import { useTeamChatStore } from '../stores/teamChatStore'

interface TeamChatSidebarProps {
  mode: 'solo' | 'p2p'
  onModeChange: (mode: 'solo' | 'p2p') => void
}

export function TeamChatSidebar({ mode, onModeChange }: TeamChatSidebarProps) {
  const {
    channels,
    activeChannelId,
    setActiveChannel,
    setChannels,
  } = useTeamChatStore()

  const [showNewChannelDialog, setShowNewChannelDialog] = useState(false)
  const [newChannelName, setNewChannelName] = useState('')
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)
  const workspaceMenuRef = useRef<HTMLDivElement>(null)

  // Close workspace menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (workspaceMenuRef.current && !workspaceMenuRef.current.contains(event.target as Node)) {
        setShowWorkspaceMenu(false)
      }
    }

    if (showWorkspaceMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showWorkspaceMenu])

  // Load channels in solo mode from localStorage
  useEffect(() => {
    if (mode === 'solo') {
      const saved = localStorage.getItem('solo_channels')
      if (saved) {
        setChannels(JSON.parse(saved))
      } else {
        // Create default channels for solo mode
        const defaultChannels = [
          {
            id: 'general',
            name: 'general',
            type: 'public' as const,
            created_at: new Date().toISOString(),
            created_by: 'me',
            members: ['me'],
            admins: ['me'],
            description: 'General notes and references'
          },
          {
            id: 'files',
            name: 'files',
            type: 'public' as const,
            created_at: new Date().toISOString(),
            created_by: 'me',
            members: ['me'],
            admins: ['me'],
            description: 'File references and attachments'
          }
        ]
        setChannels(defaultChannels)
        localStorage.setItem('solo_channels', JSON.stringify(defaultChannels))
      }
    }
  }, [mode])

  // Save channels when they change in solo mode
  useEffect(() => {
    if (mode === 'solo' && channels.length > 0) {
      localStorage.setItem('solo_channels', JSON.stringify(channels))
    }
  }, [channels, mode])

  const handleCreateChannel = () => {
    if (!newChannelName.trim()) return

    const newChannel = {
      id: `channel_${Date.now()}`,
      name: newChannelName.toLowerCase().replace(/\s+/g, '-'),
      type: 'public' as const,
      created_at: new Date().toISOString(),
      created_by: 'me',
      members: ['me'],
      admins: ['me'],
      description: 'New channel'
    }

    setChannels([...channels, newChannel])
    setActiveChannel(newChannel.id)
    setNewChannelName('')
    setShowNewChannelDialog(false)
  }

  const publicChannels = channels.filter(ch => ch.type === 'public')
  const privateChannels = channels.filter(ch => ch.type === 'private')

  return (
    <div className="h-full flex flex-col">
      {/* Workspace Header - Slack-style dropdown */}
      <div className="p-4 border-b border-white/10 dark:border-gray-700/30 relative" ref={workspaceMenuRef}>
        <button
          onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
          className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-2xl transition-all"
        >
          <div className="flex-1 text-left">
            <h2 className="font-bold text-base text-gray-900 dark:text-gray-100">
              {mode === 'solo' ? 'My Workspace' : 'Team Network'}
            </h2>
            <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
              <div className={`w-2 h-2 rounded-full ${mode === 'solo' ? 'bg-green-500' : 'bg-blue-500'}`}></div>
              <span>{mode === 'solo' ? 'Solo Mode' : 'P2P Mode'}</span>
            </div>
          </div>
          <ChevronDown size={16} className={`text-gray-400 transition-transform ${showWorkspaceMenu ? 'rotate-180' : ''}`} />
        </button>

        {/* Workspace Dropdown */}
        {showWorkspaceMenu && (
          <div className="absolute top-full left-4 right-4 mt-2 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">
            <div className="p-2">
              <div className={`px-3 py-2.5 rounded-xl ${mode === 'solo' ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'} transition-colors`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <User size={16} className="text-gray-600 dark:text-gray-400" />
                    <div>
                      <div className="font-semibold text-sm text-gray-900 dark:text-gray-100">My Workspace</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                        Solo Mode
                      </div>
                    </div>
                  </div>
                  {mode === 'solo' && (
                    <svg className="w-4 h-4 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                    </svg>
                  )}
                </div>
              </div>

              <div className={`px-3 py-2.5 rounded-xl mt-1 ${mode === 'p2p' ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'} transition-colors`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Wifi size={16} className="text-gray-600 dark:text-gray-400" />
                    <div>
                      <div className="font-semibold text-sm text-gray-900 dark:text-gray-100">Team Network</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <WifiOff size={12} />
                        Not connected
                      </div>
                    </div>
                  </div>
                  {mode === 'p2p' && (
                    <svg className="w-4 h-4 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                    </svg>
                  )}
                </div>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 p-2">
              <button
                onClick={() => {
                  onModeChange(mode === 'solo' ? 'p2p' : 'solo')
                  setShowWorkspaceMenu(false)
                }}
                className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl transition-colors"
              >
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                  </svg>
                  Switch to {mode === 'solo' ? 'Team Network' : 'My Workspace'}
                </div>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Channels */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="mb-3">
          <div className="flex items-center justify-between px-2 py-1 mb-1">
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">CHANNELS</span>
            <button
              onClick={() => setShowNewChannelDialog(true)}
              className="p-1 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-colors"
              title="Add channel"
            >
              <Plus size={14} className="text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          {publicChannels.map((channel) => (
            <button
              key={channel.id}
              onClick={() => setActiveChannel(channel.id)}
              className={`w-full text-left px-3 py-2 rounded-2xl mb-1 flex items-center gap-2 transition-all ${
                activeChannelId === channel.id
                  ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 shadow-sm'
                  : 'hover:bg-white/50 dark:hover:bg-gray-700/50 border border-transparent'
              }`}
            >
              <Hash size={16} className={`flex-shrink-0 ${activeChannelId === channel.id ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
              <span className={`truncate text-sm font-medium ${activeChannelId === channel.id ? 'text-gray-900 dark:text-gray-100' : 'text-gray-700 dark:text-gray-300'}`}>
                {channel.name}
              </span>
            </button>
          ))}

          <button
            onClick={() => setShowNewChannelDialog(true)}
            className="w-full text-left px-3 py-2 rounded-2xl flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50 transition-all text-sm"
          >
            <Plus size={16} className="flex-shrink-0" />
            <span>Add channel</span>
          </button>
        </div>

        {privateChannels.length > 0 && (
          <div className="mb-3">
            <div className="px-2 py-1 mb-1">
              <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">PRIVATE</span>
            </div>

            {privateChannels.map((channel) => (
              <button
                key={channel.id}
                onClick={() => setActiveChannel(channel.id)}
                className={`w-full text-left px-3 py-2 rounded-2xl mb-1 flex items-center gap-2 transition-all ${
                  activeChannelId === channel.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 shadow-sm'
                    : 'hover:bg-white/50 dark:hover:bg-gray-700/50 border border-transparent'
                }`}
              >
                <Lock size={16} className={`flex-shrink-0 ${activeChannelId === channel.id ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'}`} />
                <span className={`truncate text-sm font-medium ${activeChannelId === channel.id ? 'text-gray-900 dark:text-gray-100' : 'text-gray-700 dark:text-gray-300'}`}>
                  {channel.name}
                </span>
              </button>
            ))}
          </div>
        )}

        {mode === 'p2p' && (
          <div className="mb-3">
            <div className="px-2 py-1 mb-1">
              <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">DIRECT MESSAGES</span>
            </div>
            <div className="px-3 py-4 text-xs text-gray-500 dark:text-gray-400 text-center">
              No peers online
            </div>
          </div>
        )}
      </div>

      {/* New Channel Dialog */}
      {showNewChannelDialog && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Create a channel
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Channel name
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">#</span>
                  <input
                    type="text"
                    value={newChannelName}
                    onChange={(e) => setNewChannelName(e.target.value)}
                    placeholder="e.g. projects, ideas, resources"
                    className="w-full pl-8 pr-3 py-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreateChannel()
                      if (e.key === 'Escape') setShowNewChannelDialog(false)
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowNewChannelDialog(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateChannel}
                disabled={!newChannelName.trim()}
                className="flex-1 px-4 py-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
