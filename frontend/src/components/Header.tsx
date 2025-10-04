import { useNavigationStore } from '@/stores/navigationStore'

export function Header() {
  const { activeTab } = useNavigationStore()

  return (
    <header className="glass border-b border-white/30 dark:border-gray-700/40">
      <div className="flex items-center justify-between py-3.5 px-6">
        {/* Title aligned after nav rail */}
        <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          OmniStudio
        </h1>

        {/* Right side - buttons */}
        <div className="flex items-center space-x-4">
          {/* Tab-specific Clear buttons */}
          {false && activeTab === 'json' && (
            <button
              onClick={handleClearJsonWorkspace}
              disabled={isExecuting}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-sm transition-all ${isExecuting ? 'text-gray-400 cursor-not-allowed' : 'text-gray-700 hover:bg-red-50 hover:text-red-600 dark:text-gray-300 dark:hover:bg-red-900/20 dark:hover:text-red-400'}`}
              title="Clear JSON workspace"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
