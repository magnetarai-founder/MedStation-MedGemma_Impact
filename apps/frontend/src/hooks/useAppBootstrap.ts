import { useState, useEffect } from 'react'
import { useSessionStore } from '@/stores/sessionStore'
import { useUserStore } from '@/stores/userStore'
import { api } from '@/lib/api'

export type AuthState = 'welcome' | 'checking' | 'setup_needed' | 'authenticated'

export function useAppBootstrap() {
  const { sessionId, setSessionId, clearSession } = useSessionStore()
  const { fetchUser } = useUserStore()

  const [isLoading, setIsLoading] = useState(true)
  const [authState, setAuthState] = useState<AuthState>('welcome')
  const [userSetupComplete, setUserSetupComplete] = useState<boolean | null>(null)
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if we have a stored token
        const token = localStorage.getItem('auth_token')

        if (token) {
          // Token exists - validate it by fetching user
          try {
            await fetchUser()
            const userStr = localStorage.getItem('user')
            const user = userStr ? JSON.parse(userStr) : null
            const userId = user?.user_id || user?.id || ''

            setCurrentUserId(userId)
            setAuthState('checking') // Will check per-user setup next
          } catch (error) {
            // Token invalid - clear and show welcome
            localStorage.removeItem('auth_token')
            localStorage.removeItem('user')
            setAuthState('welcome')
            setIsLoading(false)
          }
        } else {
          // No token - show welcome
          setAuthState('welcome')
          setIsLoading(false)
        }
      } catch (error) {
        console.error('Failed to check auth:', error)
        setAuthState('welcome')
        setIsLoading(false)
      }
    }

    checkAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // fetchUser is a stable Zustand action, no need to include in deps

  // Check per-user setup status after authentication
  useEffect(() => {
    if (authState !== 'checking') return

    const checkUserSetup = async () => {
      try {
        // Check if this is the founder account (bypass setup wizard)
        const userStr = localStorage.getItem('user')
        const user = userStr ? JSON.parse(userStr) : null
        const isFounder = user?.role === 'founder_rights' || user?.username === 'elohim_founder'

        if (isFounder) {
          // Founder account always goes straight to authenticated
          setUserSetupComplete(true)
          setAuthState('authenticated')
          setIsLoading(false)
          return
        }

        // Check per-user setup status for regular users
        const response = await fetch('/api/v1/users/me/setup/status', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        })

        if (response.ok) {
          const status = await response.json()
          setUserSetupComplete(status.user_setup_completed)

          if (status.user_setup_completed) {
            setAuthState('authenticated')
          } else {
            // Setup incomplete - change state so we exit loading screen and show wizard
            setAuthState('setup_needed')
          }
        } else {
          // If status check fails, assume setup incomplete (show wizard)
          setUserSetupComplete(false)
          setAuthState('setup_needed')
        }
      } catch (error) {
        console.error('Failed to check user setup status:', error)
        // If check fails, assume setup incomplete (show wizard to be safe)
        setUserSetupComplete(false)
        setAuthState('setup_needed')
      } finally {
        setIsLoading(false)
      }
    }

    checkUserSetup()
  }, [authState])

  // Initialize user and session after authentication
  useEffect(() => {
    if (authState !== 'authenticated') return

    const initApp = async () => {
      try {
        // Fetch or create user identity
        await fetchUser()

        // Create session
        const response = await api.createSession()
        setSessionId(response.session_id)
      } catch (error) {
        console.error('Failed to initialize app:', error)
      }
    }

    initApp()

    // Cleanup on unmount
    return () => {
      if (sessionId) {
        api.deleteSession(sessionId).catch(console.error)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState]) // fetchUser and setSessionId are stable Zustand actions, sessionId handled internally

  return {
    authState,
    setAuthState,
    isLoading,
    userSetupComplete,
    setUserSetupComplete,
    sessionId,
    currentUserId,
    setCurrentUserId,
  }
}
