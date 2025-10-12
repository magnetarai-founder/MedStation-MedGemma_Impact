import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type NavTab = 'team' | 'chat' | 'editor' | 'database'

export interface NavItem {
  id: NavTab
  label: string
  locked?: boolean // Settings is always locked
}

interface NavigationStore {
  activeTab: NavTab
  setActiveTab: (tab: NavTab) => void

  // Custom navigation order (excludes Settings which is always at bottom)
  navOrder: Array<NavItem['id']>
  setNavOrder: (order: Array<NavItem['id']>) => void
}

// Default navigation order
const defaultNavOrder: Array<NavItem['id']> = [
  'chat',      // AI Chat first
  'database',  // Database second
  'editor',    // Code Editor third
  'team'       // Team Chat last
]

export const useNavigationStore = create<NavigationStore>()(
  persist(
    (set, get) => ({
      activeTab: 'database',
      setActiveTab: (tab) => set({ activeTab: tab }),

      navOrder: defaultNavOrder,
      setNavOrder: (order) => set({ navOrder: order }),
    }),
    {
      name: 'ns.navigation',
      // Migration to ensure all tabs are present
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Check if navOrder has all required tabs
          const requiredTabs: NavTab[] = ['team', 'chat', 'editor', 'database']
          const missingTabs = requiredTabs.filter(tab => !state.navOrder.includes(tab))

          if (missingTabs.length > 0) {
            // Reset to default order if any tabs are missing
            console.log('Resetting navigation order - missing tabs:', missingTabs)
            state.navOrder = defaultNavOrder
          }
        }
      },
    }
  )
)
