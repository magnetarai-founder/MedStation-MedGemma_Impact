import { useEffect, useState } from 'react'
import { Hash, Lock, Plus } from 'lucide-react'
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
      {/* Channels - Network mode is now controlled by Globe icon in TeamWorkspace */}
      <div className="flex-1 overflow-y-auto p-2 pt-4">
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
