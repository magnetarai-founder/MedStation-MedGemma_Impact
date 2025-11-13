import { useEffect, useState } from 'react'
import { Shield, Check, X, Search, Copy, Download } from 'lucide-react'
import { authFetch } from '../../lib/api'
import { showToast } from '../../lib/toast'

interface EffectivePermissions {
  user_id: string
  role: string
  is_founder: boolean
  team_id: string | null
  effective_permissions: Record<string, boolean | number | string>
}

export default function PermissionsTab() {
  const [permissions, setPermissions] = useState<EffectivePermissions | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadPermissions()
  }, [])

  const loadPermissions = async () => {
    setLoading(true)
    try {
      const response = await authFetch('/api/v1/permissions/effective')
      if (response.ok) {
        const data = await response.json()
        setPermissions(data)
      }
    } catch (error) {
      console.error('Failed to load permissions:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyPermissionsJSON = () => {
    if (!permissions) return

    try {
      const json = JSON.stringify(permissions, null, 2)
      navigator.clipboard.writeText(json)
      showToast.success('Permissions copied to clipboard')
    } catch (error) {
      showToast.error('Failed to copy permissions')
      console.error('Copy failed:', error)
    }
  }

  const downloadPermissionsJSON = () => {
    if (!permissions) return

    try {
      const json = JSON.stringify(permissions, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `permissions_${permissions.user_id}_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      showToast.success('Permissions downloaded')
    } catch (error) {
      showToast.error('Failed to download permissions')
      console.error('Download failed:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500 dark:text-gray-400">Loading permissions...</div>
      </div>
    )
  }

  if (!permissions) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-500">Failed to load permissions</div>
      </div>
    )
  }

  // Filter permissions by search query
  const filteredPerms = Object.entries(permissions.effective_permissions).filter(
    ([key]) => key.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group permissions by category (prefix before first dot)
  const groupedPerms: Record<string, Array<[string, any]>> = {}
  filteredPerms.forEach(([key, value]) => {
    const category = key.split('.')[0]
    if (!groupedPerms[category]) {
      groupedPerms[category] = []
    }
    groupedPerms[category].push([key, value])
  })

  const renderPermissionValue = (value: any) => {
    if (typeof value === 'boolean') {
      return value ? (
        <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
          <Check className="w-4 h-4" />
          <span>Granted</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
          <X className="w-4 h-4" />
          <span>Denied</span>
        </div>
      )
    }
    return <span className="text-blue-600 dark:text-blue-400">{String(value)}</span>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Your Permissions
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            View your effective permissions and role in the system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copyPermissionsJSON}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
            title="Copy permissions JSON to clipboard"
          >
            <Copy className="w-4 h-4" />
            <span>Copy JSON</span>
          </button>
          <button
            onClick={downloadPermissionsJSON}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg transition-colors"
            title="Download permissions as JSON file"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </button>
        </div>
      </div>

      {/* Role Badge */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Role:
              </span>
              <span className="px-2 py-0.5 bg-blue-600 text-white text-xs font-medium rounded uppercase">
                {permissions.role}
              </span>
              {permissions.is_founder && (
                <span className="px-2 py-0.5 bg-yellow-500 text-white text-xs font-medium rounded">
                  FOUNDER (Bypass All)
                </span>
              )}
            </div>
            {permissions.team_id && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Team context: {permissions.team_id}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search permissions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Permissions List */}
      <div className="space-y-4">
        {Object.keys(groupedPerms).length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No permissions found matching "{searchQuery}"
          </div>
        ) : (
          Object.entries(groupedPerms)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([category, perms]) => (
              <div
                key={category}
                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
              >
                <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase">
                    {category}
                  </h3>
                </div>
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {perms
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, value]) => (
                      <div
                        key={key}
                        className="px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-900/50"
                      >
                        <span className="text-sm font-mono text-gray-700 dark:text-gray-300">
                          {key}
                        </span>
                        {renderPermissionValue(value)}
                      </div>
                    ))}
                </div>
              </div>
            ))
        )}
      </div>

      {/* Footer Note */}
      <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
        <strong>Note:</strong> These are your effective permissions based on your role and team
        membership. Founders bypass all permission checks. Contact an administrator to request
        additional permissions.
      </div>
    </div>
  )
}
