/**
 * WorkflowQueue Component
 * My Work dashboard - shows queue of work items for a role
 */

import React, { useState } from 'react';
import { useMyActiveWork, useQueueForRole, useClaimWorkItem, useStartWork } from '../hooks/useWorkflowQueue';
import type { WorkItem, WorkItemPriority } from '../types/workflow';

interface WorkflowQueueProps {
  userId: string;
  userName: string;
  role?: string;
  workflowId?: string;
  onSelectWorkItem?: (workItem: WorkItem) => void;
}

export function WorkflowQueue({ userId, userName, role, workflowId, onSelectWorkItem }: WorkflowQueueProps) {
  const [view, setView] = useState<'my-work' | 'queue'>('my-work');
  const [selectedPriority, setSelectedPriority] = useState<WorkItemPriority | 'all'>('all');

  const { data: myWork, isLoading: loadingMyWork } = useMyActiveWork(userId);
  const { data: queueItems, isLoading: loadingQueue } = useQueueForRole(
    workflowId || '',
    role || '',
    undefined
  );

  const claimMutation = useClaimWorkItem();
  const startMutation = useStartWork();

  const handleClaimAndStart = async (workItem: WorkItem) => {
    try {
      // Claim the item
      const claimed = await claimMutation.mutateAsync({
        workItemId: workItem.id,
        userId,
      });

      // Start working on it
      await startMutation.mutateAsync({
        workItemId: claimed.id,
        userId,
      });

      // Open detail view
      if (onSelectWorkItem) {
        onSelectWorkItem(claimed);
      }
    } catch (error) {
      console.error('Failed to claim/start work item:', error);
      alert(error instanceof Error ? error.message : 'Failed to claim work item');
    }
  };

  const getPriorityColor = (priority: WorkItemPriority): string => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'normal':
        return 'bg-blue-500';
      case 'low':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getPriorityIcon = (priority: WorkItemPriority): string => {
    switch (priority) {
      case 'urgent':
        return '🚨';
      case 'high':
        return '⚠️';
      case 'normal':
        return '📋';
      case 'low':
        return '📝';
      default:
        return '📋';
    }
  };

  const formatTimeAgo = (date: string): string => {
    const now = new Date();
    const created = new Date(date);
    const diffMs = now.getTime() - created.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const currentItems = view === 'my-work' ? myWork : queueItems;
  const isLoading = view === 'my-work' ? loadingMyWork : loadingQueue;

  const filteredItems = currentItems?.filter(item => {
    if (selectedPriority === 'all') return true;
    return item.priority === selectedPriority;
  }) || [];

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-white">
            {view === 'my-work' ? '📌 My Active Work' : '📋 Available Queue'}
          </h2>
          <span className="text-sm text-gray-400">
            {userName} {role && `• ${role}`}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setView('my-work')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                view === 'my-work'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              My Work ({myWork?.length || 0})
            </button>
            <button
              onClick={() => setView('queue')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                view === 'queue'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
              disabled={!role || !workflowId}
            >
              Queue ({queueItems?.length || 0})
            </button>
          </div>

          {/* Priority Filter */}
          <select
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value as WorkItemPriority | 'all')}
            className="px-3 py-2 bg-gray-800 text-white rounded-lg text-sm border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Priorities</option>
            <option value="urgent">🚨 Urgent</option>
            <option value="high">⚠️ High</option>
            <option value="normal">📋 Normal</option>
            <option value="low">📝 Low</option>
          </select>
        </div>
      </div>

      {/* Work Items List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-400">Loading...</div>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <div className="text-6xl mb-4">
              {view === 'my-work' ? '✅' : '📭'}
            </div>
            <div className="text-lg font-medium mb-2">
              {view === 'my-work' ? 'No active work' : 'Queue is empty'}
            </div>
            <div className="text-sm">
              {view === 'my-work'
                ? 'Claim items from the queue to get started'
                : 'Check back later for new items'}
            </div>
          </div>
        ) : (
          <div className="grid gap-3">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-blue-500 transition-colors cursor-pointer"
                onClick={() => {
                  if (view === 'my-work' && onSelectWorkItem) {
                    onSelectWorkItem(item);
                  }
                }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getPriorityIcon(item.priority)}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-white">
                          {item.reference_number || item.id.slice(0, 8)}
                        </h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(item.priority)} text-white`}>
                          {item.priority}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 mt-1">
                        {item.workflow_name} • {item.current_stage_name}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-xs px-2 py-1 rounded ${
                      item.status === 'in_progress'
                        ? 'bg-blue-900 text-blue-200'
                        : item.status === 'claimed'
                        ? 'bg-green-900 text-green-200'
                        : 'bg-gray-800 text-gray-300'
                    }`}>
                      {item.status.replace('_', ' ')}
                    </span>
                    {item.is_overdue && (
                      <span className="text-xs px-2 py-1 rounded bg-red-900 text-red-200">
                        ⏰ Overdue
                      </span>
                    )}
                  </div>
                </div>

                {/* Data Preview */}
                {Object.keys(item.data).length > 0 && (
                  <div className="mb-3 p-3 bg-gray-800 rounded text-sm">
                    {Object.entries(item.data).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2 text-gray-300">
                        <span className="text-gray-500">{key}:</span>
                        <span className="text-white">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Created {formatTimeAgo(item.created_at)}</span>

                  {view === 'queue' ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClaimAndStart(item);
                      }}
                      disabled={claimMutation.isPending || startMutation.isPending}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {claimMutation.isPending || startMutation.isPending ? 'Claiming...' : '✋ Claim & Start'}
                    </button>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onSelectWorkItem) onSelectWorkItem(item);
                      }}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Continue →
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
