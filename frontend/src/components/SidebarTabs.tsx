import { useState, useEffect } from 'react'
import { ColumnInspector } from './ColumnInspector'
import { LogViewer } from './LogViewer'

type Tab = 'columns' | 'logs'

export function SidebarTabs() {
  const [activeTab, setActiveTab] = useState<Tab>('columns')

  // Allow external components (Header) to open Logs/Columns
  // e.g., "Let's Chat" button focuses Logs as a chat-like panel
  useEffect(() => {
    const openLogs = () => setActiveTab('logs')
    const openColumns = () => setActiveTab('columns')
    window.addEventListener('open-logs', openLogs)
    window.addEventListener('open-columns', openColumns)
    return () => {
      window.removeEventListener('open-logs', openLogs)
      window.removeEventListener('open-columns', openColumns)
    }
  }, [])

  return (
    <div className="h-full flex flex-col">
      {/* Tab Headers */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 relative">
        <button
          onClick={() => setActiveTab('columns')}
          className={`
            flex-1 px-4 py-2 text-sm font-medium transition-colors
            ${activeTab === 'columns'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Columns
        </button>
        
        {/* Vertical divider */}
        <div className="w-px bg-gray-200 dark:bg-gray-700 my-2" />
        
        <button
          onClick={() => setActiveTab('logs')}
          className={`
            flex-1 px-4 py-2 text-sm font-medium transition-colors
            ${activeTab === 'logs'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Logs
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'columns' && <ColumnInspector />}
        {activeTab === 'logs' && <LogViewer />}
      </div>
    </div>
  )
}
