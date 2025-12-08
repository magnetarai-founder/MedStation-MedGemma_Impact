import { useState, useEffect } from 'react'
import { ResizableSidebar } from '../ResizableSidebar'
import { TeamChatSidebar } from '../TeamChatSidebar'
import { TeamChatWindow } from './TeamChatWindow'
import { P2PPeerDiscovery } from '../P2PPeerDiscovery'
import { P2PFileSharing } from '../P2PFileSharing'
import { X, Wifi, WifiOff, Loader2, Users, Upload } from 'lucide-react'
import { useTeamChatStore } from '../../stores/teamChatStore'
import { useP2PChat } from '../../hooks/useP2PChat'

interface TeamChatProps {
  mode: 'solo' | 'lan' | 'p2p'
}

export function TeamChat({ mode }: TeamChatProps) {
  // Convert network mode to chat mode (lan and p2p both use p2p for chat)
  const chatMode: 'solo' | 'p2p' = mode === 'solo' ? 'solo' : 'p2p'

  const [showNewChannelDialog, setShowNewChannelDialog] = useState(false)
  const [newChannelName, setNewChannelName] = useState('')
  const [newChannelDescription, setNewChannelDescription] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [showPeerDiscovery, setShowPeerDiscovery] = useState(false)
  const [showFileSharing, setShowFileSharing] = useState(false)

  const { channels: localChannels, setChannels, setActiveChannel } = useTeamChatStore()

  // Use P2P hook for real mesh networking
  const p2p = useP2PChat(chatMode)

  // Sync P2P channels with local store when in P2P mode
  useEffect(() => {
    if (chatMode === 'p2p' && p2p.channels.length > 0) {
      setChannels(p2p.channels)
    }
  }, [chatMode, p2p.channels, setChannels])

  const handleCreateChannel = async () => {
    if (!newChannelName.trim()) return

    if (chatMode === 'p2p') {
      // Use P2P API to create channel
      try {
        const channel = await p2p.createChannel(
          newChannelName.toLowerCase().replace(/\s+/g, '-'),
          isPrivate ? 'private' : 'public',
          newChannelDescription || undefined
        )

        setActiveChannel(channel.id)
        setNewChannelName('')
        setNewChannelDescription('')
        setIsPrivate(false)
        setShowNewChannelDialog(false)
      } catch (error) {
        console.error('Failed to create P2P channel:', error)
      }
    } else {
      // Solo mode - use localStorage
      const newChannel = {
        id: `channel_${Date.now()}`,
        name: newChannelName.toLowerCase().replace(/\s+/g, '-'),
        type: (isPrivate ? 'private' : 'public') as const,
        created_at: new Date().toISOString(),
        created_by: 'me',
        members: ['me'],
        admins: ['me'],
        description: newChannelDescription || 'New channel'
      }

      setChannels([...localChannels, newChannel])
      setActiveChannel(newChannel.id)
      setNewChannelName('')
      setNewChannelDescription('')
      setIsPrivate(false)
      setShowNewChannelDialog(false)
      localStorage.setItem('solo_channels', JSON.stringify([...localChannels, newChannel]))
    }
  }

  return (
    <>
      {/* P2P Status Banner */}
      {chatMode === 'p2p' && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            {p2p.isInitializing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
                <span className="text-blue-700 dark:text-blue-300">Initializing P2P mesh...</span>
              </>
            ) : p2p.error ? (
              <>
                <WifiOff className="w-4 h-4 text-red-600 dark:text-red-400" />
                <span className="text-red-700 dark:text-red-300">P2P connection failed</span>
                <button
                  onClick={p2p.retry}
                  className="ml-2 px-2 py-0.5 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                >
                  Retry
                </button>
              </>
            ) : p2p.status?.running ? (
              <>
                <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
                <span className="text-green-700 dark:text-green-300">
                  P2P mesh active • {p2p.peers.length} peer{p2p.peers.length !== 1 ? 's' : ''}
                </span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-gray-700 dark:text-gray-300">P2P mesh offline</span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {p2p.status && (
              <div className="text-xs text-blue-600 dark:text-blue-400 font-mono">
                {p2p.status.peer_id?.substring(0, 8)}...
              </div>
            )}
            <button
              onClick={() => setShowPeerDiscovery(true)}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              title="Connect to Peers"
            >
              <Users className="w-3 h-3" />
              Peers
            </button>
            <button
              onClick={() => setShowFileSharing(true)}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              title="Share Files"
            >
              <Upload className="w-3 h-3" />
              Files
            </button>
          </div>
        </div>
      )}

      <ResizableSidebar
        initialWidth={320}
        minWidth={280}
        storageKey="ns.teamChatSidebarWidth"
        left={<TeamChatSidebar mode={chatMode} onModeChange={() => {}} onShowNewChannel={() => setShowNewChannelDialog(true)} />}
        right={<TeamChatWindow mode={chatMode} />}
      />

      {/* P2P Peer Discovery Modal */}
      <P2PPeerDiscovery
        isOpen={showPeerDiscovery}
        onClose={() => setShowPeerDiscovery(false)}
      />

      {/* P2P File Sharing Modal */}
      <P2PFileSharing
        isOpen={showFileSharing}
        onClose={() => setShowFileSharing(false)}
      />

      {/* New Channel Dialog - Rendered at root level */}
      {showNewChannelDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-900 rounded-lg w-full max-w-xl shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Create a channel
              </h2>
              <button
                onClick={() => {
                  setShowNewChannelDialog(false)
                  setNewChannelName('')
                  setNewChannelDescription('')
                  setIsPrivate(false)
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
              >
                <X size={20} className="text-gray-500 dark:text-gray-400" />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-6">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Channels are where conversations happen around a topic. Use a name that is easy to find and understand.
              </p>

              <div className="space-y-4">
                {/* Channel Name */}
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    Name
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-semibold">#</span>
                    <input
                      type="text"
                      value={newChannelName}
                      onChange={(e) => setNewChannelName(e.target.value)}
                      placeholder="e.g. projects, ideas, resources"
                      className="w-full pl-8 pr-3 py-2.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && newChannelName.trim()) handleCreateChannel()
                        if (e.key === 'Escape') {
                          setShowNewChannelDialog(false)
                          setNewChannelName('')
                          setNewChannelDescription('')
                          setIsPrivate(false)
                        }
                      }}
                    />
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                    Description <span className="text-gray-500 dark:text-gray-400 font-normal">(optional)</span>
                  </label>
                  <textarea
                    value={newChannelDescription}
                    onChange={(e) => setNewChannelDescription(e.target.value)}
                    placeholder="What's this channel about?"
                    className="w-full px-3 py-2.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    rows={3}
                  />
                </div>

                {/* Privacy Toggle */}
                <div>
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPrivate}
                      onChange={(e) => setIsPrivate(e.target.checked)}
                      className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          Make private
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                        {isPrivate
                          ? 'Only specific people can access this channel'
                          : 'Anyone can find and join this channel'}
                      </p>
                    </div>
                  </label>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <button
                onClick={() => {
                  setShowNewChannelDialog(false)
                  setNewChannelName('')
                  setNewChannelDescription('')
                  setIsPrivate(false)
                }}
                className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors font-medium text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateChannel}
                disabled={!newChannelName.trim()}
                className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-sm"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
