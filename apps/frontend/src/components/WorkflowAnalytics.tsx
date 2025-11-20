/**
 * Workflow Analytics Component (Phase D)
 * Displays comprehensive analytics for a workflow
 */

import { TrendingUp, Clock, CheckCircle, XCircle, Loader2, AlertCircle, BarChart3, PlayCircle } from 'lucide-react'
import { useWorkflowAnalytics } from '@/hooks/useWorkflowQueue'
import type { WorkflowAnalytics as AnalyticsType, WorkflowStageAnalytics } from '@/types/workflow'

interface WorkflowAnalyticsProps {
  workflowId: string
}

// Format seconds into human-readable duration
function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined || seconds === 0) {
    return '—'
  }

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)
  if (secs > 0 && days === 0) parts.push(`${secs}s`)

  return parts.length > 0 ? parts.join(' ') : '—'
}

export function WorkflowAnalytics({ workflowId }: WorkflowAnalyticsProps) {
  const { data: analytics, isLoading, error, refetch } = useWorkflowAnalytics(workflowId)

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full w-full flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary-600 dark:text-primary-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading analytics...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Failed to load analytics
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  // Empty state - no data yet
  if (!analytics || analytics.total_items === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <BarChart3 className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            No analytics yet
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            This workflow has no historical data. Create and complete work items to see analytics.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full p-6 overflow-y-auto bg-gray-50/30 dark:bg-gray-900/30">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Workflow Analytics
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {analytics.workflow_name}
          </p>
        </div>

        {/* Overall Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Items */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Total Items</span>
              <PlayCircle className="w-4 h-4 text-gray-400" />
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {analytics.total_items}
            </p>
          </div>

          {/* Completed Items */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Completed</span>
              <CheckCircle className="w-4 h-4 text-green-500" />
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {analytics.completed_items}
              </p>
              {analytics.total_items > 0 && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  ({Math.round((analytics.completed_items / analytics.total_items) * 100)}%)
                </span>
              )}
            </div>
          </div>

          {/* In Progress */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">In Progress</span>
              <TrendingUp className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {analytics.in_progress_items}
            </p>
          </div>

          {/* Average Cycle Time */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">Avg Cycle Time</span>
              <Clock className="w-4 h-4 text-purple-500" />
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {formatDuration(analytics.average_cycle_time_seconds)}
            </p>
            {analytics.median_cycle_time_seconds !== null && analytics.median_cycle_time_seconds !== analytics.average_cycle_time_seconds && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Median: {formatDuration(analytics.median_cycle_time_seconds)}
              </p>
            )}
          </div>
        </div>

        {/* Additional Status Cards */}
        {(analytics.cancelled_items > 0 || analytics.failed_items > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analytics.cancelled_items > 0 && (
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Cancelled</span>
                  <XCircle className="w-4 h-4 text-gray-400" />
                </div>
                <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {analytics.cancelled_items}
                </p>
              </div>
            )}

            {analytics.failed_items > 0 && (
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Failed</span>
                  <XCircle className="w-4 h-4 text-red-500" />
                </div>
                <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {analytics.failed_items}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Stage-Level Metrics */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Stage Performance
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Metrics for each stage in the workflow
            </p>
          </div>

          {analytics.stages && analytics.stages.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Stage
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Entered
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Completed
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Avg Time
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Median Time
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {analytics.stages.map((stage) => (
                    <tr
                      key={stage.stage_id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors"
                    >
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">
                        {stage.stage_name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">
                        {stage.entered_count}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">
                        {stage.completed_count}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">
                        {formatDuration(stage.avg_time_seconds)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">
                        {formatDuration(stage.median_time_seconds)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No stage data available
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
