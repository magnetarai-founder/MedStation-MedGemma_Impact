import { useState, useEffect } from 'react'
import { Shield, Key, Fingerprint, Users, QrCode, Eye, EyeOff, Copy, Check, AlertCircle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

/**
 * Security Tab
 *
 * Integrates with backend services:
 * - E2E Encryption Service (e2e_encryption_service.py)
 * - Database Encryption Service (database_encryption_service.py)
 * - RBAC Permissions Service (permissions.py)
 */

interface DeviceFingerprint {
  device_id: string
  fingerprint: string
  public_key: string
  created_at: string
}

interface BackupCode {
  code: string
  used: boolean
}

interface User {
  id: string
  username: string
  role: 'super_admin' | 'admin' | 'member' | 'viewer'
  created_at: string
}

export default function SecurityTab() {
  const queryClient = useQueryClient()
  const [showPassphrase, setShowPassphrase] = useState(false)
  const [showBackupCodes, setShowBackupCodes] = useState(false)
  const [copiedFingerprint, setCopiedFingerprint] = useState(false)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // E2E Encryption - Device Fingerprint
  const { data: deviceInfo, isLoading: loadingDevice } = useQuery({
    queryKey: ['e2e-device'],
    queryFn: async () => {
      const response = await fetch('/api/v1/e2e/device')
      if (!response.ok) throw new Error('Failed to load device info')
      return response.json() as Promise<DeviceFingerprint>
    },
  })

  // Database Encryption - Backup Codes
  const { data: backupCodes, isLoading: loadingCodes } = useQuery({
    queryKey: ['backup-codes'],
    queryFn: async () => {
      const response = await fetch('/api/v1/database/backup-codes')
      if (!response.ok) throw new Error('Failed to load backup codes')
      return response.json() as Promise<BackupCode[]>
    },
    enabled: showBackupCodes,
  })

  // RBAC - Current User
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await fetch('/api/v1/users/me')
      if (!response.ok) throw new Error('Failed to load user')
      return response.json() as Promise<User>
    },
  })

  // RBAC - All Users (Admin only)
  const { data: allUsers, isLoading: loadingUsers } = useQuery({
    queryKey: ['all-users'],
    queryFn: async () => {
      const response = await fetch('/api/v1/users')
      if (!response.ok) throw new Error('Failed to load users')
      return response.json() as Promise<User[]>
    },
    enabled: currentUser?.role === 'super_admin' || currentUser?.role === 'admin',
  })

  // Regenerate Backup Codes
  const regenerateCodesMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/v1/database/backup-codes/regenerate', {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to regenerate codes')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup-codes'] })
    },
  })

  // Update User Role
  const updateRoleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      const response = await fetch(`/api/v1/users/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role }),
      })
      if (!response.ok) throw new Error('Failed to update role')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['all-users'] })
    },
  })

  const copyToClipboard = async (text: string, id?: string) => {
    await navigator.clipboard.writeText(text)
    if (id) {
      setCopiedCode(id)
      setTimeout(() => setCopiedCode(null), 2000)
    } else {
      setCopiedFingerprint(true)
      setTimeout(() => setCopiedFingerprint(false), 2000)
    }
  }

  const formatFingerprint = (fingerprint: string) => {
    // Format as: XX:XX:XX:XX:XX:XX...
    return fingerprint.match(/.{1,2}/g)?.join(':') || fingerprint
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'super_admin':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
      case 'admin':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
      case 'member':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      case 'viewer':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
    }
  }

  return (
    <div className="space-y-8">
      {/* E2E Encryption Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Fingerprint className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            End-to-End Encryption
          </h3>
        </div>

        {loadingDevice ? (
          <div className="text-gray-500 dark:text-gray-400">Loading device information...</div>
        ) : deviceInfo ? (
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Device ID
              </div>
              <div className="font-mono text-xs text-gray-600 dark:text-gray-400">
                {deviceInfo.device_id}
              </div>
            </div>

            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Device Fingerprint (SHA-256)
                </div>
                <button
                  onClick={() => copyToClipboard(deviceInfo.fingerprint)}
                  className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                >
                  {copiedFingerprint ? (
                    <Check className="w-4 h-4 text-green-600" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-500" />
                  )}
                </button>
              </div>
              <div className="font-mono text-xs text-gray-600 dark:text-gray-400 break-all">
                {formatFingerprint(deviceInfo.fingerprint)}
              </div>
            </div>

            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800 dark:text-blue-300">
                  <div className="font-medium mb-1">Verify Fingerprints</div>
                  <div>
                    Compare this fingerprint with other devices to ensure secure communication.
                    Messages from unverified devices will show a warning.
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <QrCode className="w-4 h-4" />
              <span>QR code for device linking (UI TODO)</span>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 dark:text-gray-400">
            E2E encryption not configured
          </div>
        )}
      </div>

      {/* Database Encryption Section */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-8">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Database Encryption
          </h3>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Encryption Status
            </div>
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <Shield className="w-4 h-4" />
              <span className="text-sm font-medium">AES-256-GCM Encrypted</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              All databases encrypted at rest with PBKDF2 key derivation (600k iterations)
            </div>
          </div>

          <div>
            <button
              onClick={() => setShowBackupCodes(!showBackupCodes)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              {showBackupCodes ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
              <span className="text-sm font-medium">
                {showBackupCodes ? 'Hide' : 'Show'} Backup Codes
              </span>
            </button>
          </div>

          {showBackupCodes && (
            <div className="space-y-4">
              {loadingCodes ? (
                <div className="text-gray-500 dark:text-gray-400">Loading backup codes...</div>
              ) : backupCodes && backupCodes.length > 0 ? (
                <>
                  <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-yellow-800 dark:text-yellow-300">
                        <div className="font-medium mb-1">SAVE THESE CODES NOW</div>
                        <div>
                          Store these backup codes in a secure location. You can use them to recover
                          access if you forget your passphrase. Each code can only be used once.
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {backupCodes.map((code, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg flex items-center justify-between ${
                          code.used
                            ? 'bg-gray-100 dark:bg-gray-800 opacity-50'
                            : 'bg-gray-50 dark:bg-gray-800'
                        }`}
                      >
                        <span className={`font-mono text-sm ${code.used ? 'line-through' : ''}`}>
                          {code.code}
                        </span>
                        {!code.used && (
                          <button
                            onClick={() => copyToClipboard(code.code, code.code)}
                            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                          >
                            {copiedCode === code.code ? (
                              <Check className="w-4 h-4 text-green-600" />
                            ) : (
                              <Copy className="w-4 h-4 text-gray-500" />
                            )}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => regenerateCodesMutation.mutate()}
                    disabled={regenerateCodesMutation.isPending}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {regenerateCodesMutation.isPending ? 'Regenerating...' : 'Regenerate Codes'}
                  </button>
                </>
              ) : (
                <div className="text-gray-500 dark:text-gray-400">No backup codes available</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* RBAC Section */}
      {(currentUser?.role === 'super_admin' || currentUser?.role === 'admin') && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-8">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              User Roles & Permissions
            </h3>
          </div>

          {loadingUsers ? (
            <div className="text-gray-500 dark:text-gray-400">Loading users...</div>
          ) : allUsers && allUsers.length > 0 ? (
            <div className="space-y-2">
              {allUsers.map((user) => (
                <div
                  key={user.id}
                  className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        {user.username}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {user.id}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(
                        user.role
                      )}`}
                    >
                      {user.role.replace('_', ' ').toUpperCase()}
                    </span>

                    {currentUser?.role === 'super_admin' && user.id !== currentUser.id && (
                      <select
                        value={user.role}
                        onChange={(e) =>
                          updateRoleMutation.mutate({ userId: user.id, role: e.target.value })
                        }
                        disabled={updateRoleMutation.isPending}
                        className="px-3 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                      >
                        <option value="super_admin">Super Admin</option>
                        <option value="admin">Admin</option>
                        <option value="member">Member</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500 dark:text-gray-400">No users found</div>
          )}

          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="text-sm text-blue-800 dark:text-blue-300">
              <div className="font-medium mb-2">Permission Levels:</div>
              <ul className="space-y-1 text-xs">
                <li>
                  <strong>Super Admin:</strong> Full access, can create other admins
                </li>
                <li>
                  <strong>Admin:</strong> Manage users, workflows, and settings (cannot create admins)
                </li>
                <li>
                  <strong>Member:</strong> Create and edit own workflows, access vault
                </li>
                <li>
                  <strong>Viewer:</strong> Read-only access to workflows
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
