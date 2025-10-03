import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NavigationStore {
  activeTab: 'chat' | 'editor' | 'queries'
  setActiveTab: (tab: 'chat' | 'editor' | 'queries') => void
}

export const useNavigationStore = create<NavigationStore>()(
  persist(
    (set) => ({
      activeTab: 'editor',
      setActiveTab: (tab) => set({ activeTab: tab }),
    }),
    {
      name: 'ns.navigation',
    }
  )
)
