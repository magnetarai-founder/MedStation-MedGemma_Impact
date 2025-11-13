import { useEffect, useState } from 'react'
import { authFetch } from '../lib/api'

interface TokenMeterProps {
  sessionId: string
  refreshOn?: any // changes to this prop will trigger a refresh
  onNearLimit?: () => void // callback when token usage >= 85%
}

interface TokenCountResponse {
  session_id: string
  total_tokens: number
  max_tokens: number
  percentage: number
  cached?: boolean
}

export function TokenMeter({ sessionId, refreshOn, onNearLimit }: TokenMeterProps) {
  const [data, setData] = useState<TokenCountResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [nearLimitTriggered, setNearLimitTriggered] = useState(false)

  const fetchCount = async (signal?: AbortSignal) => {
    if (!sessionId) return
    setLoading(true)
    try {
      const res = await authFetch(`/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/token-count`, { signal })
      if (res.ok) {
        const json = await res.json()
        setData(json)

        // Check near-limit threshold (85%)
        const percentage = json.percentage || 0
        if (percentage >= 85 && !nearLimitTriggered && onNearLimit) {
          setNearLimitTriggered(true)
          onNearLimit()
        } else if (percentage < 85) {
          // Reset flag if we drop back below threshold
          setNearLimitTriggered(false)
        }
      }
    } catch (e) {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    fetchCount(controller.signal)
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  useEffect(() => {
    const controller = new AbortController()
    fetchCount(controller.signal)
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshOn])

  const pct = Math.min(100, Math.max(0, (data?.percentage ?? 0) * 100))
  const color = pct < 70 ? 'bg-green-500' : pct < 90 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="mt-1" title={data ? `${data.total_tokens} / ${data.max_tokens} tokens${data.cached ? ' (cached)' : ''}` : 'Counting tokens...'}>
      <div className="w-48 h-1.5 bg-gray-200 dark:bg-gray-800 rounded overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${loading ? 0 : pct}%` }}
        />
      </div>
    </div>
  )
}

