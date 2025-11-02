/**
 * User Identity Store
 *
 * Manages user profile for ElohimOS.
 * Single-user per device model for offline-first operation.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

// Create axios instance with auth interceptor
const apiClient = axios.create({
  baseURL: '/',
})

// Add request interceptor to attach JWT token
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

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
          const authResponse = await apiClient.get('/api/v1/auth/me')
          const authData = authResponse.data

          console.log('userStore.fetchUser - authData:', authData)

          // If this is the founder account, create a minimal profile from auth data
          if (authData.role === 'founder_rights') {
            set({
              user: {
                user_id: authData.user_id,
                display_name: authData.username,
                device_name: authData.device_id,
                created_at: new Date().toISOString(),
                role: authData.role,
                avatar_color: '#8b5cf6', // Purple for founder
                bio: 'System Founder Account'
              },
              isLoading: false,
              error: null
            })
          } else {
            // For regular users, get full profile from /api/v1/users/me
            const profileResponse = await apiClient.get('/api/v1/users/me')
            set({ user: { ...profileResponse.data, role: authData.role }, isLoading: false, error: null })
          }
        } catch (error: any) {
          console.error('Failed to fetch user:', error)
          console.error('Error response:', error.response?.data)
          set({
            error: error.response?.data?.detail || error.message || 'Failed to fetch user',
            isLoading: false,
            user: null
          })
        }
      },

      updateUser: async (updates) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.put('/api/v1/users/me', updates)
          set({ user: response.data, isLoading: false, error: null })
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || error.message || 'Failed to update user',
            isLoading: false
          })
          console.error('Failed to update user:', error)
        }
      },

      resetUser: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.post('/api/v1/users/reset')
          set({ user: response.data.user, isLoading: false, error: null })
        } catch (error: any) {
          set({
            error: error.response?.data?.detail || error.message || 'Failed to reset user',
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
