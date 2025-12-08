/**
 * WorkflowStatusTracker Component
 * Kanban-style board showing work items across workflow stages
 */

import React from 'react';
import { useWorkItems, useWorkflow } from '../hooks/useWorkflowQueue';
import type { WorkItem } from '../types/workflow';

interface WorkflowStatusTrackerProps {
  workflowId: string;
  onSelectWorkItem?: (workItem: WorkItem) => void;
}

export function WorkflowStatusTracker({ workflowId, onSelectWorkItem }: WorkflowStatusTrackerProps) {
  const { data: workflow } = useWorkflow(workflowId);
  const { data: workItems } = useWorkItems({ workflowId, limit: 100 });

  if (!workflow) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0a0a0a] text-white">
        <div>Loading workflow...</div>
      </div>
    );
  }

  // Group work items by stage
  const itemsByStage = workflow.stages.reduce((acc, stage) => {
    acc[stage.id] = workItems?.filter(item => item.current_stage_id === stage.id) || [];
    return acc;
  }, {} as Record<string, WorkItem[]>);

  const completedItems = workItems?.filter(item => item.status === 'completed') || [];

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'urgent': return 'border-l-4 border-red-500';
      case 'high': return 'border-l-4 border-orange-500';
      case 'normal': return 'border-l-4 border-blue-500';
      case 'low': return 'border-l-4 border-gray-500';
      default: return '';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span>📊</span> {workflow.name}
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          {workItems?.length || 0} active items • {completedItems.length} completed
        </p>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-4">
        <div className="flex gap-4 h-full min-w-max">
          {/* Stage Columns */}
          {workflow.stages
            .sort((a, b) => a.order - b.order)
            .map((stage) => {
              const items = itemsByStage[stage.id] || [];

              return (
                <div
                  key={stage.id}
                  className="flex flex-col w-80 bg-gray-900 rounded-lg border border-gray-800"
                >
                  {/* Column Header */}
                  <div className="p-4 border-b border-gray-800">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{stage.name}</h3>
                      <span className="px-2 py-1 bg-gray-800 rounded text-sm">
                        {items.length}
                      </span>
                    </div>
                    {stage.description && (
                      <p className="text-xs text-gray-400">{stage.description}</p>
                    )}
                    {stage.sla_minutes && (
                      <div className="text-xs text-gray-500 mt-1">
                        ⏱️ SLA: {stage.sla_minutes}min
                      </div>
                    )}
                  </div>

                  {/* Column Items */}
                  <div className="flex-1 overflow-y-auto p-3 space-y-2">
                    {items.length === 0 ? (
                      <div className="text-center text-gray-500 text-sm mt-8">
                        No items
                      </div>
                    ) : (
                      items.map((item) => (
                        <div
                          key={item.id}
                          onClick={() => onSelectWorkItem?.(item)}
                          className={`bg-gray-800 rounded-lg p-3 cursor-pointer hover:bg-gray-750 transition-colors ${getPriorityColor(item.priority)}`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="text-sm font-medium">
                              {item.reference_number || item.id.slice(0, 8)}
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className={`text-xs px-1.5 py-0.5 rounded ${
                                item.status === 'in_progress'
                                  ? 'bg-blue-900 text-blue-200'
                                  : item.status === 'claimed'
                                  ? 'bg-green-900 text-green-200'
                                  : 'bg-gray-700 text-gray-300'
                              }`}>
                                {item.status.replace('_', ' ')}
                              </span>
                              {item.is_overdue && (
                                <span className="text-xs px-1.5 py-0.5 rounded bg-red-900 text-red-200">
                                  Overdue
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Data Preview */}
                          {Object.keys(item.data).length > 0 && (
                            <div className="text-xs text-gray-400 space-y-1">
                              {Object.entries(item.data).slice(0, 2).map(([key, value]) => (
                                <div key={key} className="truncate">
                                  <span className="text-gray-500">{key}:</span> {String(value)}
                                </div>
                              ))}
                            </div>
                          )}

                          {item.assigned_to && (
                            <div className="text-xs text-gray-500 mt-2">
                              👤 {item.assigned_to}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}

          {/* Completed Column */}
          <div className="flex flex-col w-80 bg-gray-900 rounded-lg border border-gray-800">
            <div className="p-4 border-b border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold flex items-center gap-2">
                  <span>✅</span> Completed
                </h3>
                <span className="px-2 py-1 bg-gray-800 rounded text-sm">
                  {completedItems.length}
                </span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {completedItems.length === 0 ? (
                <div className="text-center text-gray-500 text-sm mt-8">
                  No completed items
                </div>
              ) : (
                completedItems.slice(0, 20).map((item) => (
                  <div
                    key={item.id}
                    onClick={() => onSelectWorkItem?.(item)}
                    className="bg-gray-800 rounded-lg p-3 cursor-pointer hover:bg-gray-750 transition-colors border-l-4 border-green-500"
                  >
                    <div className="text-sm font-medium mb-1">
                      {item.reference_number || item.id.slice(0, 8)}
                    </div>
                    <div className="text-xs text-gray-400">
                      {item.completed_at &&
                        new Date(item.completed_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
