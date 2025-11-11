import { createWithEqualityFn } from 'zustand/traditional'

export interface Peer {
  peer_id: string
  display_name: string
  device_name: string
  public_key: string
  status: 'online' | 'away' | 'offline'
  last_seen: string
  avatar_hash?: string
  bio?: string
}

export interface Channel {
  id: string
  name: string
  type: 'public' | 'private' | 'direct'
  created_at: string
  created_by: string
  members: string[]
  admins: string[]
  description?: string
  topic?: string
  dm_participants?: string[]
}

export interface TeamMessage {
  id: string
  channel_id: string
  sender_id: string
  sender_name: string
  type: 'text' | 'file' | 'system'
  content: string
  encrypted: boolean
  timestamp: string
  edited_at?: string
  file_metadata?: {
    name: string
    size: number
    hash: string
    mime_type: string
  }
  thread_id?: string
  reply_to?: string
  reactions: Record<string, string[]>
  delivered_to: string[]
  read_by: string[]
}

export interface P2PStatus {
  peer_id: string
  is_connected: boolean
  discovered_peers: number
  active_channels: number
  multiaddrs: string[]
}

interface TeamChatStore {
  // P2P Status
  status: P2PStatus | null
  isInitialized: boolean
  isConnecting: boolean

  // Peers
  peers: Peer[]
  onlinePeers: Peer[]

  // Channels
  channels: Channel[]
  activeChannelId: string | null

  // Messages
  messagesByChannel: Record<string, TeamMessage[]>

  // UI State
  isSidebarOpen: boolean
  isLoadingMessages: boolean
  isSendingMessage: boolean

  // Actions
  setStatus: (status: P2PStatus) => void
  setInitialized: (initialized: boolean) => void
  setConnecting: (connecting: boolean) => void
  setPeers: (peers: Peer[]) => void
  setChannels: (channels: Channel[]) => void
  setActiveChannel: (channelId: string | null) => void
  setMessages: (channelId: string, messages: TeamMessage[]) => void
  addMessage: (message: TeamMessage) => void
  toggleSidebar: () => void
  setLoadingMessages: (loading: boolean) => void
  setSendingMessage: (sending: boolean) => void
}

export const useTeamChatStore = createWithEqualityFn<TeamChatStore>((set, get) => ({
  // Initial state
  status: null,
  isInitialized: false,
  isConnecting: false,
  peers: [],
  onlinePeers: [],
  channels: [],
  activeChannelId: null,
  messagesByChannel: {},
  isSidebarOpen: true,
  isLoadingMessages: false,
  isSendingMessage: false,

  // Actions
  setStatus: (status) => set({ status }),

  setInitialized: (initialized) => set({ isInitialized: initialized }),

  setConnecting: (connecting) => set({ isConnecting: connecting }),

  setPeers: (peers) => {
    const onlinePeers = peers.filter(p => p.status === 'online')
    set({ peers, onlinePeers })
  },

  setChannels: (channels) => set({ channels }),

  setActiveChannel: (channelId) => set({ activeChannelId: channelId }),

  setMessages: (channelId, messages) =>
    set((state) => ({
      messagesByChannel: {
        ...state.messagesByChannel,
        [channelId]: messages
      }
    })),

  addMessage: (message) =>
    set((state) => {
      const channelMessages = state.messagesByChannel[message.channel_id] || []
      return {
        messagesByChannel: {
          ...state.messagesByChannel,
          [message.channel_id]: [...channelMessages, message]
        }
      }
    }),

  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  setLoadingMessages: (loading) => set({ isLoadingMessages: loading }),

  setSendingMessage: (sending) => set({ isSendingMessage: sending }),
}))
