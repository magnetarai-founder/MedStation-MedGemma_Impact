import { useState } from 'react'
import { Cpu, Sparkles } from 'lucide-react'
import { QuickChatDropdown } from './QuickChatDropdown'
import { ModelManagementSidebar } from './ModelManagementSidebar'

export function Header() {
  const [showModelSidebar, setShowModelSidebar] = useState(false)

  return (
    <>
      <header className="glass border-b border-white/30 dark:border-gray-700/40">
        <div className="flex items-center justify-between py-3.5 px-6">
          {/* Left: Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
          </div>

          {/* Center: Title */}
          <h1 className="absolute left-1/2 transform -translate-x-1/2 text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            OmniStudio
          </h1>

          {/* Right: Controls */}
          <div className="flex items-center gap-3">
            {/* Model Management Button */}
            <button
              onClick={() => setShowModelSidebar(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
              title="Model Management (⌘M)"
            >
              <Cpu size={20} />
            </button>

            {/* Quick Chat */}
            <QuickChatDropdown />
          </div>
        </div>
      </header>

      {/* Model Management Sidebar */}
      <ModelManagementSidebar
        isOpen={showModelSidebar}
        onClose={() => setShowModelSidebar(false)}
      />
    </>
  )
}
