import { useEffect } from 'react'
import { Hash, Lock, Plus, MessageSquare, Users } from 'lucide-react'
import { useTeamChatStore } from '../stores/teamChatStore'

interface TeamChatSidebarProps {
  mode: 'solo' | 'p2p'
  onModeChange: (mode: 'solo' | 'p2p') => void
  onShowNewChannel: () => void
}

export function TeamChatSidebar({ mode, onModeChange, onShowNewChannel }: TeamChatSidebarProps) {
  const {
    channels,
    activeChannelId,
    setActiveChannel,
    setChannels,
  } = useTeamChatStore()

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
              onClick={onShowNewChannel}
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
            onClick={onShowNewChannel}
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

        {/* Direct Messages */}
        <div className="mb-3">
          <div className="flex items-center justify-between px-2 py-1 mb-1">
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">DIRECT MESSAGES</span>
            <button
              className="p-1 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-colors"
              title="New message"
            >
              <Plus size={14} className="text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          <div className="px-3 py-3 text-xs text-gray-500 dark:text-gray-400 text-center">
            No dm chats yet
          </div>
        </div>

        {/* Team Chats */}
        <div className="mb-3">
          <div className="flex items-center justify-between px-2 py-1 mb-1">
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">TEAM CHATS</span>
            <button
              className="p-1 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-colors"
              title="New team chat"
            >
              <Plus size={14} className="text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          <div className="px-3 py-3 text-xs text-gray-500 dark:text-gray-400 text-center">
            No team chats yet
          </div>
        </div>
      </div>
    </div>
  )
}
