/**
 * P2P Peer Discovery & Connection UI
 *
 * Allows users to:
 * - See discovered peers on the mesh
 * - Generate connection codes for pairing
 * - Connect to peers using codes
 * - View peer status and details
 */

import { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  Users,
  Wifi,
  WifiOff,
  QrCode,
  Copy,
  Check,
  RefreshCw,
  UserPlus,
  X,
  Loader2
} from 'lucide-react';
import {
  getDiscoveredPeers,
  generateConnectionCode,
  connectWithCode,
  connectToPeer,
  type Peer,
  type ConnectionCode
} from '../lib/p2pApi';

interface P2PPeerDiscoveryProps {
  isOpen: boolean;
  onClose: () => void;
}

export function P2PPeerDiscovery({ isOpen, onClose }: P2PPeerDiscoveryProps) {
  const [peers, setPeers] = useState<Peer[]>([]);
  const [connectionCode, setConnectionCode] = useState<ConnectionCode | null>(null);
  const [manualCode, setManualCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showManualConnect, setShowManualConnect] = useState(false);

  // Load peers on mount
  useEffect(() => {
    if (isOpen) {
      loadPeers();
      // Refresh peers every 5 seconds
      const interval = setInterval(loadPeers, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const loadPeers = async () => {
    setIsLoading(true);
    try {
      const discoveredPeers = await getDiscoveredPeers();
      setPeers(discoveredPeers);
    } catch (error) {
      console.error('Failed to load peers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateCode = async () => {
    setIsGenerating(true);
    try {
      const code = await generateConnectionCode();
      setConnectionCode(code);
      toast.success('Connection code generated');
    } catch (error) {
      console.error('Failed to generate code:', error);
      toast.error('Failed to generate connection code');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyCode = async () => {
    if (!connectionCode) return;

    try {
      await navigator.clipboard.writeText(connectionCode.code);
      setCopied(true);
      toast.success('Code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy code');
    }
  };

  const handleConnectWithCode = async () => {
    if (!manualCode.trim()) return;

    setIsConnecting(true);
    try {
      const result = await connectWithCode(manualCode.trim());
      toast.success(`Connected to peer ${result.peer_id.substring(0, 8)}`);
      setManualCode('');
      setShowManualConnect(false);
      loadPeers();
    } catch (error: any) {
      console.error('Failed to connect:', error);
      toast.error(error.response?.data?.message || 'Failed to connect to peer');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleConnectToPeer = async (peer: Peer) => {
    try {
      // Use first multiaddr if available
      const multiaddr = peer.public_key || '';
      await connectToPeer(peer.peer_id, multiaddr);
      toast.success(`Connected to ${peer.display_name}`);
      loadPeers();
    } catch (error) {
      console.error('Failed to connect to peer:', error);
      toast.error('Failed to connect to peer');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              P2P Mesh Network
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
          >
            <X size={20} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Connection Code Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                Share Connection Code
              </h3>
              <button
                onClick={handleGenerateCode}
                disabled={isGenerating}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <QrCode className="w-4 h-4" />
                    Generate Code
                  </>
                )}
              </button>
            </div>

            {connectionCode && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                    Share this code with others:
                  </span>
                  <button
                    onClick={handleCopyCode}
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
                <div className="font-mono text-2xl font-bold text-blue-900 dark:text-blue-100 text-center py-2">
                  {connectionCode.code}
                </div>
                <p className="text-xs text-blue-600 dark:text-blue-400 text-center mt-2">
                  Code expires in 15 minutes
                </p>
              </div>
            )}
          </div>

          {/* Manual Connect Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                Connect to Peer
              </h3>
              {!showManualConnect && (
                <button
                  onClick={() => setShowManualConnect(true)}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <UserPlus className="w-4 h-4" />
                  Enter Code
                </button>
              )}
            </div>

            {showManualConnect && (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={manualCode}
                    onChange={(e) => setManualCode(e.target.value.toUpperCase())}
                    placeholder="OMNI-XXXX-XXXX"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && manualCode.trim()) {
                        handleConnectWithCode();
                      }
                      if (e.key === 'Escape') {
                        setShowManualConnect(false);
                        setManualCode('');
                      }
                    }}
                  />
                  <button
                    onClick={handleConnectWithCode}
                    disabled={!manualCode.trim() || isConnecting}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isConnecting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      'Connect'
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setShowManualConnect(false);
                      setManualCode('');
                    }}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Discovered Peers Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                Discovered Peers ({peers.length})
              </h3>
              <button
                onClick={loadPeers}
                disabled={isLoading}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
                title="Refresh"
              >
                <RefreshCw
                  className={`w-4 h-4 text-gray-600 dark:text-gray-400 ${
                    isLoading ? 'animate-spin' : ''
                  }`}
                />
              </button>
            </div>

            {peers.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Wifi className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No peers discovered yet</p>
                <p className="text-xs mt-1">
                  Make sure other devices are on the same network
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {peers.map((peer) => (
                  <div
                    key={peer.peer_id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div
                        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                          peer.status === 'online'
                            ? 'bg-green-500'
                            : peer.status === 'away'
                            ? 'bg-yellow-500'
                            : 'bg-gray-400'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                          {peer.display_name}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {peer.device_name}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 font-mono">
                        {peer.status === 'online' ? (
                          <Wifi className="w-3 h-3 text-green-600" />
                        ) : (
                          <WifiOff className="w-3 h-3 text-gray-400" />
                        )}
                        {peer.peer_id.substring(0, 8)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors font-medium text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
