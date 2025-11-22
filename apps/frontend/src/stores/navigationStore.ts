import { createWithEqualityFn } from 'zustand/traditional'
import { persist } from 'zustand/middleware'

export type NavTab = 'team' | 'chat' | 'database' | 'admin' | 'kanban'

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
  'team',      // Workspace first
  'chat',      // AI Chat second
  'database',  // Database third
  'kanban'     // Kanban fourth
]

export const useNavigationStore = createWithEqualityFn<NavigationStore>()(
  persist(
    (set, get) => ({
      activeTab: 'database',
      setActiveTab: (tab) => set({ activeTab: tab }),

      navOrder: defaultNavOrder,
      setNavOrder: (order) => set({ navOrder: order }),
    }),
    {
      name: 'ns.navigation',
      version: 3, // Increment version to force migration
      // Migration to ensure all tabs are present and in new default order
      migrate: (persistedState: any, version: number) => {
        // Force update to new default order for everyone
        if (version < 3) {
          console.log('Migrating navigation order to v3 - code tab removed')
          return {
            ...persistedState,
            navOrder: defaultNavOrder
          }
        }
        return persistedState
      },
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Check if navOrder has all required tabs
          const requiredTabs: NavTab[] = ['team', 'chat', 'database', 'kanban']
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
