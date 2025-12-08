import { useEffect, useState } from 'react'
import { RefreshCw, Wifi } from 'lucide-react'

interface Peer {
  id: string
  name: string
  connected: boolean
}

interface NearbyDevicesPanelProps {
  onSelectPeer?: (peer: Peer) => void
}

/**
 * Minimal Nearby Devices panel (skeleton) to embed in VaultWorkspace sidebar.
 */
export function NearbyDevicesPanel({ onSelectPeer }: NearbyDevicesPanelProps) {
  const [peers, setPeers] = useState<Peer[]>([])
  const [loading, setLoading] = useState(false)

  const loadPeers = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/p2p/peers')
      if (res.ok) {
        const data = await res.json().catch(() => ({} as any))
        const list: Peer[] = (data?.peers || []).map((p: any) => ({ id: p.id, name: p.name, connected: !!p.connected }))
        setPeers(list)
      } else {
        setPeers([])
      }
    } catch {
      setPeers([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPeers()
  }, [])

  return (
    <div className="p-3 border rounded bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Wifi className="w-4 h-4" />
          <h4 className="text-sm font-medium">Nearby Devices</h4>
        </div>
        <button onClick={loadPeers} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800" title="Refresh">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {peers.length === 0 ? (
        <div className="text-xs text-gray-500">No peers discovered.</div>
      ) : (
        <div className="space-y-1 max-h-48 overflow-auto">
          {peers.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectPeer?.(p)}
              className="w-full text-left px-2 py-1 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <div className="text-xs font-medium">{p.name || p.id}</div>
              <div className="text-[10px] text-gray-500">{p.connected ? 'Online' : 'Unknown status'}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

