import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type NavTab = 'team' | 'chat' | 'database' | 'queries'

export interface NavItem {
  id: NavTab | 'json' | 'library'
  label: string
  locked?: boolean // Settings is always locked
  isModal?: boolean // JSON and Library are modals, not tabs
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
  'database',
  'queries',
  'json',
  'library'
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
