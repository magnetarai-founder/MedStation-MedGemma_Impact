/**
 * P2P Team Chat API Client
 *
 * Provides interface to backend P2P mesh networking for:
 * - Team chat (channels, DMs, messages)
 * - Peer discovery and connection
 * - File sharing
 * - Vault synchronization
 */

import axios from 'axios';

const API_BASE = '/api/v1';

// ===== Types =====

export interface Peer {
  peer_id: string;
  display_name: string;
  device_name: string;
  status: 'online' | 'offline' | 'away';
  last_seen: string;
  public_key?: string;
  avatar_hash?: string;
}

export interface Channel {
  id: string;
  name: string;
  type: 'public' | 'private' | 'dm';
  created_at: string;
  created_by: string;
  description?: string;
  topic?: string;
  members: string[];
  admins: string[];
  dm_participants?: string[];
}

export interface Message {
  id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  type: 'text' | 'file' | 'system';
  content: string;
  encrypted: boolean;
  timestamp: string;
  edited_at?: string;
  file_metadata?: {
    file_name: string;
    file_size: number;
    mime_type: string;
  };
  reactions?: Record<string, string[]>;
  delivered_to?: string[];
  read_by?: string[];
}

export interface P2PStatus {
  running: boolean;
  peer_id?: string;
  display_name?: string;
  device_name?: string;
  multiaddrs?: string[];
  discovered_peers: number;
  active_channels: number;
}

export interface ConnectionCode {
  code: string;
  peer_id: string;
  multiaddrs: string[];
  expires_at?: string;
}

// ===== P2P Service Management =====

/**
 * Initialize P2P service
 */
export async function initializeP2P(displayName: string, deviceName: string): Promise<P2PStatus> {
  const response = await axios.post(`${API_BASE}/team/initialize`, null, {
    params: { display_name: displayName, device_name: deviceName }
  });
  return response.data;
}

/**
 * Start P2P mesh networking
 */
export async function startP2PMesh(displayName: string, deviceName: string): Promise<any> {
  const response = await axios.post(`${API_BASE}/p2p/start`, null, {
    params: { display_name: displayName, device_name: deviceName }
  });
  return response.data;
}

/**
 * Stop P2P service
 */
export async function stopP2P(): Promise<void> {
  await axios.post(`${API_BASE}/team/stop`);
}

/**
 * Get P2P service status
 */
export async function getP2PStatus(): Promise<P2PStatus> {
  const response = await axios.get(`${API_BASE}/team/status`);
  return response.data;
}

// ===== Peer Discovery & Connection =====

/**
 * Get list of discovered peers
 */
export async function getDiscoveredPeers(): Promise<Peer[]> {
  const response = await axios.get(`${API_BASE}/team/peers`);
  return response.data.peers || [];
}

/**
 * Generate connection code for pairing
 */
export async function generateConnectionCode(): Promise<ConnectionCode> {
  const response = await axios.post(`${API_BASE}/p2p/connection-code`);
  return response.data;
}

/**
 * Connect to peer using connection code
 */
export async function connectWithCode(code: string): Promise<{ success: boolean; peer_id: string }> {
  const response = await axios.post(`${API_BASE}/p2p/add-peer`, { code });
  return response.data;
}

/**
 * Connect to peer directly
 */
export async function connectToPeer(peerId: string, multiaddr: string): Promise<void> {
  await axios.post(`${API_BASE}/team/peers/${peerId}/connect`, { multiaddr });
}

/**
 * Disconnect from peer
 */
export async function disconnectFromPeer(peerId: string): Promise<void> {
  await axios.post(`${API_BASE}/team/peers/${peerId}/disconnect`);
}

// ===== Channels =====

/**
 * Get list of channels
 */
export async function getChannels(): Promise<Channel[]> {
  const response = await axios.get(`${API_BASE}/team/channels`);
  return response.data.channels || [];
}

/**
 * Create a new channel
 */
export async function createChannel(
  name: string,
  type: 'public' | 'private',
  description?: string
): Promise<Channel> {
  const response = await axios.post(`${API_BASE}/team/channels`, {
    name,
    type,
    description
  });
  return response.data;
}

/**
 * Create a direct message channel
 */
export async function createDM(peerId: string): Promise<Channel> {
  const response = await axios.post(`${API_BASE}/team/channels/dm`, {
    peer_id: peerId
  });
  return response.data;
}

/**
 * Join a channel
 */
export async function joinChannel(channelId: string): Promise<void> {
  await axios.post(`${API_BASE}/team/channels/${channelId}/join`);
}

/**
 * Leave a channel
 */
export async function leaveChannel(channelId: string): Promise<void> {
  await axios.post(`${API_BASE}/team/channels/${channelId}/leave`);
}

/**
 * Invite peer to channel
 */
export async function inviteToChannel(channelId: string, peerId: string): Promise<void> {
  await axios.post(`${API_BASE}/team/channels/${channelId}/invite`, {
    peer_id: peerId
  });
}

// ===== Messages =====

/**
 * Get messages for a channel
 */
export async function getMessages(channelId: string, limit = 50): Promise<Message[]> {
  const response = await axios.get(`${API_BASE}/team/channels/${channelId}/messages`, {
    params: { limit }
  });
  return response.data.messages || [];
}

/**
 * Send a message to a channel
 */
export async function sendMessage(
  channelId: string,
  content: string,
  type: 'text' | 'file' = 'text'
): Promise<Message> {
  const response = await axios.post(`${API_BASE}/team/channels/${channelId}/messages`, {
    content,
    type
  });
  return response.data;
}

/**
 * Mark message as read
 */
export async function markMessageRead(channelId: string, messageId: string): Promise<void> {
  await axios.post(`${API_BASE}/team/channels/${channelId}/messages/${messageId}/read`);
}

/**
 * Add reaction to message
 */
export async function addReaction(
  channelId: string,
  messageId: string,
  emoji: string
): Promise<void> {
  await axios.post(`${API_BASE}/team/channels/${channelId}/messages/${messageId}/react`, {
    emoji
  });
}

// ===== File Sharing =====

/**
 * Upload and share file in channel
 */
export async function shareFile(
  channelId: string,
  file: File,
  onProgress?: (progress: number) => void
): Promise<Message> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('channel_id', channelId);

  const response = await axios.post(`${API_BASE}/team/files/share`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    }
  });

  return response.data;
}

/**
 * Download shared file
 */
export async function downloadFile(
  fileId: string,
  onProgress?: (progress: number) => void
): Promise<Blob> {
  const response = await axios.get(`${API_BASE}/team/files/${fileId}`, {
    responseType: 'blob',
    onDownloadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    }
  });

  return response.data;
}

/**
 * Get list of shared files
 */
export async function getSharedFiles(): Promise<any[]> {
  const response = await axios.get(`${API_BASE}/team/files`);
  return response.data.files || [];
}

// ===== WebSocket for Real-time Updates =====

/**
 * Connect to P2P WebSocket for real-time messages
 */
export function connectP2PWebSocket(
  onMessage: (message: Message) => void,
  onPeerUpdate: (peer: Peer) => void,
  onChannelUpdate: (channel: Channel) => void
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}${API_BASE}/team/ws`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'message':
          onMessage(data.data);
          break;
        case 'peer_update':
          onPeerUpdate(data.data);
          break;
        case 'channel_update':
          onChannelUpdate(data.data);
          break;
        default:
          console.log('Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket connection closed');
  };

  return ws;
}

// ===== Presence =====

/**
 * Update user presence status
 */
export async function updatePresence(status: 'online' | 'away' | 'offline'): Promise<void> {
  await axios.post(`${API_BASE}/team/presence`, { status });
}

// ===== Mesh Network Status =====

/**
 * Get P2P mesh peers
 */
export async function getP2PMeshPeers(): Promise<any[]> {
  const response = await axios.get(`${API_BASE}/p2p/peers`);
  return response.data.peers || [];
}

/**
 * Get P2P mesh status
 */
export async function getP2PMeshStatus(): Promise<any> {
  const response = await axios.get(`${API_BASE}/p2p/status`);
  return response.data;
}
