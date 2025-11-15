import { useEffect, useRef, useState } from 'react'
import * as Y from 'yjs'

/**
 * Hook to bind a Y.Text to a textarea value with bidirectional sync.
 *
 * Handles Yjs events to update local state and applies local changes back to Y.Text.
 *
 * @param ytext Y.Text instance to bind
 * @returns value and onChange handler for textarea
 */
export function useYTextBinding(ytext: Y.Text | null) {
  const [value, setValue] = useState<string>('')
  const isApplyingRef = useRef(false)

  useEffect(() => {
    if (!ytext) return

    // Initialize local state from Y.Text
    setValue(ytext.toString())

    const observer = () => {
      // Avoid reflecting our own changes redundantly
      if (isApplyingRef.current) return
      setValue(ytext.toString())
    }

    ytext.observe(observer)
    return () => ytext.unobserve(observer)
  }, [ytext])

  const onChange = (next: string) => {
    setValue(next)
    if (!ytext) return

    isApplyingRef.current = true
    // Replace content atomically (simple approach for MVP)
    // For large docs, use delta-based operations
    ytext.delete(0, ytext.length)
    ytext.insert(0, next)
    isApplyingRef.current = false
  }

  return { value, onChange }
}
