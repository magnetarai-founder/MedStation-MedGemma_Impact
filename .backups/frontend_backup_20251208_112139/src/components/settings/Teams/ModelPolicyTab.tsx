import { useEffect, useState } from 'react'
import { Shield, Save, AlertTriangle, Info } from 'lucide-react'
import { authFetch } from '../../../lib/api'
import { showToast } from '../../../lib/toast'

interface TeamModelPolicy {
  team_id: string
  allowed_models: string[]
  default_model: string | null
  updated_at: string | null
}

interface Model {
  name: string
  size?: string
  status?: string
}

interface ModelPolicyTabProps {
  teamId: string
  canManage: boolean // Whether user has team.manage_models permission
}

export default function ModelPolicyTab({ teamId, canManage }: ModelPolicyTabProps) {
  const [policy, setPolicy] = useState<TeamModelPolicy | null>(null)
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [defaultModel, setDefaultModel] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadData()
  }, [teamId])

  const loadData = async () => {
    setLoading(true)
    try {
      // Load available models from catalog
      const modelsRes = await authFetch('/api/v1/models/catalog')
      if (modelsRes.ok) {
        const modelsData = await modelsRes.json()
        setAvailableModels(modelsData.models || [])
      }

      // Load current policy
      const policyRes = await authFetch(`/api/v1/teams/${teamId}/model-policy`)
      if (policyRes.ok) {
        const policyData = await policyRes.json()
        setPolicy(policyData)
        setSelectedModels(new Set(policyData.allowed_models || []))
        setDefaultModel(policyData.default_model || '')
      }
    } catch (error) {
      console.error('Failed to load model policy:', error)
      showToast.error('Failed to load model policy')
    } finally {
      setLoading(false)
    }
  }

  const toggleModel = (modelName: string) => {
    if (!canManage) return

    const newSelected = new Set(selectedModels)
    if (newSelected.has(modelName)) {
      newSelected.delete(modelName)
      // If we're removing the default model, clear it
      if (defaultModel === modelName) {
        setDefaultModel('')
      }
    } else {
      newSelected.add(modelName)
    }
    setSelectedModels(newSelected)
  }

  const handleSave = async () => {
    if (!canManage) return

    // Validate
    if (selectedModels.size === 0) {
      const confirmed = window.confirm(
        'Warning: Setting no allowed models means team members will not be able to use any models. Continue?'
      )
      if (!confirmed) return
    }

    if (defaultModel && !selectedModels.has(defaultModel)) {
      showToast.error('Default model must be in allowed models')
      return
    }

    setSaving(true)
    const previousPolicy = { ...policy }
    const previousSelected = new Set(selectedModels)
    const previousDefault = defaultModel

    // Optimistic update
    const newPolicy: TeamModelPolicy = {
      team_id: teamId,
      allowed_models: Array.from(selectedModels),
      default_model: defaultModel || null,
      updated_at: new Date().toISOString()
    }
    setPolicy(newPolicy)

    try {
      const response = await authFetch(`/api/v1/teams/${teamId}/model-policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allowed_models: Array.from(selectedModels),
          default_model: defaultModel || null
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to save policy')
      }

      const updatedPolicy = await response.json()
      setPolicy(updatedPolicy)
      showToast.success('Model policy saved successfully')
    } catch (error) {
      // Rollback on failure
      setPolicy(previousPolicy as TeamModelPolicy)
      setSelectedModels(previousSelected)
      setDefaultModel(previousDefault)
      showToast.error(error instanceof Error ? error.message : 'Failed to save policy')
      console.error('Failed to save model policy:', error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500 dark:text-gray-400">Loading model policy...</div>
      </div>
    )
  }

  if (!canManage) {
    return (
      <div className="space-y-4">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-yellow-900 dark:text-yellow-100">
                Permission Required
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                You need the <code className="bg-yellow-100 dark:bg-yellow-900/40 px-1 rounded">team.manage_models</code> permission to manage team model policies.
              </p>
            </div>
          </div>
        </div>

        {/* Show current policy read-only */}
        {policy && policy.allowed_models.length > 0 && (
          <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Current Policy (Read-Only)
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-xs text-gray-600 dark:text-gray-400">Allowed Models:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {policy.allowed_models.map(model => (
                    <span
                      key={model}
                      className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded"
                    >
                      {model}
                    </span>
                  ))}
                </div>
              </div>
              {policy.default_model && (
                <div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">Default Model:</span>
                  <span className="ml-2 text-sm text-gray-900 dark:text-gray-100 font-medium">
                    {policy.default_model}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Model Access Policy
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Control which models team members can use in their sessions
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div className="text-sm text-blue-700 dark:text-blue-300">
            <p>
              <strong>How it works:</strong> Team members will only see and be able to select models from the allowed list.
              The default model (if set) will be automatically selected for new sessions.
            </p>
          </div>
        </div>
      </div>

      {/* Allowed Models Multi-Select */}
      <div>
        <label className="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Allowed Models
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 font-normal">
            ({selectedModels.size} selected)
          </span>
        </label>

        <div className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
          {availableModels.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
              No models available
            </div>
          ) : (
            availableModels.map((model) => (
              <label
                key={model.name}
                className="flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-900 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedModels.has(model.name)}
                  onChange={() => toggleModel(model.name)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  aria-label={`Allow ${model.name}`}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {model.name}
                    </span>
                    {model.size && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {model.size}
                      </span>
                    )}
                  </div>
                  {model.status && (
                    <span className={`text-xs ${
                      model.status === 'ready' ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'
                    }`}>
                      {model.status}
                    </span>
                  )}
                </div>
              </label>
            ))
          )}
        </div>
      </div>

      {/* Default Model Picker */}
      <div>
        <label htmlFor="default-model" className="block text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Default Model
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 font-normal">
            (optional)
          </span>
        </label>
        <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
          This model will be automatically selected for new sessions in this team context.
        </p>

        <select
          id="default-model"
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
          disabled={selectedModels.size === 0}
          className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">-- No default --</option>
          {Array.from(selectedModels).sort().map(model => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>

      {/* Warning for empty selection */}
      {selectedModels.size === 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
                No Models Selected
              </h3>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                Team members will not be able to use any models until you add at least one to the allowed list.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Saving...</span>
            </>
          ) : (
            <>
              <Save size={16} />
              <span>Save Policy</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}
