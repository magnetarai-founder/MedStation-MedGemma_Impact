/**
 * User Identity Store
 *
 * Manages user profile for ElohimOS.
 * Single-user per device model for offline-first operation.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

export interface UserProfile {
  user_id: string
  display_name: string
  device_name: string
  created_at: string
  avatar_color?: string
  bio?: string
  role?: string
  role_changed_at?: string
  role_changed_by?: string
  job_role?: string
}

interface UserStore {
  user: UserProfile | null
  isLoading: boolean
  error: string | null

  // Actions
  fetchUser: () => Promise<void>
  updateUser: (updates: Partial<UserProfile>) => Promise<void>
  resetUser: () => Promise<void>

  // Computed
  getUserId: () => string
}

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      error: null,

      fetchUser: async () => {
        set({ isLoading: true, error: null })
        try {
          // Use /api/v1/auth/me to get user from JWT token (works for both regular users and founder account)
          const response = await axios.get('/api/v1/auth/me')
          set({ user: response.data, isLoading: false })
        } catch (error: any) {
          set({
            error: error.message || 'Failed to fetch user',
            isLoading: false
          })
          console.error('Failed to fetch user:', error)
        }
      },

      updateUser: async (updates) => {
        set({ isLoading: true, error: null })
        try {
          const response = await axios.put('/api/v1/users/me', updates)
          set({ user: response.data, isLoading: false })
        } catch (error: any) {
          set({
            error: error.message || 'Failed to update user',
            isLoading: false
          })
          console.error('Failed to update user:', error)
        }
      },

      resetUser: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await axios.post('/api/v1/users/reset')
          set({ user: response.data.user, isLoading: false })
        } catch (error: any) {
          set({
            error: error.message || 'Failed to reset user',
            isLoading: false
          })
          console.error('Failed to reset user:', error)
        }
      },

      getUserId: () => {
        const user = get().user
        if (!user) {
          // Fetch user if not loaded
          get().fetchUser()
          return 'loading'
        }
        return user.user_id
      },
    }),
    {
      name: 'elohimos.user',
      // Persist user data
      partialize: (state) => ({
        user: state.user,
      }),
    }
  )
)
