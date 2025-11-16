import { Database, SlidersHorizontal, MessageSquare, Briefcase, Code, Shield, Kanban } from 'lucide-react'
import { type NavTab } from '../stores/navigationStore'
import { usePermissions } from '@/hooks/usePermissions'

interface NavigationRailProps {
  activeTab: NavTab
  onTabChange: (tab: NavTab) => void
  onOpenSettings: () => void
}

// Navigation item configuration
const NAV_ITEMS = {
  team: { icon: Briefcase, label: 'Workspace' },
  chat: { icon: MessageSquare, label: 'AI Chat' },
  code: { icon: Code, label: 'Code' },
  database: { icon: Database, label: 'Database' },
  kanban: { icon: Kanban, label: 'Kanban' },
  admin: { icon: Shield, label: 'Admin' },
} as const

// Static navigation order
const NAV_ORDER: NavTab[] = ['chat', 'team', 'kanban', 'code', 'database']

export function NavigationRail({ activeTab, onTabChange, onOpenSettings }: NavigationRailProps) {
  const permissions = usePermissions()

  // Filter navigation items based on permissions
  const getVisibleNavItems = (): NavTab[] => {
    return NAV_ORDER.filter((itemId) => {
      switch (itemId) {
        case 'team':
          // Team workspace: Everyone can access (includes chat + file share for guests)
          return true
        case 'chat':
          // AI Chat: Everyone can access
          return permissions.canAccessChat
        case 'code':
          // Code: Members and above only (no guests)
          return permissions.canAccessCode
        case 'database':
          // Database: Members and above only (no guests)
          return permissions.canAccessDocuments
        case 'kanban':
          // Kanban: Members and above only (no guests)
          return permissions.canAccessDocuments
        case 'admin':
          // Admin: All authenticated users can access
          return true
        default:
          return true
      }
    })
  }

  const visibleNavItems = getVisibleNavItems()

  const getButtonClasses = (itemId: string) => {
    const isActive = activeTab === itemId

    return `w-14 h-14 rounded-2xl flex items-center justify-center transition-all cursor-pointer ${
      isActive
        ? 'bg-primary-600/90 text-white shadow-xl backdrop-blur-xl'
        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg'
    }`
  }

  return (
    <div className="w-18 glass flex flex-col items-center bg-gradient-to-b from-indigo-50/80 via-purple-50/80 to-blue-50/80 dark:from-gray-900/80 dark:via-gray-850/80 dark:to-gray-900/80 backdrop-blur-xl border-r border-white/20 dark:border-gray-700/30">
      {/* Top section with navigation items */}
      <div className="flex flex-col items-center gap-3 pt-5">
        {/* Role-filtered navigation items */}
        {visibleNavItems.map((itemId) => {
          const item = NAV_ITEMS[itemId]
          const Icon = item.icon

          return (
            <button
              key={itemId}
              onClick={() => onTabChange(itemId)}
              className={getButtonClasses(itemId)}
              title={item.label}
            >
              <Icon size={22} />
            </button>
          )
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1"></div>

      {/* Bottom section - Admin + Settings */}
      <div className="pb-4 flex flex-col gap-3">
        {/* Admin button (all authenticated users can see) */}
        <button
          onClick={() => onTabChange('admin')}
          className={getButtonClasses('admin')}
          title="Admin"
        >
          <Shield size={22} />
        </button>

        <button
          onClick={onOpenSettings}
          className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg"
          title="Settings"
        >
          <SlidersHorizontal size={22} />
        </button>
      </div>
    </div>
  )
}
