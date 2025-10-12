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
  'team',
  'chat',
  'editor',
  'database'
]

export const useNavigationStore = create<NavigationStore>()(
  persist(
    (set) => ({
      activeTab: 'database',
      setActiveTab: (tab) => set({ activeTab: tab }),

      navOrder: defaultNavOrder,
      setNavOrder: (order) => set({ navOrder: order }),
    }),
    {
      name: 'ns.navigation',
    }
  )
)
