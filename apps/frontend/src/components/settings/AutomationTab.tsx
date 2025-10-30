/**
 * Automation Settings Tab
 *
 * Configure workflow automation, code editor preferences, and integration settings
 */

import { useState } from 'react'
import { Workflow, Code, Database, Zap, GitBranch, Cpu, Save } from 'lucide-react'
import { showToast } from '@/lib/toast'

export default function AutomationTab() {
  const [settings, setSettings] = useState({
    // Workflow settings
    auto_save_workflows: true,
    workflow_notifications: true,
    enable_workflow_templates: true,

    // Code editor settings
    editor_theme: 'vs-dark',
    editor_font_size: 14,
    editor_tab_size: 2,
    editor_word_wrap: true,
    editor_minimap: true,
    editor_line_numbers: true,

    // Integration settings
    enable_n8n: false,
    n8n_webhook_url: '',
    enable_mcp: false,

    // Database settings
    query_timeout: 30,
    max_query_results: 1000,
    enable_query_cache: true,
  })

  const handleSave = () => {
    // Save settings to localStorage
    localStorage.setItem('automation_settings', JSON.stringify(settings))
    showToast.success('Automation settings saved')
  }

  const handleReset = () => {
    if (confirm('Reset all automation settings to defaults?')) {
      const defaults = {
        auto_save_workflows: true,
        workflow_notifications: true,
        enable_workflow_templates: true,
        editor_theme: 'vs-dark',
        editor_font_size: 14,
        editor_tab_size: 2,
        editor_word_wrap: true,
        editor_minimap: true,
        editor_line_numbers: true,
        enable_n8n: false,
        n8n_webhook_url: '',
        enable_mcp: false,
        query_timeout: 30,
        max_query_results: 1000,
        enable_query_cache: true,
      }
      setSettings(defaults)
      localStorage.setItem('automation_settings', JSON.stringify(defaults))
      showToast.success('Settings reset to defaults')
    }
  }

  return (
    <div className="space-y-6">
      {/* Workflow Settings */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Workflow className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Workflow Automation
          </h3>
        </div>

        <div className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.auto_save_workflows}
              onChange={(e) => setSettings({ ...settings, auto_save_workflows: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Auto-save workflows
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Automatically save workflow changes as you edit
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.workflow_notifications}
              onChange={(e) => setSettings({ ...settings, workflow_notifications: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Workflow notifications
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Show toast notifications for workflow events
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enable_workflow_templates}
              onChange={(e) => setSettings({ ...settings, enable_workflow_templates: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Enable workflow templates
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Show pre-built workflow templates in the library
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Code Editor Settings */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Code className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Code Editor
          </h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Editor theme
            </label>
            <select
              value={settings.editor_theme}
              onChange={(e) => setSettings({ ...settings, editor_theme: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="vs-dark">Dark (VS Code)</option>
              <option value="vs-light">Light (VS Code)</option>
              <option value="hc-black">High Contrast</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Font size: {settings.editor_font_size}px
            </label>
            <input
              type="range"
              min="10"
              max="24"
              value={settings.editor_font_size}
              onChange={(e) => setSettings({ ...settings, editor_font_size: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Tab size
            </label>
            <select
              value={settings.editor_tab_size}
              onChange={(e) => setSettings({ ...settings, editor_tab_size: parseInt(e.target.value) })}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="2">2 spaces</option>
              <option value="4">4 spaces</option>
              <option value="8">8 spaces</option>
            </select>
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.editor_word_wrap}
              onChange={(e) => setSettings({ ...settings, editor_word_wrap: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Word wrap
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.editor_minimap}
              onChange={(e) => setSettings({ ...settings, editor_minimap: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Show minimap
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.editor_line_numbers}
              onChange={(e) => setSettings({ ...settings, editor_line_numbers: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Show line numbers
            </div>
          </label>
        </div>
      </div>

      {/* Integration Settings */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Integrations
          </h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="flex items-center gap-3 cursor-pointer mb-2">
              <input
                type="checkbox"
                checked={settings.enable_n8n}
                onChange={(e) => setSettings({ ...settings, enable_n8n: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
              />
              <div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Enable n8n integration
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  Connect workflows to n8n automation platform
                </div>
              </div>
            </label>

            {settings.enable_n8n && (
              <input
                type="url"
                placeholder="https://n8n.yourdomain.com/webhook/..."
                value={settings.n8n_webhook_url}
                onChange={(e) => setSettings({ ...settings, n8n_webhook_url: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
              />
            )}
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enable_mcp}
              onChange={(e) => setSettings({ ...settings, enable_mcp: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Enable MCP (Model Context Protocol)
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Connect to MCP servers for extended functionality
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Database Settings */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Database & Queries
          </h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Query timeout (seconds)
            </label>
            <input
              type="number"
              min="5"
              max="300"
              value={settings.query_timeout}
              onChange={(e) => setSettings({ ...settings, query_timeout: parseInt(e.target.value) })}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Maximum time a query can run before timing out
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Max query results
            </label>
            <input
              type="number"
              min="100"
              max="100000"
              step="100"
              value={settings.max_query_results}
              onChange={(e) => setSettings({ ...settings, max_query_results: parseInt(e.target.value) })}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Maximum number of rows to display from queries
            </p>
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enable_query_cache}
              onChange={(e) => setSettings({ ...settings, enable_query_cache: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Enable query caching
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Cache query results for faster repeated queries
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-6 flex items-center justify-between">
        <button
          onClick={handleReset}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          Reset to Defaults
        </button>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>
    </div>
  )
}
