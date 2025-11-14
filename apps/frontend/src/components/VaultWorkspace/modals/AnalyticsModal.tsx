import { useState, useEffect } from 'react'
import { BarChart3, X, TrendingUp, Activity, Clock } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface AnalyticsModalProps {
  isOpen: boolean
  vaultMode: string
  onClose: () => void
}

export function AnalyticsModal({ isOpen, vaultMode, onClose }: AnalyticsModalProps) {
  const [analyticsData, setAnalyticsData] = useState<any>({
    storageTrends: null,
    accessPatterns: null,
    activityTimeline: null
  })
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadAnalytics()
    }
  }, [isOpen])

  const loadAnalytics = async () => {
    setIsLoading(true)
    try {
      const [storageTrends, accessPatterns, activityTimeline] = await Promise.all([
        axios.get('/api/v1/vault/analytics/storage-trends', {
          params: { vault_type: vaultMode, days: 30 }
        }),
        axios.get('/api/v1/vault/analytics/access-patterns', {
          params: { vault_type: vaultMode, limit: 10 }
        }),
        axios.get('/api/v1/vault/analytics/activity-timeline', {
          params: { vault_type: vaultMode, hours: 24, limit: 50 }
        })
      ])

      setAnalyticsData({
        storageTrends: storageTrends.data,
        accessPatterns: accessPatterns.data,
        activityTimeline: activityTimeline.data
      })
    } catch (error) {
      console.error('Failed to load analytics:', error)
      toast.error('Failed to load analytics data')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[900px] max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <BarChart3 className="w-5 h-5" />
            Vault Analytics & Insights
          </h3>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse" />
              <p>Loading analytics...</p>
            </div>
          ) : (
            <>
              {/* Storage Trends */}
              {analyticsData.storageTrends && (
                <div className="mb-6">
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <TrendingUp className="w-5 h-5" />
                    Storage Trends (Last 30 Days)
                  </h4>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <div className="text-sm text-blue-700 dark:text-blue-300 mb-1">Total Files</div>
                      <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                        {analyticsData.storageTrends.total_files}
                      </div>
                    </div>
                    <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                      <div className="text-sm text-purple-700 dark:text-purple-300 mb-1">Total Storage</div>
                      <div className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                        {(analyticsData.storageTrends.total_bytes / (1024 * 1024)).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  {analyticsData.storageTrends.trends.length > 0 ? (
                    <div className="space-y-2">
                      {analyticsData.storageTrends.trends.slice(0, 5).map((trend: any) => (
                        <div key={trend.date} className="flex items-center justify-between p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{trend.date}</span>
                          <div className="flex gap-4 text-sm">
                            <span className="text-blue-600 dark:text-blue-400">{trend.files_added} files</span>
                            <span className="text-purple-600 dark:text-purple-400">
                              +{(trend.bytes_added / (1024 * 1024)).toFixed(2)} MB
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No storage activity in the last 30 days</p>
                  )}
                </div>
              )}

              {/* Access Patterns */}
              {analyticsData.accessPatterns && (
                <div className="mb-6">
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <Activity className="w-5 h-5" />
                    Access Patterns
                  </h4>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-center">
                      <div className="text-sm text-green-700 dark:text-green-300 mb-1">Views</div>
                      <div className="text-xl font-bold text-green-900 dark:text-green-100">
                        {analyticsData.accessPatterns.access_by_type?.view || 0}
                      </div>
                    </div>
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-center">
                      <div className="text-sm text-orange-700 dark:text-orange-300 mb-1">Downloads</div>
                      <div className="text-xl font-bold text-orange-900 dark:text-orange-100">
                        {analyticsData.accessPatterns.access_by_type?.download || 0}
                      </div>
                    </div>
                    <div className="p-4 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg text-center">
                      <div className="text-sm text-teal-700 dark:text-teal-300 mb-1">Last 24h</div>
                      <div className="text-xl font-bold text-teal-900 dark:text-teal-100">
                        {analyticsData.accessPatterns.recent_access_24h}
                      </div>
                    </div>
                  </div>
                  <h5 className="text-md font-semibold mb-2 text-gray-900 dark:text-gray-100">Most Accessed Files</h5>
                  {analyticsData.accessPatterns.most_accessed.length > 0 ? (
                    <div className="space-y-2">
                      {analyticsData.accessPatterns.most_accessed.slice(0, 5).map((file: any) => (
                        <div key={file.id} className="flex items-center justify-between p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <div className="flex-1 truncate">
                            <div className="font-medium text-gray-900 dark:text-gray-100 truncate">{file.filename}</div>
                            <div className="text-xs text-gray-600 dark:text-gray-400">
                              {(file.file_size / 1024).toFixed(2)} KB • {file.mime_type}
                            </div>
                          </div>
                          <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 ml-4">
                            {file.access_count} accesses
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No file access recorded yet</p>
                  )}
                </div>
              )}

              {/* Activity Timeline */}
              {analyticsData.activityTimeline && (
                <div>
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <Clock className="w-5 h-5" />
                    Recent Activity (Last 24 Hours)
                  </h4>
                  {Object.keys(analyticsData.activityTimeline.action_summary).length > 0 && (
                    <div className="grid grid-cols-4 gap-2 mb-4">
                      {Object.entries(analyticsData.activityTimeline.action_summary).map(([action, count]: [string, any]) => (
                        <div key={action} className="p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 text-center">
                          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 truncate">{action}</div>
                          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{count}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {analyticsData.activityTimeline.activities.length > 0 ? (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {analyticsData.activityTimeline.activities.slice(0, 10).map((activity: any, index: number) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <div className="flex-shrink-0 mt-1">
                            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900 dark:text-gray-100">{activity.action}</span>
                              <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-zinc-700 rounded text-gray-700 dark:text-gray-300 truncate">
                                {activity.resource_type}
                              </span>
                            </div>
                            {activity.details && (
                              <p className="text-sm text-gray-600 dark:text-zinc-500 mt-1">{activity.details}</p>
                            )}
                            <p className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                              {new Date(activity.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No recent activity</p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
