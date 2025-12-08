import axios from 'axios'
import type { Peer, Channel, TeamMessage, P2PStatus } from '../stores/teamChatStore'

const BASE_URL = '/api'

class TeamChatAPI {
  private client = axios.create({
    baseURL: `${BASE_URL}/v1/team`,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000,
  })

  // Initialization
  async initialize(displayName: string, deviceName: string) {
    try {
      const { data } = await this.client.post('/initialize', null, {
        params: { display_name: displayName, device_name: deviceName }
      })
      return data
    } catch (error: any) {
      console.error('P2P initialization error:', error.response?.data || error.message)
      throw new Error(error.response?.data?.detail || error.message || 'Failed to initialize P2P service')
    }
  }

  async getStatus(): Promise<P2PStatus> {
    const { data } = await this.client.get('/status')
    return data
  }

  // Peers
  async listPeers(): Promise<Peer[]> {
    const { data } = await this.client.get('/peers')
    return data.peers
  }

  async getPeer(peerId: string): Promise<Peer> {
    const { data } = await this.client.get(`/peers/${peerId}`)
    return data
  }

  // Channels
  async createChannel(name: string, type: 'public' | 'private', description?: string): Promise<Channel> {
    const { data } = await this.client.post('/channels', {
      name,
      type,
      description,
      members: []
    })
    return data
  }

  async createDM(peerId: string): Promise<Channel> {
    const { data } = await this.client.post('/dm', { peer_id: peerId })
    return data
  }

  async listChannels(): Promise<Channel[]> {
    const { data } = await this.client.get('/channels')
    return data.channels
  }

  async getChannel(channelId: string): Promise<Channel> {
    const { data } = await this.client.get(`/channels/${channelId}`)
    return data
  }

  // Messages
  async sendMessage(
    channelId: string,
    content: string,
    replyTo?: string
  ): Promise<TeamMessage> {
    const { data } = await this.client.post(`/channels/${channelId}/messages`, {
      channel_id: channelId,
      content,
      type: 'text',
      reply_to: replyTo
    })
    return data
  }

  async getMessages(channelId: string, limit: number = 50): Promise<TeamMessage[]> {
    const { data } = await this.client.get(`/channels/${channelId}/messages`, {
      params: { limit }
    })
    return data.messages
  }

  async markAsRead(channelId: string, messageId: string): Promise<void> {
    await this.client.post(`/channels/${channelId}/messages/${messageId}/read`)
  }

  // WebSocket connection
  connectWebSocket(onMessage: (event: any) => void): WebSocket {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${BASE_URL}/v1/team/ws`
    const ws = new WebSocket(wsUrl)
    let pingInterval: NodeJS.Timeout | null = null

    ws.onopen = () => {
      console.log('Team Chat WebSocket connected')
      // Send ping every 30 seconds to keep alive
      pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('Team Chat WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('Team Chat WebSocket disconnected')
      // Clear ping interval on close to prevent memory leak
      if (pingInterval) {
        clearInterval(pingInterval)
        pingInterval = null
      }
    }

    return ws
  }
}

export const teamChatApi = new TeamChatAPI()
