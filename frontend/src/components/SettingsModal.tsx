import { useEffect, useState } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { MessageSquare, Code, FileJson, Globe, Settings2, Download } from 'lucide-react'

type Tab = 'display' | 'chat' | 'editor' | 'json' | 'performance' | 'export'

export function SettingsModal() {
  const settings = useSettingsStore()
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('display')

  // Local state for editing
  const [localSettings, setLocalSettings] = useState({
    logoAnimation: settings.logoAnimation,
    chatAutoTitle: settings.chatAutoTitle,
    chatContextWindow: settings.chatContextWindow,
    previewRowCount: settings.previewRowCount,
    queryTimeout: settings.queryTimeout,
    maxFileSize: settings.maxFileSize,
    memoryLimit: settings.memoryLimit,
    sessionTimeout: settings.sessionTimeout,
    maxHistoryItems: settings.maxHistoryItems,
    maxSavedQueries: settings.maxSavedQueries,
    defaultExportFormat: settings.defaultExportFormat,
    exportFilenamePattern: settings.exportFilenamePattern,
    jsonExpandArrays: settings.jsonExpandArrays,
    jsonMaxDepth: settings.jsonMaxDepth,
    jsonAutoSafe: settings.jsonAutoSafe,
    jsonIncludeSummary: settings.jsonIncludeSummary,
  })

  useEffect(() => {
    const openHandler = () => {
      // Reset local state to current settings
      setLocalSettings({
        logoAnimation: settings.logoAnimation,
        chatAutoTitle: settings.chatAutoTitle,
        chatContextWindow: settings.chatContextWindow,
        previewRowCount: settings.previewRowCount,
        queryTimeout: settings.queryTimeout,
        maxFileSize: settings.maxFileSize,
        memoryLimit: settings.memoryLimit,
        sessionTimeout: settings.sessionTimeout,
        maxHistoryItems: settings.maxHistoryItems,
        maxSavedQueries: settings.maxSavedQueries,
        defaultExportFormat: settings.defaultExportFormat,
        exportFilenamePattern: settings.exportFilenamePattern,
        jsonExpandArrays: settings.jsonExpandArrays,
        jsonMaxDepth: settings.jsonMaxDepth,
        jsonAutoSafe: settings.jsonAutoSafe,
        jsonIncludeSummary: settings.jsonIncludeSummary,
      })
      setOpen(true)
    }
    const closeHandler = () => setOpen(false)
    window.addEventListener('open-settings', openHandler)
    window.addEventListener('close-settings', closeHandler)
    return () => {
      window.removeEventListener('open-settings', openHandler)
      window.removeEventListener('close-settings', closeHandler)
    }
  }, [settings])

  const handleSave = () => {
    settings.setLogoAnimation(localSettings.logoAnimation)
    settings.setChatAutoTitle(localSettings.chatAutoTitle)
    settings.setChatContextWindow(Math.max(10, Math.min(200, localSettings.chatContextWindow)))
    settings.setPreviewRowCount(Math.max(10, Math.min(10000, localSettings.previewRowCount)))
    settings.setQueryTimeout(Math.max(30, Math.min(600, localSettings.queryTimeout)))
    settings.setMaxFileSize(Math.max(10, Math.min(10000, localSettings.maxFileSize)))
    settings.setMemoryLimit(Math.max(512, Math.min(16384, localSettings.memoryLimit)))
    settings.setSessionTimeout(Math.max(0, Math.min(168, localSettings.sessionTimeout)))
    settings.setMaxHistoryItems(Math.max(10, Math.min(1000, localSettings.maxHistoryItems)))
    settings.setMaxSavedQueries(Math.max(10, Math.min(1000, localSettings.maxSavedQueries)))
    settings.setDefaultExportFormat(localSettings.defaultExportFormat)
    settings.setExportFilenamePattern(localSettings.exportFilenamePattern)
    settings.setJsonExpandArrays(localSettings.jsonExpandArrays)
    settings.setJsonMaxDepth(Math.max(1, Math.min(10, localSettings.jsonMaxDepth)))
    settings.setJsonAutoSafe(localSettings.jsonAutoSafe)
    settings.setJsonIncludeSummary(localSettings.jsonIncludeSummary)
    setOpen(false)
  }

  if (!open) return null

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'display', label: 'Display', icon: Globe },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'editor', label: 'Editor', icon: Code },
    { id: 'json', label: 'JSON', icon: FileJson },
    { id: 'performance', label: 'Performance', icon: Settings2 },
    { id: 'export', label: 'Export', icon: Download },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-3xl glass-panel rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 dark:border-gray-700/30">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Settings</h2>
            <button
              onClick={() => setOpen(false)}
              className="text-sm px-3 py-1.5 rounded-xl text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
            >
              Close
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-white/10 dark:border-gray-700/30">
          <div className="flex gap-2 flex-wrap">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-primary-600/90 text-white shadow-lg'
                    : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60'
                }`}
              >
                <tab.icon size={16} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 max-h-[60vh] overflow-y-auto">
          {activeTab === 'display' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Logo Animation</label>
                <div className="space-y-2">
                  {['static', 'spinning', 'pulsing'].map((animation) => (
                    <label key={animation} className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="logoAnimation"
                        value={animation}
                        checked={localSettings.logoAnimation === animation}
                        onChange={(e) => setLocalSettings({ ...localSettings, logoAnimation: e.target.value as any })}
                        className="w-4 h-4 text-primary-600"
                      />
                      <span className="text-sm capitalize text-gray-900 dark:text-gray-100">{animation}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Auto-generate titles</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Automatically name chats from first message</p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.chatAutoTitle}
                  onChange={(e) => setLocalSettings({ ...localSettings, chatAutoTitle: e.target.checked })}
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <p className="text-sm text-gray-900 dark:text-gray-100 font-medium">Context Window: 200k tokens</p>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">Full conversation history sent to model for optimal context preservation</p>
              </div>
            </div>
          )}

          {activeTab === 'editor' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Preview row count</label>
                <input
                  type="number"
                  min={10}
                  max={10000}
                  step={10}
                  value={localSettings.previewRowCount}
                  onChange={(e) => setLocalSettings({ ...localSettings, previewRowCount: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Number of rows shown in query preview (10-10,000)</p>
              </div>
            </div>
          )}

          {activeTab === 'json' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Expand arrays</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Create rows for each array element</p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.jsonExpandArrays}
                  onChange={(e) => setLocalSettings({ ...localSettings, jsonExpandArrays: e.target.checked })}
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Max nesting depth</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={localSettings.jsonMaxDepth}
                  onChange={(e) => setLocalSettings({ ...localSettings, jsonMaxDepth: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Maximum depth for flattening nested objects (1-10)</p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Auto-safe mode</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Prevent row explosion from large array combinations</p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.jsonAutoSafe}
                  onChange={(e) => setLocalSettings({ ...localSettings, jsonAutoSafe: e.target.checked })}
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Include summary sheet</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Add conversion metadata to Excel output</p>
                </div>
                <input
                  type="checkbox"
                  checked={localSettings.jsonIncludeSummary}
                  onChange={(e) => setLocalSettings({ ...localSettings, jsonIncludeSummary: e.target.checked })}
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>
            </div>
          )}

          {activeTab === 'performance' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Query timeout (seconds)</label>
                <input
                  type="number"
                  min={30}
                  max={600}
                  step={30}
                  value={localSettings.queryTimeout}
                  onChange={(e) => setLocalSettings({ ...localSettings, queryTimeout: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Maximum time for query execution (30-600s)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Max file size (MB)</label>
                <input
                  type="number"
                  min={10}
                  max={10000}
                  step={100}
                  value={localSettings.maxFileSize}
                  onChange={(e) => setLocalSettings({ ...localSettings, maxFileSize: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Maximum upload file size (10-10,000 MB)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Memory limit (MB)</label>
                <input
                  type="number"
                  min={512}
                  max={16384}
                  step={512}
                  value={localSettings.memoryLimit}
                  onChange={(e) => setLocalSettings({ ...localSettings, memoryLimit: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">DuckDB memory limit (512-16,384 MB)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Session timeout (hours)</label>
                <input
                  type="number"
                  min={0}
                  max={168}
                  step={1}
                  value={localSettings.sessionTimeout}
                  onChange={(e) => setLocalSettings({ ...localSettings, sessionTimeout: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Auto-delete idle sessions (0 = never, max 168h/7d)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Max history items</label>
                <input
                  type="number"
                  min={10}
                  max={1000}
                  step={10}
                  value={localSettings.maxHistoryItems}
                  onChange={(e) => setLocalSettings({ ...localSettings, maxHistoryItems: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Max query history to keep (10-1,000)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Max saved queries</label>
                <input
                  type="number"
                  min={10}
                  max={1000}
                  step={10}
                  value={localSettings.maxSavedQueries}
                  onChange={(e) => setLocalSettings({ ...localSettings, maxSavedQueries: Number(e.target.value) })}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Max saved queries to keep (10-1,000)</p>
              </div>
            </div>
          )}

          {activeTab === 'export' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Default export format</label>
                <select
                  value={localSettings.defaultExportFormat}
                  onChange={(e) => setLocalSettings({ ...localSettings, defaultExportFormat: e.target.value as any })}
                  className="px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                >
                  <option value="excel">Excel (.xlsx)</option>
                  <option value="csv">CSV</option>
                  <option value="parquet">Parquet</option>
                  <option value="json">JSON</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Export filename pattern</label>
                <input
                  type="text"
                  value={localSettings.exportFilenamePattern}
                  onChange={(e) => setLocalSettings({ ...localSettings, exportFilenamePattern: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  placeholder="omni_export_{date}"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Use {'{date}'} for current date</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 dark:border-gray-700/30 flex justify-end gap-3">
          <button
            onClick={() => setOpen(false)}
            className="px-4 py-2 text-sm font-medium rounded-xl text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm font-medium rounded-xl bg-primary-600 text-white hover:bg-primary-700 shadow-lg transition-all"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}
