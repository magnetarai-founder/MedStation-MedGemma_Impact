/**
 * Analytics Tab - Sprint 6 Theme A (Ticket A4)
 *
 * Dashboard for viewing usage analytics with charts and exports
 */

import { useState, useEffect } from 'react'
import { Download, BarChart3, TrendingUp, Activity, AlertCircle, Copy, Check } from 'lucide-react'
import {
  fetchAnalyticsUsage,
  exportAnalytics,
  downloadExportedFile,
  formatDateRangeLabel,
  type DateRange,
  type AnalyticsSummary
} from '../../lib/analyticsApi'
import { showToast } from '../../lib/toast'

export default function AnalyticsTab() {
  const [range, setRange] = useState<DateRange>('7d')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [exporting, setExporting] = useState(false)
  const [copiedChart, setCopiedChart] = useState<string | null>(null)

  useEffect(() => {
    loadAnalytics()
  }, [range])

  const loadAnalytics = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetchAnalyticsUsage(range)
      setData(response.data)
    } catch (err: any) {
      const errorMsg = err.message || 'Failed to load analytics'
      setError(errorMsg)

      // Check if it's a permission error
      if (errorMsg.includes('403') || errorMsg.includes('permission')) {
        setError('You do not have permission to view analytics. Only admins and founders can access this feature.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: 'json' | 'csv') => {
    setExporting(true)

    try {
      const blob = await exportAnalytics(format, range)
      const filename = `analytics-${range}-${new Date().toISOString().split('T')[0]}.${format}`
      downloadExportedFile(blob, filename)

      showToast.success(`Analytics exported as ${format.toUpperCase()}`)
    } catch (err: any) {
      showToast.error(err.message || 'Failed to export analytics')
    } finally {
      setExporting(false)
    }
  }

  const handleCopyChartData = (chartName: string, chartData: any[]) => {
    try {
      const text = JSON.stringify(chartData, null, 2)
      navigator.clipboard.writeText(text)
      setCopiedChart(chartName)
      setTimeout(() => setCopiedChart(null), 2000)
      showToast.success(`${chartName} data copied to clipboard`)
    } catch (err) {
      showToast.error('Failed to copy data')
    }
  }

  // Calculate totals
  const totalTokens = data?.tokens_trend.reduce((sum, point) => sum + (point.tokens || 0), 0) || 0
  const totalSessions = data?.sessions_trend.reduce((sum, point) => sum + (point.sessions || 0), 0) || 0
  const totalErrors = data?.errors_trend.reduce((sum, point) => sum + (point.errors || 0), 0) || 0
  const maxTokens = Math.max(...(data?.tokens_trend.map(p => p.tokens || 0) || [1]))
  const maxSessions = Math.max(...(data?.sessions_trend.map(p => p.sessions || 0) || [1]))
  const maxErrors = Math.max(...(data?.errors_trend.map(p => p.errors || 0) || [1]))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Analytics Dashboard
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            View usage patterns, trends, and system metrics
          </p>
          {data && !loading && !error && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
              Data updated: {new Date().toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
              })}
            </p>
          )}
        </div>

        {/* Export Buttons */}
        {data && !error && (
          <div className="flex gap-2">
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              aria-label="Export as JSON"
            >
              <Download size={16} />
              <span className="text-sm">JSON</span>
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              aria-label="Export as CSV"
            >
              <Download size={16} />
              <span className="text-sm">CSV</span>
            </button>
          </div>
        )}
      </div>

      {/* Date Range Selector */}
      <div className="flex gap-2" role="group" aria-label="Date range selector">
        {(['7d', '30d', '90d'] as DateRange[]).map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              range === r
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
            aria-label={`View ${formatDateRangeLabel(r)}`}
            aria-pressed={range === r}
          >
            {formatDateRangeLabel(r)}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600 dark:text-gray-400">Loading analytics...</span>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                Unable to load analytics
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Dashboard Content */}
      {data && !loading && !error && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Tokens</p>
                  <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {totalTokens.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Activity className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Sessions</p>
                  <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {totalSessions.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Errors</p>
                  <p className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {totalErrors.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Model Usage */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <BarChart3 size={20} />
                  Model Usage
                </h3>
                <button
                  onClick={() => handleCopyChartData('Model Usage', data.model_usage)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy chart data"
                >
                  {copiedChart === 'Model Usage' ? <Check size={16} /> : <Copy size={16} />}
                </button>
              </div>
              {data.model_usage.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No model usage data
                </p>
              ) : (
                <div className="space-y-3" role="list" aria-label="Model usage distribution">
                  {data.model_usage.map((model, idx) => {
                    const percentage = totalTokens > 0 ? (model.total_tokens / totalTokens) * 100 : 0
                    return (
                      <div key={model.model_name || idx} role="listitem">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="font-medium text-gray-700 dark:text-gray-300 truncate">
                            {model.model_name || 'Unknown'}
                          </span>
                          <span className="text-gray-500 dark:text-gray-400 ml-2">
                            {model.total_tokens.toLocaleString()} tokens
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-blue-600 h-full transition-all duration-300"
                            style={{ width: `${percentage}%` }}
                            role="progressbar"
                            aria-valuenow={percentage}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`${model.model_name} usage: ${percentage.toFixed(1)}%`}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Daily Tokens Trend */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <TrendingUp size={20} />
                  Daily Tokens
                </h3>
                <button
                  onClick={() => handleCopyChartData('Daily Tokens', data.tokens_trend)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy chart data"
                >
                  {copiedChart === 'Daily Tokens' ? <Check size={16} /> : <Copy size={16} />}
                </button>
              </div>
              {data.tokens_trend.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No token data
                </p>
              ) : (
                <div className="space-y-2" role="img" aria-label="Daily tokens bar chart">
                  {data.tokens_trend.map((point, idx) => {
                    const height = maxTokens > 0 ? ((point.tokens || 0) / maxTokens) * 100 : 0
                    return (
                      <div key={point.date || idx} className="flex items-end gap-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400 w-16 flex-shrink-0">
                          {new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden relative">
                          <div
                            className="bg-blue-600 h-full transition-all duration-300"
                            style={{ width: `${height}%` }}
                            title={`${point.tokens?.toLocaleString() || 0} tokens`}
                          />
                        </div>
                        <span className="text-xs text-gray-600 dark:text-gray-400 w-16 text-right">
                          {(point.tokens || 0).toLocaleString()}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Sessions Trend */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <Activity size={20} />
                  Sessions per Day
                </h3>
                <button
                  onClick={() => handleCopyChartData('Sessions', data.sessions_trend)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy chart data"
                >
                  {copiedChart === 'Sessions' ? <Check size={16} /> : <Copy size={16} />}
                </button>
              </div>
              {data.sessions_trend.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No session data
                </p>
              ) : (
                <div className="space-y-2" role="img" aria-label="Daily sessions bar chart">
                  {data.sessions_trend.map((point, idx) => {
                    const height = maxSessions > 0 ? ((point.sessions || 0) / maxSessions) * 100 : 0
                    return (
                      <div key={point.date || idx} className="flex items-end gap-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400 w-16 flex-shrink-0">
                          {new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden relative">
                          <div
                            className="bg-green-600 h-full transition-all duration-300"
                            style={{ width: `${height}%` }}
                            title={`${point.sessions || 0} sessions`}
                          />
                        </div>
                        <span className="text-xs text-gray-600 dark:text-gray-400 w-16 text-right">
                          {point.sessions || 0}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Error Rate */}
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                  <AlertCircle size={20} />
                  Error Rate
                </h3>
                <button
                  onClick={() => handleCopyChartData('Error Rate', data.errors_trend)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy chart data"
                >
                  {copiedChart === 'Error Rate' ? <Check size={16} /> : <Copy size={16} />}
                </button>
              </div>
              {data.errors_trend.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No error data
                </p>
              ) : (
                <div className="space-y-2" role="img" aria-label="Daily errors bar chart">
                  {data.errors_trend.map((point, idx) => {
                    const height = maxErrors > 0 ? ((point.errors || 0) / maxErrors) * 100 : 0
                    return (
                      <div key={point.date || idx} className="flex items-end gap-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400 w-16 flex-shrink-0">
                          {new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden relative">
                          <div
                            className="bg-red-600 h-full transition-all duration-300"
                            style={{ width: `${height}%` }}
                            title={`${point.errors || 0} errors`}
                          />
                        </div>
                        <span className="text-xs text-gray-600 dark:text-gray-400 w-16 text-right">
                          {point.errors || 0}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Leaderboards */}
          {(data.top_users.length > 0 || data.top_teams.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Users */}
              {data.top_users.length > 0 && (
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Top Users
                  </h3>
                  <div className="space-y-2" role="list" aria-label="Top users by activity">
                    {data.top_users.map((user, idx) => (
                      <div
                        key={user.user_id || idx}
                        className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                        role="listitem"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-500 dark:text-gray-400 w-6">
                            #{idx + 1}
                          </span>
                          <span className="text-sm text-gray-900 dark:text-gray-100 font-medium">
                            {user.user_id}
                          </span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            {user.calls.toLocaleString()} calls
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {user.tokens.toLocaleString()} tokens
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Teams */}
              {data.top_teams.length > 0 && (
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                    Top Teams
                  </h3>
                  <div className="space-y-2" role="list" aria-label="Top teams by activity">
                    {data.top_teams.map((team, idx) => (
                      <div
                        key={team.team_id || idx}
                        className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                        role="listitem"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-500 dark:text-gray-400 w-6">
                            #{idx + 1}
                          </span>
                          <span className="text-sm text-gray-900 dark:text-gray-100 font-medium">
                            {team.team_id}
                          </span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            {team.calls.toLocaleString()} calls
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {team.tokens.toLocaleString()} tokens
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
