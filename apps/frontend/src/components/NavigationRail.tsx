import { Database, SlidersHorizontal, MessageSquare, Briefcase, GitBranch, Power } from 'lucide-react'
import { type NavTab } from '../stores/navigationStore'

interface NavigationRailProps {
  activeTab: NavTab
  onTabChange: (tab: NavTab) => void
  onOpenSettings: () => void
  onOpenServerControls: () => void
}

// Navigation item configuration
const NAV_ITEMS = {
  team: { icon: Briefcase, label: 'Workspace' },
  chat: { icon: MessageSquare, label: 'AI Chat' },
  editor: { icon: GitBranch, label: 'Automation' },
  database: { icon: Database, label: 'Database' },
} as const

// Static navigation order
const NAV_ORDER: NavTab[] = ['chat', 'team', 'editor', 'database']

export function NavigationRail({ activeTab, onTabChange, onOpenSettings, onOpenServerControls }: NavigationRailProps) {
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
        {/* Static navigation items */}
        {NAV_ORDER.map((itemId) => {
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

      {/* Bottom section - Settings & Server Controls */}
      <div className="pb-4 flex flex-col gap-3">
        <button
          onClick={onOpenSettings}
          className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg"
          title="Settings"
        >
          <SlidersHorizontal size={22} />
        </button>
        <button
          onClick={onOpenServerControls}
          className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg"
          title="Ollama Server Controls"
        >
          <Power size={22} />
        </button>
      </div>
    </div>
  )
}
