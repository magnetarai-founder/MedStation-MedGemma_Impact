import { useEffect, useMemo, useRef, useState } from 'react'
import { X, Wifi, Send, Loader2 } from 'lucide-react'

interface Peer {
  id: string
  name: string
  connected: boolean
}

interface ShareToDeviceModalProps {
  isOpen: boolean
  onClose: () => void
  files: { id?: string; name: string; size: number; blob?: Blob }[]
}

/**
 * Minimal Share-to-Device modal (skeleton).
 *
 * - Lists discovered peers (placeholder API)
 * - Allows selecting a peer and initiating a stub transfer flow
 * - Hooks are ready to wire chunked upload via /api/v1/p2p/transfer/* endpoints
 */
export function ShareToDeviceModal({ isOpen, onClose, files }: ShareToDeviceModalProps) {
  const [peers, setPeers] = useState<Peer[]>([])
  const [selectedPeerId, setSelectedPeerId] = useState<string>('')
  const [busy, setBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!isOpen) return
    // Placeholder discovery – replace with real peers API
    ;(async () => {
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
      }
    })()
  }, [isOpen])

  const totalSize = useMemo(() => files.reduce((s, f) => s + (f.size || 0), 0), [files])

  const onShare = async () => {
    if (!selectedPeerId || files.length === 0) return
    setBusy(true)
    const ac = new AbortController()
    abortRef.current = ac
    try {
      // Skeleton: this is where chunked transfer init/upload/commit will go.
      // For now, simulate with a short delay.
      await new Promise((r) => setTimeout(r, 800))
      onClose()
    } catch (e) {
      console.error('Share failed:', e)
    } finally {
      setBusy(false)
    }
  }

  const onCancel = () => {
    abortRef.current?.abort()
    setBusy(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-[680px] max-w-[95vw] rounded-xl shadow-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Wifi className="w-5 h-5" />
            <h3 className="text-base font-semibold">Share to Nearby Device</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
            Select a device and click Share. Transfers work offline over local network.
          </div>

          {/* Peers list */}
          <div className="max-h-52 overflow-auto border rounded mb-4">
            {peers.length === 0 ? (
              <div className="p-3 text-sm text-gray-500">No peers discovered. Ensure both devices are on the same network and P2P is enabled.</div>
            ) : (
              peers.map((p) => (
                <label key={p.id} className="flex items-center gap-3 px-3 py-2 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                  <input
                    type="radio"
                    name="peer"
                    value={p.id}
                    checked={selectedPeerId === p.id}
                    onChange={() => setSelectedPeerId(p.id)}
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{p.name || p.id}</div>
                    <div className="text-xs text-gray-500">{p.connected ? 'Online' : 'Unknown status'}</div>
                  </div>
                </label>
              ))
            )}
          </div>

          {/* Files summary */}
          <div className="text-xs text-gray-600 dark:text-gray-400 mb-4">
            {files.length} file(s), total {(totalSize / (1024 * 1024)).toFixed(2)} MB
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2">
            <button onClick={onCancel} className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50 dark:bg-gray-900 dark:border-gray-700">
              Cancel
            </button>
            <button
              onClick={onShare}
              disabled={!selectedPeerId || files.length === 0 || busy}
              className="px-3 py-1.5 rounded text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>{busy ? 'Sharing…' : 'Share'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

