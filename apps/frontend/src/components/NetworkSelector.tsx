/**
 * Network Selector
 *
 * macOS WiFi-style dropdown for selecting network mode:
 * - Solo Mode (offline, local only)
 * - LAN Discovery (find local laptops, central hub model)
 * - P2P Mesh (connect to peers anywhere via libp2p)
 *
 * Built for the persecuted Church - no cloud, no central servers.
 * "For such a time as this." - Esther 4:14
 */

import { useState, useRef, useEffect } from 'react'
import { Globe, Wifi, Users, Check, Plus, Share2, Loader2 } from 'lucide-react'

type NetworkMode = 'solo' | 'lan' | 'p2p'

interface LANDevice {
  id: string
  name: string
  ip: string
  isHub: boolean
}

interface P2PPeer {
  id: string
  name: string
  location?: string
  connected: boolean
}

interface NetworkSelectorProps {
  mode: NetworkMode
  onModeChange: (mode: NetworkMode) => void
}

export function NetworkSelector({ mode, onModeChange }: NetworkSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [lanDevices, setLanDevices] = useState<LANDevice[]>([])
  const [p2pPeers, setP2pPeers] = useState<P2PPeer[]>([])
  const [showAddPeer, setShowAddPeer] = useState(false)
  const [peerCode, setPeerCode] = useState('')
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected')
  const [isHub, setIsHub] = useState(false)
  const [hubPort, setHubPort] = useState<number | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setShowAddPeer(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Scan for LAN devices when opening LAN mode
  const handleScanLAN = async () => {
    setIsScanning(true)

    try {
      // Start discovery
      await fetch('/api/v1/lan/discovery/start', { method: 'POST' })

      // Wait a moment for devices to be discovered
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Fetch discovered devices
      const response = await fetch('/api/v1/lan/devices')
      const data = await response.json()

      if (data.status === 'success') {
        setLanDevices(data.devices.map((d: any) => ({
          id: d.id,
          name: d.name,
          ip: d.ip,
          isHub: d.is_hub
        })))
      }
    } catch (error) {
      console.error('Failed to scan LAN:', error)
      // No fallback - show empty state
      setLanDevices([])
    } finally {
      setIsScanning(false)
    }
  }

  // Load P2P peers
  const handleLoadP2PPeers = async () => {
    try {
      // Start P2P mesh if not already started
      await fetch('/api/v1/p2p/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: 'ElohimOS User',
          device_name: window.location.hostname || 'My Device'
        })
      })

      // Fetch connected peers
      const response = await fetch('/api/v1/p2p/peers')
      const data = await response.json()

      if (data.status === 'success') {
        setP2pPeers(data.peers)
      }
    } catch (error) {
      console.error('Failed to load P2P peers:', error)
      // No fallback - show empty state
      setP2pPeers([])
    }
  }

  // Handle mode selection
  const handleModeSelect = (newMode: NetworkMode) => {
    onModeChange(newMode)

    if (newMode === 'lan') {
      handleScanLAN()
    } else if (newMode === 'p2p') {
      handleLoadP2PPeers()
    }
  }

  // Join LAN device
  const handleJoinLAN = async (device: LANDevice) => {
    console.log('Joining LAN device:', device)
    setConnectionStatus('connecting')

    try {
      const response = await fetch('/api/v1/lan/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: device.id })
      })

      const data = await response.json()

      if (data.status === 'success') {
        console.log('Successfully joined:', data.message)
        setConnectionStatus('connected')
        setIsHub(false)
      } else {
        setConnectionStatus('disconnected')
      }
    } catch (error) {
      console.error('Failed to join device:', error)
      setConnectionStatus('disconnected')
    }
  }

  // Host LAN network
  const handleHostLAN = async () => {
    console.log('Hosting LAN network as hub')
    setConnectionStatus('connecting')

    try {
      const hostname = window.location.hostname || 'ElohimOS'

      const response = await fetch('/api/v1/lan/hub/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          port: 8765,
          device_name: hostname
        })
      })

      const data = await response.json()

      if (data.status === 'success') {
        console.log('Hub started:', data.hub_info)
        setConnectionStatus('connected')
        setIsHub(true)
        setHubPort(data.hub_info?.port || 8765)
      } else {
        setConnectionStatus('disconnected')
      }
    } catch (error) {
      console.error('Failed to start hub:', error)
      setConnectionStatus('disconnected')
    }
  }

  // Add P2P peer
  const handleAddPeer = async () => {
    if (!peerCode.trim()) return

    try {
      const response = await fetch('/api/v1/p2p/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: peerCode })
      })

      const data = await response.json()

      if (data.status === 'success') {
        console.log('Successfully connected:', data.message)
        // Reload peers
        await handleLoadP2PPeers()
      }
    } catch (error) {
      console.error('Failed to connect to peer:', error)
    } finally {
      setPeerCode('')
      setShowAddPeer(false)
    }
  }

  // Share connection code
  const handleShareCode = async () => {
    try {
      const response = await fetch('/api/v1/p2p/connection-code', {
        method: 'POST'
      })

      const data = await response.json()

      if (data.status === 'success') {
        await navigator.clipboard.writeText(data.code)
        console.log('Connection code copied:', data.code)
        alert(`Connection code copied: ${data.code}\n\nShare this with others to connect!`)
      }
    } catch (error) {
      console.error('Failed to generate connection code:', error)
      // Fallback
      const myCode = 'OMNI-' + Math.random().toString(36).substr(2, 8).toUpperCase()
      await navigator.clipboard.writeText(myCode)
      console.log('Connection code copied:', myCode)
    }
  }

  // Get status text
  const getStatusText = () => {
    switch (mode) {
      case 'solo':
        return 'Offline'
      case 'lan':
        if (connectionStatus === 'connecting') return 'Connecting...'
        if (connectionStatus === 'connected') {
          return isHub ? `Hub (${lanDevices.length} devices)` : 'Connected'
        }
        return isScanning ? 'Scanning...' : `${lanDevices.length} found`
      case 'p2p':
        const connected = p2pPeers.filter(p => p.connected).length
        if (connectionStatus === 'connecting') return 'Connecting...'
        return `${connected} peer${connected !== 1 ? 's' : ''}`
      default:
        return 'Offline'
    }
  }

  // Get icon color based on mode and connection status
  const getIconColor = () => {
    if (connectionStatus === 'connecting') return 'text-yellow-500 animate-pulse'
    if (connectionStatus === 'connected') {
      switch (mode) {
        case 'lan':
          return 'text-blue-500'
        case 'p2p':
          return 'text-green-500'
        default:
          return 'text-gray-400'
      }
    }
    return 'text-gray-400'
  }

  // Get status badge
  const getStatusBadge = () => {
    if (mode === 'solo') return null

    if (connectionStatus === 'connecting') {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
          <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse"></span>
          Connecting
        </span>
      )
    }

    if (connectionStatus === 'connected') {
      if (mode === 'lan' && isHub) {
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
            Hub:{hubPort}
          </span>
        )
      }
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
          Connected
        </span>
      )
    }

    return null
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Globe Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all"
        title="Network"
      >
        <Globe className={`w-5 h-5 ${getIconColor()}`} />
        <div className="flex flex-col items-start gap-0.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">{getStatusText()}</span>
          {getStatusBadge()}
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden">

          {/* Mode Selection */}
          {!showAddPeer && (
            <>
              <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Network Mode
                </div>

                {/* Solo Mode */}
                <button
                  onClick={() => handleModeSelect('solo')}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg mb-1 transition-all ${
                    mode === 'solo'
                      ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5 flex-1 min-w-0">
                    <div className="w-2 h-2 rounded-full bg-gray-400 flex-shrink-0"></div>
                    <div className="text-left flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Solo Mode
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 italic leading-relaxed">
                        "God's man or woman, in the center of God's will, is immortal until God is done with him."
                      </div>
                    </div>
                  </div>
                  {mode === 'solo' && <Check className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0" />}
                </button>

                {/* LAN Discovery */}
                <button
                  onClick={() => handleModeSelect('lan')}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg mb-1 transition-all ${
                    mode === 'lan'
                      ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        LAN Discovery
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Find local devices
                      </div>
                    </div>
                  </div>
                  {mode === 'lan' && <Check className="w-4 h-4 text-primary-600 dark:text-primary-400" />}
                </button>

                {/* P2P Mesh */}
                <button
                  onClick={() => handleModeSelect('p2p')}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all ${
                    mode === 'p2p'
                      ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        P2P Mesh
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Connect anywhere
                      </div>
                    </div>
                  </div>
                  {mode === 'p2p' && <Check className="w-4 h-4 text-primary-600 dark:text-primary-400" />}
                </button>
              </div>

              {/* LAN Devices */}
              {mode === 'lan' && (
                <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Local Devices
                    </div>
                    {isScanning && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
                  </div>

                  {lanDevices.length === 0 ? (
                    <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-3">
                      {isScanning ? 'Scanning network...' : 'No devices found'}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {lanDevices.map((device) => (
                        <div
                          key={device.id}
                          className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                        >
                          <div className="flex items-center gap-2">
                            <Wifi className="w-4 h-4 text-blue-500" />
                            <div>
                              <div className="text-sm text-gray-900 dark:text-gray-100">
                                {device.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {device.ip} {device.isHub && '• Hub'}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => handleJoinLAN(device)}
                            className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                          >
                            Join
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={handleHostLAN}
                    className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    <Wifi className="w-4 h-4" />
                    <span>Host Network (Be Hub)</span>
                  </button>
                </div>
              )}

              {/* P2P Peers */}
              {mode === 'p2p' && (
                <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                  <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Connected Peers
                  </div>

                  {p2pPeers.length === 0 ? (
                    <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-3">
                      No peers connected
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {p2pPeers.map((peer) => (
                        <div
                          key={peer.id}
                          className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                        >
                          <div className="flex items-center gap-2">
                            <Users className="w-4 h-4 text-green-500" />
                            <div>
                              <div className="text-sm text-gray-900 dark:text-gray-100">
                                {peer.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {peer.location}
                              </div>
                            </div>
                          </div>
                          <div className={`w-2 h-2 rounded-full ${peer.connected ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => setShowAddPeer(true)}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-medium transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Peer</span>
                    </button>
                    <button
                      onClick={handleShareCode}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-medium transition-colors"
                    >
                      <Share2 className="w-3.5 h-3.5" />
                      <span>Share Code</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Add Peer Dialog */}
          {showAddPeer && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  Add Peer
                </div>
                <button
                  onClick={() => setShowAddPeer(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Connection Code
                  </label>
                  <input
                    type="text"
                    value={peerCode}
                    onChange={(e) => setPeerCode(e.target.value)}
                    placeholder="OMNI-XXXXXXXX"
                    className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddPeer()
                      if (e.key === 'Escape') setShowAddPeer(false)
                    }}
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowAddPeer(false)}
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddPeer}
                    disabled={!peerCode.trim()}
                    className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                  >
                    Connect
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
