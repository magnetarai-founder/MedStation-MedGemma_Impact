/**
 * useP2PChat Hook
 *
 * Manages P2P team chat state and real-time updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'react-hot-toast';
import {
  initializeP2P,
  getP2PStatus,
  getDiscoveredPeers,
  getChannels,
  getMessages,
  sendMessage,
  createChannel,
  createDM,
  connectP2PWebSocket,
  type Peer,
  type Channel,
  type Message,
  type P2PStatus
} from '../lib/p2pApi';

export function useP2PChat(mode: 'solo' | 'p2p') {
  const [status, setStatus] = useState<P2PStatus | null>(null);
  const [peers, setPeers] = useState<Peer[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // Initialize P2P service when mode changes to p2p
  useEffect(() => {
    if (mode === 'p2p') {
      initializeP2PService();
    } else {
      cleanup();
    }

    return () => cleanup();
  }, [mode]);

  const initializeP2PService = useCallback(async () => {
    if (isInitializing) return;

    setIsInitializing(true);
    setError(null);

    try {
      // Get user info from localStorage
      const user = JSON.parse(localStorage.getItem('user') || '{}');
      const displayName = user.username || 'Anonymous';
      const deviceName = `${displayName}'s Device`;

      // Initialize P2P service
      console.log('Initializing P2P service...');
      const statusResponse = await initializeP2P(displayName, deviceName);
      setStatus(statusResponse);

      // Load initial data
      await Promise.all([
        loadPeers(),
        loadChannels()
      ]);

      // Connect WebSocket for real-time updates
      connectWebSocket();

      toast.success('P2P mesh network initialized');
    } catch (err: any) {
      console.error('Failed to initialize P2P:', err);
      setError(err.message || 'Failed to initialize P2P service');
      toast.error('Failed to start P2P mesh network');
    } finally {
      setIsInitializing(false);
    }
  }, [isInitializing]);

  const loadPeers = useCallback(async () => {
    try {
      const discoveredPeers = await getDiscoveredPeers();
      setPeers(discoveredPeers);
    } catch (err) {
      console.error('Failed to load peers:', err);
    }
  }, []);

  const loadChannels = useCallback(async () => {
    try {
      const channelList = await getChannels();
      setChannels(channelList);
    } catch (err) {
      console.error('Failed to load channels:', err);
    }
  }, []);

  const loadMessagesForChannel = useCallback(async (channelId: string) => {
    try {
      const channelMessages = await getMessages(channelId);
      setMessages(prev => ({
        ...prev,
        [channelId]: channelMessages
      }));
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  }, []);

  const handleSendMessage = useCallback(async (channelId: string, content: string) => {
    try {
      const message = await sendMessage(channelId, content);

      // Optimistically add message to local state
      setMessages(prev => ({
        ...prev,
        [channelId]: [...(prev[channelId] || []), message]
      }));

      return message;
    } catch (err: any) {
      console.error('Failed to send message:', err);
      toast.error('Failed to send message');
      throw err;
    }
  }, []);

  const handleCreateChannel = useCallback(async (
    name: string,
    type: 'public' | 'private',
    description?: string
  ) => {
    try {
      const channel = await createChannel(name, type, description);
      setChannels(prev => [...prev, channel]);
      toast.success(`Channel #${name} created`);
      return channel;
    } catch (err: any) {
      console.error('Failed to create channel:', err);
      toast.error('Failed to create channel');
      throw err;
    }
  }, []);

  const handleCreateDM = useCallback(async (peerId: string) => {
    try {
      const channel = await createDM(peerId);
      setChannels(prev => [...prev, channel]);
      return channel;
    } catch (err: any) {
      console.error('Failed to create DM:', err);
      toast.error('Failed to create direct message');
      throw err;
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      const ws = connectP2PWebSocket(
        // On new message
        (message) => {
          setMessages(prev => ({
            ...prev,
            [message.channel_id]: [...(prev[message.channel_id] || []), message]
          }));
        },
        // On peer update
        (peer) => {
          setPeers(prev => {
            const index = prev.findIndex(p => p.peer_id === peer.peer_id);
            if (index >= 0) {
              const newPeers = [...prev];
              newPeers[index] = peer;
              return newPeers;
            } else {
              return [...prev, peer];
            }
          });
        },
        // On channel update
        (channel) => {
          setChannels(prev => {
            const index = prev.findIndex(c => c.id === channel.id);
            if (index >= 0) {
              const newChannels = [...prev];
              newChannels[index] = channel;
              return newChannels;
            } else {
              return [...prev, channel];
            }
          });
        }
      );

      wsRef.current = ws;

      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting in 3s...');
        setTimeout(() => {
          if (mode === 'p2p') {
            connectWebSocket();
          }
        }, 3000);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
    }
  }, [mode]);

  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setPeers([]);
    setChannels([]);
    setMessages({});
    setStatus(null);
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const currentStatus = await getP2PStatus();
      setStatus(currentStatus);
    } catch (err) {
      console.error('Failed to refresh status:', err);
    }
  }, []);

  return {
    // State
    status,
    peers,
    channels,
    messages,
    isInitializing,
    error,

    // Actions
    sendMessage: handleSendMessage,
    createChannel: handleCreateChannel,
    createDM: handleCreateDM,
    loadMessages: loadMessagesForChannel,
    refreshPeers: loadPeers,
    refreshChannels: loadChannels,
    refreshStatus,
    retry: initializeP2PService
  };
}
