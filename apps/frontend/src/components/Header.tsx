import { useState } from 'react'
import { Cpu } from 'lucide-react'
import { QuickChatDropdown } from './QuickChatDropdown'
import { ModelManagementSidebar } from './ModelManagementSidebar'

export function Header() {
  const [showModelSidebar, setShowModelSidebar] = useState(false)

  return (
    <>
      <header className="glass border-b border-white/30 dark:border-gray-700/40">
        <div className="flex items-center justify-between py-3.5 px-6">
          {/* Left-aligned title */}
          <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            OmniStudio
          </h1>

          {/* Right-aligned controls */}
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
