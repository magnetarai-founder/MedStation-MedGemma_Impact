/**
 * useProfileData Hook
 *
 * Manages user data fetching and provides user state
 */

import { useEffect, useRef } from 'react'
import { useUserStore } from '@/stores/userStore'

export function useProfileData() {
  const { user, fetchUser, isLoading } = useUserStore()
  const hasFetchedRef = useRef(false)

  // Auto-fetch user on mount if not loaded (run only once)
  useEffect(() => {
    if (!user && !isLoading && !hasFetchedRef.current) {
      hasFetchedRef.current = true
      fetchUser()
    }
  }, [user, isLoading, fetchUser])

  return {
    user,
    isLoading,
    fetchUser,
  }
}
