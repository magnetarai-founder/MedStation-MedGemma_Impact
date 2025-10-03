import { Code, MessageSquare, FolderOpen, SlidersHorizontal } from 'lucide-react'

interface NavigationRailProps {
  activeTab: 'chat' | 'editor' | 'queries'
  onTabChange: (tab: 'chat' | 'editor' | 'queries') => void
}

export function NavigationRail({ activeTab, onTabChange }: NavigationRailProps) {
  const handleOpenSettings = () => {
    window.dispatchEvent(new CustomEvent('open-settings'))
  }

  return (
    <div className="w-18 glass flex flex-col items-center justify-between">
      {/* Top section with logo and nav buttons */}
      <div className="flex flex-col items-center gap-3">
        {/* Logo at top */}
        <div className="py-5 flex items-center justify-center">
        <div className="relative w-10 h-10">
          {/* Outer glow/radiation */}
          <div className="absolute -inset-1 bg-primary-400/30 rounded-full blur-sm animate-pulse"></div>

          {/* Main star body - gradient sphere */}
          <div className="absolute inset-0 bg-gradient-radial from-blue-200 via-primary-500 to-primary-800 rounded-full shadow-lg"></div>

          {/* Surface detail - darker spots */}
          <div className="absolute inset-2 bg-primary-700/40 rounded-full"></div>

          {/* Bright core */}
          <div className="absolute inset-3 bg-gradient-to-br from-white via-blue-100 to-primary-300 rounded-full"></div>

          {/* Polar emission beams */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-t from-primary-300 to-transparent"></div>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-b from-primary-300 to-transparent"></div>

          {/* Rotating effect with magnetic field indicators */}
          <div className="absolute inset-0 rounded-full border border-primary-400/50"></div>
        </div>
      </div>

      {/* Divider */}
      <div className="w-12 h-px bg-gray-300/30 dark:bg-gray-600/30"></div>

      <button
        onClick={() => onTabChange('chat')}
        className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${
          activeTab === 'chat'
            ? 'bg-primary-600/90 text-white shadow-xl backdrop-blur-xl'
            : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg'
        }`}
        title="AI Chat"
      >
        <MessageSquare size={22} />
      </button>

      <button
        onClick={() => onTabChange('editor')}
        className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${
          activeTab === 'editor'
            ? 'bg-primary-600/90 text-white shadow-xl backdrop-blur-xl'
            : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg'
        }`}
        title="Code Editor (SQL/JSON)"
      >
        <Code size={22} />
      </button>

      <button
        onClick={() => onTabChange('queries')}
        className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${
          activeTab === 'queries'
            ? 'bg-primary-600/90 text-white shadow-xl backdrop-blur-xl'
            : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg'
        }`}
        title="History & Library"
      >
        <FolderOpen size={22} />
      </button>
      </div>

      {/* Bottom section - Settings */}
      <button
        onClick={handleOpenSettings}
        className="mb-6 w-14 h-14 rounded-2xl flex items-center justify-center transition-all text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg"
        title="Settings"
      >
        <SlidersHorizontal size={22} />
      </button>
    </div>
  )
}
