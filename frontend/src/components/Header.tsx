import { useNavigationStore } from '@/stores/navigationStore'
import { QuickChatDropdown } from './QuickChatDropdown'

export function Header() {
  const { activeTab } = useNavigationStore()

  return (
    <header className="glass border-b border-white/30 dark:border-gray-700/40">
      <div className="flex items-center justify-between py-3.5 px-6">
        {/* Title aligned after nav rail */}
        <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          OmniStudio
        </h1>

        {/* Right side - Quick Chat & buttons */}
        <div className="flex items-center space-x-4">
          <QuickChatDropdown />
        </div>
      </div>
    </header>
  )
}
