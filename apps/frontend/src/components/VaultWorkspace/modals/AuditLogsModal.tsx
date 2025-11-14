import { useState, useEffect } from 'react'
import { Activity, X } from 'lucide-react'
import axios from 'axios'
import { toast } from 'sonner'

interface AuditLogsModalProps {
  isOpen: boolean
  vaultMode: string
  onClose: () => void
}

export function AuditLogsModal({ isOpen, vaultMode, onClose }: AuditLogsModalProps) {
  const [auditLogs, setAuditLogs] = useState<Array<any>>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadAuditLogs()
    }
  }, [isOpen])

  const loadAuditLogs = async () => {
    setIsLoading(true)
    try {
      const response = await axios.get('/api/v1/vault/audit-logs', {
        params: { vault_type: vaultMode, limit: 50 }
      })
      setAuditLogs(response.data.logs)
    } catch (error) {
      console.error('Failed to load audit logs:', error)
      toast.error('Failed to load audit logs')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[800px] max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <Activity className="w-5 h-5" />
            Audit Log Timeline
          </h3>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Audit Logs List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <Activity className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse" />
              <p>Loading audit logs...</p>
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <Activity className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>No activity logs</p>
            </div>
          ) : (
            <div className="space-y-3">
              {auditLogs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700"
                >
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-gray-100">{log.action}</span>
                      <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-zinc-700 rounded text-gray-700 dark:text-gray-300">
                        {log.resource_type}
                      </span>
                    </div>
                    {log.details && (
                      <p className="text-sm text-gray-600 dark:text-zinc-500 mt-1">{log.details}</p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                      {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
