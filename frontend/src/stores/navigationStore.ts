import { create } from 'zustand'

interface NavigationStore {
  activeTab: 'chat' | 'sql' | 'json'
  setActiveTab: (tab: 'chat' | 'sql' | 'json') => void
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  activeTab: 'chat',
  setActiveTab: (tab) => set({ activeTab: tab }),
}))