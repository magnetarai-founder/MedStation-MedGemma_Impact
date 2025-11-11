/**
 * Audit Log Viewer
 *
 * "The Lord is my rock" - Psalm 18:2
 *
 * Permission audit log viewer for compliance and security monitoring.
 * Displays permission changes, grants, revocations, and check denials.
 *
 * Features:
 * - Real-time audit log display
 * - Filtering by user, action, resource
 * - Date range filtering
 * - Pagination
 * - Export to CSV
 * - Color-coded action types
 *
 * Integrates with audit_logger.py backend.
 */

import { useState, useEffect } from 'react'
import {
  Shield,
  Search,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info
} from 'lucide-react'

interface AuditEntry {
  id: number
  user_id: string
  action: string
  resource: string | null
  resource_id: string | null
  ip_address: string | null
  user_agent: string | null
  timestamp: string
  details: any
}

export default function AuditLogViewer() {
  const [logs, setLogs] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [userFilter, setUserFilter] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [resourceFilter, setResourceFilter] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // Pagination
  const [page, setPage] = useState(1)
  const [limit] = useState(50)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    fetchAuditLogs()
  }, [page, userFilter, actionFilter, resourceFilter, startDate, endDate])

  const fetchAuditLogs = async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: ((page - 1) * limit).toString()
      })

      if (userFilter) params.append('user_id', userFilter)
      if (actionFilter) params.append('action', actionFilter)
      if (resourceFilter) params.append('resource', resourceFilter)
      if (startDate) params.append('start_date', new Date(startDate).toISOString())
      if (endDate) params.append('end_date', new Date(endDate).toISOString())

      const response = await fetch(`/api/v1/admin/audit-logs?${params}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access denied: Admin privileges required')
        }
        throw new Error('Failed to fetch audit logs')
      }

      const data = await response.json()
      setLogs(data.logs || [])
      setTotal(data.total || 0)

    } catch (err: any) {
      console.error('Failed to fetch audit logs:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getActionColor = (action: string) => {
    if (action.includes('granted') || action.includes('check.granted')) {
      return 'text-green-500'
    }
    if (action.includes('revoked') || action.includes('denied')) {
      return 'text-red-500'
    }
    if (action.includes('modified')) {
      return 'text-yellow-500'
    }
    return 'text-blue-500'
  }

  const getActionIcon = (action: string) => {
    if (action.includes('granted')) {
      return <CheckCircle className="w-4 h-4" />
    }
    if (action.includes('revoked') || action.includes('denied')) {
      return <XCircle className="w-4 h-4" />
    }
    if (action.includes('modified')) {
      return <AlertCircle className="w-4 h-4" />
    }
    return <Info className="w-4 h-4" />
  }

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const handleExport = () => {
    // TODO: Implement CSV export via backend endpoint
    console.log('Export functionality to be implemented')
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-500" />
            Audit Logs
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Permission changes and security events
          </p>
        </div>
        <button
          onClick={handleExport}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-gray-400" />
          <h3 className="text-white font-semibold">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">User ID</label>
            <input
              type="text"
              value={userFilter}
              onChange={(e) => { setUserFilter(e.target.value); setPage(1) }}
              placeholder="Filter by user..."
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Action</label>
            <select
              value={actionFilter}
              onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
            >
              <option value="">All actions</option>
              <option value="permission.granted">Permission Granted</option>
              <option value="permission.revoked">Permission Revoked</option>
              <option value="permission.modified">Permission Modified</option>
              <option value="profile.granted">Profile Granted</option>
              <option value="profile.revoked">Profile Revoked</option>
              <option value="permission_set.granted">Permission Set Granted</option>
              <option value="permission_set.revoked">Permission Set Revoked</option>
              <option value="permission.check.denied">Check Denied</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Resource</label>
            <input
              type="text"
              value={resourceFilter}
              onChange={(e) => { setResourceFilter(e.target.value); setPage(1) }}
              placeholder="Filter by resource..."
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1) }}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1) }}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
            />
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-500">
            <AlertCircle className="w-5 h-5" />
            <span className="font-semibold">Error</span>
          </div>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <Shield className="w-12 h-12 mb-2 opacity-50" />
            <p>No audit logs found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900 border-b border-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Timestamp</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-700/50">
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {formatDate(log.timestamp)}
                    </td>
                    <td className="px-4 py-3 text-sm text-white">
                      {log.user_id}
                    </td>
                    <td className="px-4 py-3">
                      <div className={`flex items-center gap-2 text-sm ${getActionColor(log.action)}`}>
                        {getActionIcon(log.action)}
                        <span>{log.action}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {log.resource || '-'}
                      {log.resource_id && (
                        <span className="text-xs text-gray-500 ml-1">
                          ({log.resource_id})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {log.details ? (
                        <div className="max-w-md truncate" title={JSON.stringify(log.details, null, 2)}>
                          {JSON.stringify(log.details)}
                        </div>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-400">
            Showing {((page - 1) * limit) + 1} - {Math.min(page * limit, total)} of {total} logs
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded flex items-center gap-1"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>
            <span className="text-sm text-gray-400">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded flex items-center gap-1"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
