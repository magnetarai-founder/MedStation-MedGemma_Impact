import { useState, useEffect } from 'react'
import { Wand2, CheckCircle, AlertCircle, Info, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../lib/api'

interface AgentAssistProps {
  workspaceRoot?: string
  sessionId?: string
  openFiles?: string[]
}

interface PlanStep {
  description: string
  risk_level: string
  estimated_files: number
}

interface FilePatch {
  path: string
  patch_text: string
  summary: string
}

export function AgentAssist({ workspaceRoot, sessionId, openFiles = [] }: AgentAssistProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [plan, setPlan] = useState<{
    steps: PlanStep[]
    risks: string[]
    requires_confirmation: boolean
    estimated_time_min: number
  } | null>(null)
  const [patches, setPatches] = useState<FilePatch[]>([])
  const [applySuccess, setApplySuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [capabilities, setCapabilities] = useState<{
    engines: Array<{
      name: string
      available: boolean
      version?: string
      error?: string
      remediation?: string
    }>
    features: Record<string, boolean>
  } | null>(null)

  // Load capabilities on mount
  useEffect(() => {
    loadCapabilities()
  }, [])

  const loadCapabilities = async () => {
    try {
      const caps = await api.agentCapabilities()
      setCapabilities(caps)
    } catch (err) {
      console.error('Failed to load agent capabilities:', err)
    }
  }

  const handleGeneratePlan = async () => {
    if (!input.trim()) return

    setLoading(true)
    setError(null)
    setPlan(null)
    setPatches([])
    setApplySuccess(false)

    try {
      // Get context first
      const context = await api.agentContext({
        sessionId,
        repoRoot: workspaceRoot,
        openFiles
      })

      // Generate plan
      const planResult = await api.agentPlan({
        input: input.trim(),
        contextBundle: context
      })

      setPlan(planResult)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate plan')
    } finally {
      setLoading(false)
    }
  }

  const handleApplyPlan = async (dryRun: boolean = false) => {
    if (!plan) return

    setLoading(true)
    setError(null)
    setApplySuccess(false)

    try {
      const result = await api.agentApply({
        input: input.trim(),
        repoRoot: workspaceRoot,
        dryRun
      })

      if (result.success) {
        setPatches(result.patches)
        if (!dryRun) {
          setApplySuccess(true)
        }
      } else {
        setError('Failed to apply changes')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to apply plan')
    } finally {
      setLoading(false)
    }
  }

  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case 'high': return 'bg-red-100 text-red-800 border-red-300'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      default: return 'bg-green-100 text-green-800 border-green-300'
    }
  }

  // Check if any engine is available
  const hasAvailableEngines = capabilities?.engines.some(e => e.available) || false

  return (
    <div className="border rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Wand2 className="w-4 h-4 text-purple-600" />
          <span className="font-medium text-sm">AI Agent Assist</span>
          {capabilities && !hasAvailableEngines && (
            <span className="text-xs text-orange-600">(Limited - No engines)</span>
          )}
        </div>
        <button className="p-1 hover:bg-gray-200 rounded">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Capabilities Warning */}
          {capabilities && !hasAvailableEngines && (
            <div className="bg-orange-50 border border-orange-200 rounded p-3 text-sm">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-orange-600 mt-0.5" />
                <div>
                  <p className="font-medium text-orange-900">No AI engines available</p>
                  <p className="text-orange-700 text-xs mt-1">
                    Agent features require Aider or Continue. Check capabilities below.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Input */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Describe what you want to do:
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g., Add error handling to the API endpoints, refactor the authentication logic, etc."
              className="w-full border rounded p-2 text-sm min-h-[80px] focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleGeneratePlan}
              disabled={loading || !input.trim() || !hasAvailableEngines}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
              Generate Plan
            </button>

            {plan && (
              <>
                <button
                  onClick={() => handleApplyPlan(true)}
                  disabled={loading}
                  className="px-4 py-2 border border-purple-600 text-purple-600 rounded hover:bg-purple-50 disabled:opacity-50 text-sm"
                >
                  Preview Changes
                </button>
                <button
                  onClick={() => handleApplyPlan(false)}
                  disabled={loading || !plan}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 text-sm"
                >
                  Apply Changes
                </button>
              </>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 mt-0.5" />
                <div className="text-red-900">{error}</div>
              </div>
            </div>
          )}

          {/* Success */}
          {applySuccess && (
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-600 mt-0.5" />
                <div className="text-green-900">Changes applied successfully!</div>
              </div>
            </div>
          )}

          {/* Plan */}
          {plan && (
            <div className="border rounded p-3 bg-gray-50 space-y-3">
              <div className="font-medium text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600" />
                Execution Plan ({plan.estimated_time_min} min estimated)
              </div>

              {/* Steps */}
              <div className="space-y-2">
                {plan.steps.map((step, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-gray-500 mt-0.5">{idx + 1}.</span>
                    <div className="flex-1">
                      <p>{step.description}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs px-2 py-0.5 rounded border ${getRiskBadgeColor(step.risk_level)}`}>
                          {step.risk_level} risk
                        </span>
                        {step.estimated_files > 0 && (
                          <span className="text-xs text-gray-600">
                            ~{step.estimated_files} file{step.estimated_files > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Risks */}
              {plan.risks.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                  <p className="text-xs font-medium text-yellow-900 mb-1">⚠️ Risks:</p>
                  <ul className="text-xs text-yellow-800 list-disc list-inside">
                    {plan.risks.map((risk, idx) => (
                      <li key={idx}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}

              {plan.requires_confirmation && (
                <div className="text-xs text-orange-600">
                  ⚠️ This plan requires careful review before applying
                </div>
              )}
            </div>
          )}

          {/* Patches Preview */}
          {patches.length > 0 && (
            <div className="border rounded p-3 bg-gray-50 space-y-2">
              <div className="font-medium text-sm">Changes Preview:</div>
              {patches.map((patch, idx) => (
                <details key={idx} className="text-sm">
                  <summary className="cursor-pointer hover:bg-gray-100 p-2 rounded">
                    {patch.path} - {patch.summary}
                  </summary>
                  <pre className="bg-black text-green-400 p-2 rounded mt-2 text-xs overflow-x-auto">
                    {patch.patch_text}
                  </pre>
                </details>
              ))}
            </div>
          )}

          {/* Capabilities Info (collapsible) */}
          {capabilities && (
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                Engine Capabilities
              </summary>
              <div className="mt-2 space-y-2 pl-4">
                {capabilities.engines.map((engine) => (
                  <div key={engine.name} className="flex items-start gap-2">
                    <div className={`w-2 h-2 rounded-full mt-1 ${engine.available ? 'bg-green-500' : 'bg-red-500'}`} />
                    <div className="flex-1">
                      <div className="font-medium">
                        {engine.name} {engine.version && `(${engine.version})`}
                      </div>
                      {engine.error && (
                        <div className="text-red-600">{engine.error}</div>
                      )}
                      {engine.remediation && (
                        <div className="text-gray-600 italic">{engine.remediation}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
