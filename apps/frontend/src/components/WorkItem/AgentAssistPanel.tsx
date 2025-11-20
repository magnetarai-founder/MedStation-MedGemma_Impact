/**
 * Agent Assist Panel Component
 * Displays agent recommendations, auto-apply results, and agent events for AGENT_ASSIST stages
 */

import React, { useState } from 'react';
import { AlertCircle, Bot, CheckCircle, XCircle, AlertTriangle, Clock, FileCode, Zap, Loader2 } from 'lucide-react';
import type {
  WorkItem,
  Stage,
  AgentRecommendation,
  AgentAutoApplyResult,
  AgentEventInfo,
  StageType,
} from '@/types/workflow';

interface AgentAssistPanelProps {
  workItem: WorkItem;
  stage: Stage;
  onRefresh?: () => void;
}

export function AgentAssistPanel({ workItem, stage, onRefresh }: AgentAssistPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Only show for AGENT_ASSIST stages
  if (stage.stage_type !== 'agent_assist') {
    return null;
  }

  // Extract agent data from work item
  const recommendation = workItem.data.agent_recommendation as AgentRecommendation | undefined;
  const error = workItem.data.agent_recommendation_error as string | undefined;
  const autoApplyResult = workItem.data.agent_auto_apply_result as AgentAutoApplyResult | undefined;
  const agentEvent = workItem.data.agent_event as AgentEventInfo | undefined;

  // Helper to render risk level badge
  const renderRiskBadge = (riskLevel?: string | null) => {
    if (!riskLevel) return null;

    const colors = {
      low: 'bg-green-900/30 text-green-300 border-green-700',
      medium: 'bg-yellow-900/30 text-yellow-300 border-yellow-700',
      high: 'bg-red-900/30 text-red-300 border-red-700',
    };

    const color = colors[riskLevel.toLowerCase() as keyof typeof colors] || colors.medium;

    return (
      <span className={`px-2 py-0.5 text-xs rounded border ${color}`}>
        {riskLevel}
      </span>
    );
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <Bot className="w-5 h-5 text-blue-400" />
          <h3 className="font-semibold text-white">Agent Assist</h3>
          {stage.agent_auto_apply && (
            <span className="px-2 py-0.5 text-xs bg-purple-900/30 text-purple-300 border border-purple-700 rounded">
              Auto-Apply Enabled
            </span>
          )}
        </div>
        <button className="text-gray-400 hover:text-white">
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 pt-0 space-y-4">
          {/* Error State */}
          {error && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h4 className="font-semibold text-red-300 mb-1">Agent Assist Failed</h4>
                  <p className="text-sm text-red-200/80">{error}</p>
                  <p className="text-xs text-red-300/60 mt-2">
                    Try again later or adjust the stage configuration.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Recommendation Display */}
          {recommendation && !error && (
            <div className="space-y-4">
              {/* Plan Summary */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileCode className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-300">Plan Summary</span>
                </div>
                <p className="text-sm text-gray-200 bg-gray-800/50 p-3 rounded border border-gray-700">
                  {recommendation.plan_summary}
                </p>
              </div>

              {/* Engine & Model Info */}
              {(recommendation.engine_used || recommendation.model_used) && (
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  {recommendation.engine_used && (
                    <span>Engine: <span className="text-gray-300">{recommendation.engine_used}</span></span>
                  )}
                  {recommendation.model_used && (
                    <span>Model: <span className="text-gray-300">{recommendation.model_used}</span></span>
                  )}
                  {recommendation.estimated_time_min && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      ~{recommendation.estimated_time_min} min
                    </span>
                  )}
                </div>
              )}

              {/* Steps */}
              {recommendation.steps && recommendation.steps.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">Steps</span>
                  </div>
                  <div className="space-y-2">
                    {recommendation.steps.map((step, idx) => (
                      <div
                        key={idx}
                        className="bg-gray-800/50 border border-gray-700 rounded p-3 text-sm"
                      >
                        <div className="flex items-start justify-between gap-3 mb-1">
                          <span className="text-gray-200 flex-1">{step.description}</span>
                          {step.risk_level && renderRiskBadge(step.risk_level)}
                        </div>
                        {(step.estimated_files || step.estimated_time_min) && (
                          <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                            {step.estimated_files && (
                              <span>{step.estimated_files} file(s)</span>
                            )}
                            {step.estimated_time_min && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                ~{step.estimated_time_min} min
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risks */}
              {recommendation.risks && recommendation.risks.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm font-medium text-gray-300">Risks to Consider</span>
                  </div>
                  <ul className="space-y-1 text-sm text-gray-300">
                    {recommendation.risks.map((risk, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-yellow-400 mt-0.5">•</span>
                        <span>{risk}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Confirmation Note */}
              {recommendation.requires_confirmation && (
                <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
                  <p className="text-sm text-blue-200 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Agent suggests human review before applying these changes.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* No Recommendation Yet */}
          {!recommendation && !error && (
            <div className="text-center py-6 text-gray-400">
              <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin opacity-50" />
              <p className="text-sm">Agent Assist hasn't produced a recommendation yet.</p>
              <p className="text-xs mt-1 text-gray-500">
                Recommendations are generated when the work item enters this stage.
              </p>
            </div>
          )}

          {/* Auto-Apply Results */}
          {autoApplyResult && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-gray-300">Agent Auto-Apply Result</span>
              </div>

              {autoApplyResult.success ? (
                <div className="bg-green-900/20 border border-green-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-green-300 mb-1">Auto-Apply Succeeded</h4>
                      {autoApplyResult.summary && (
                        <p className="text-sm text-green-200/80 mb-2">{autoApplyResult.summary}</p>
                      )}
                      {autoApplyResult.files_changed && autoApplyResult.files_changed.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-green-300/60 mb-1">Files Changed:</p>
                          <ul className="space-y-0.5">
                            {autoApplyResult.files_changed.map((file, idx) => (
                              <li key={idx} className="text-xs text-green-200/70 font-mono">
                                {file}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {autoApplyResult.patch_id && (
                        <p className="text-xs text-green-300/60 mt-2">
                          Patch ID: {autoApplyResult.patch_id}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-red-300 mb-1">Auto-Apply Failed</h4>
                      {autoApplyResult.error && (
                        <p className="text-sm text-red-200/80">{autoApplyResult.error}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Agent Events */}
          {agentEvent && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <Bot className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-gray-300">Agent Event</span>
              </div>

              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-gray-400">Type:</span>
                  <span className="text-gray-200 font-mono text-xs">{agentEvent.type}</span>
                </div>
                {agentEvent.summary && (
                  <p className="text-gray-300 mb-2">{agentEvent.summary}</p>
                )}
                {agentEvent.files && agentEvent.files.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-400 mb-1">Files:</p>
                    <ul className="space-y-0.5">
                      {agentEvent.files.map((file, idx) => (
                        <li key={idx} className="text-xs text-gray-300 font-mono">
                          {file}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  {agentEvent.session_id && (
                    <span>Session: {agentEvent.session_id.slice(0, 8)}</span>
                  )}
                  {agentEvent.engine_used && (
                    <span>Engine: {agentEvent.engine_used}</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Refresh Button */}
          {onRefresh && (
            <div className="mt-4 pt-4 border-t border-gray-800">
              <button
                onClick={onRefresh}
                className="w-full px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
              >
                Refresh Work Item
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
