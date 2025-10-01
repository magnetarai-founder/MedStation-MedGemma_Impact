import { useEffect, useState } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { MessageSquare, Database, FileJson, Globe } from 'lucide-react'

export function SettingsModal() {
  const {
    previewRowCount,
    setPreviewRowCount,
    jsonExpandArrays,
    jsonMaxDepth,
    jsonAutoSafe,
    setJsonExpandArrays,
    setJsonMaxDepth,
    setJsonAutoSafe,
    chatAutoTitle,
    chatContextWindow,
    setChatAutoTitle,
    setChatContextWindow,
  } = useSettingsStore()

  const [open, setOpen] = useState(false)
  const [activeSettingsTab, setActiveSettingsTab] = useState<'chat' | 'sql' | 'json' | 'global'>('global')

  // Local state for all settings
  const [localPreviewCount, setLocalPreviewCount] = useState(previewRowCount)
  const [localJsonExpand, setLocalJsonExpand] = useState(jsonExpandArrays)
  const [localJsonDepth, setLocalJsonDepth] = useState(jsonMaxDepth)
  const [localJsonSafe, setLocalJsonSafe] = useState(jsonAutoSafe)
  const [localChatAutoTitle, setLocalChatAutoTitle] = useState(chatAutoTitle)
  const [localChatContext, setLocalChatContext] = useState(chatContextWindow)

  useEffect(() => {
    const openHandler = () => {
      // Load current values
      setLocalPreviewCount(previewRowCount)
      setLocalJsonExpand(jsonExpandArrays)
      setLocalJsonDepth(jsonMaxDepth)
      setLocalJsonSafe(jsonAutoSafe)
      setLocalChatAutoTitle(chatAutoTitle)
      setLocalChatContext(chatContextWindow)
      setOpen(true)
    }
    const closeHandler = () => setOpen(false)
    window.addEventListener('open-settings', openHandler)
    window.addEventListener('close-settings', closeHandler)
    return () => {
      window.removeEventListener('open-settings', openHandler)
      window.removeEventListener('close-settings', closeHandler)
    }
  }, [previewRowCount, jsonExpandArrays, jsonMaxDepth, jsonAutoSafe, chatAutoTitle, chatContextWindow])

  const handleSave = () => {
    // Save all settings
    setPreviewRowCount(Math.max(10, Math.min(10000, localPreviewCount || 100)))
    setJsonExpandArrays(localJsonExpand)
    setJsonMaxDepth(Math.max(1, Math.min(10, localJsonDepth || 5)))
    setJsonAutoSafe(localJsonSafe)
    setChatAutoTitle(localChatAutoTitle)
    setChatContextWindow(Math.max(10, Math.min(200, localChatContext || 50)))
    setOpen(false)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl glass-panel rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 dark:border-gray-700/30">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Settings</h2>
            <button
              onClick={() => setOpen(false)}
              className="text-sm px-3 py-1.5 rounded-xl text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all"
            >
              Done
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-6 py-3 border-b border-white/10 dark:border-gray-700/30">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveSettingsTab('global')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                activeSettingsTab === 'global'
                  ? 'bg-primary-600/90 text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60'
              }`}
            >
              <Globe size={16} />
              Global
            </button>
            <button
              onClick={() => setActiveSettingsTab('chat')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                activeSettingsTab === 'chat'
                  ? 'bg-primary-600/90 text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60'
              }`}
            >
              <MessageSquare size={16} />
              Chat
            </button>
            <button
              onClick={() => setActiveSettingsTab('sql')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                activeSettingsTab === 'sql'
                  ? 'bg-primary-600/90 text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60'
              }`}
            >
              <Database size={16} />
              SQL
            </button>
            <button
              onClick={() => setActiveSettingsTab('json')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                activeSettingsTab === 'json'
                  ? 'bg-primary-600/90 text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60'
              }`}
            >
              <FileJson size={16} />
              JSON
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6 max-h-96 overflow-y-auto">
          {/* Global Settings */}
          {activeSettingsTab === 'global' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Application-wide settings and preferences.
              </p>
              {/* Add global settings here in the future */}
              <div className="text-sm text-gray-500 dark:text-gray-400 italic">
                No global settings available yet.
              </div>
            </div>
          )}

          {/* Chat Settings */}
          {activeSettingsTab === 'chat' && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Auto-generate titles</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Automatically name chats from first message</p>
                </div>
                <input
                  type="checkbox"
                  checked={localChatAutoTitle}
                  onChange={(e) => setLocalChatAutoTitle(e.target.checked)}
                  className="w-5 h-5 rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Context window size</label>
                <input
                  type="number"
                  min={10}
                  max={200}
                  step={10}
                  value={localChatContext}
                  onChange={(e) => setLocalChatContext(Number(e.target.value))}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Number of recent messages sent to model</p>
              </div>
            </>
          )}

          {/* SQL Settings */}
          {activeSettingsTab === 'sql' && (
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Preview row count</label>
              <input
                type="number"
                min={10}
                max={10000}
                step={10}
                value={localPreviewCount}
                onChange={(e) => setLocalPreviewCount(Number(e.target.value))}
                className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Number of rows shown in preview</p>
            </div>
          )}

          {/* JSON Settings */}
          {activeSettingsTab === 'json' && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Expand arrays</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Flatten nested arrays</p>
                </div>
                <input
                  type="checkbox"
                  checked={localJsonExpand}
                  onChange={(e) => setLocalJsonExpand(e.target.checked)}
                  className="w-5 h-5 rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Max depth</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={localJsonDepth}
                  onChange={(e) => setLocalJsonDepth(Number(e.target.value))}
                  className="w-40 px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Maximum nesting level to process</p>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">Auto-safe mode</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Handle special characters safely</p>
                </div>
                <input
                  type="checkbox"
                  checked={localJsonSafe}
                  onChange={(e) => setLocalJsonSafe(e.target.checked)}
                  className="w-5 h-5 rounded"
                />
              </div>
            </>
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

