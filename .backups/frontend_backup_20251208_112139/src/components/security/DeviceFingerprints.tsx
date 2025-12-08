/**
 * Device Fingerprints Component
 *
 * Displays all linked devices with their cryptographic fingerprints
 * Allows users to verify device identities and revoke access
 */

import { useState, useEffect } from 'react'
import { Smartphone, Monitor, Tablet, Trash2, Shield, Clock, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

interface Device {
  id: string
  name: string
  device_type: 'desktop' | 'mobile' | 'tablet'
  fingerprint: string
  last_seen: string
  created_at: string
  is_current: boolean
}

export function DeviceFingerprints() {
  const [devices, setDevices] = useState<Device[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    loadDevices()
  }, [])

  async function loadDevices() {
    setIsLoading(true)
    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/v1/devices/linked')
      // const data = await response.json()

      // Mock data for now
      const mockDevices: Device[] = [
        {
          id: '1',
          name: 'MacBook Pro',
          device_type: 'desktop',
          fingerprint: 'A3:4F:2C:9E:1B:7D:8A:5C:3F:6E:2D:9B:4A:7C:1E:8F',
          last_seen: new Date().toISOString(),
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          is_current: true,
        },
        {
          id: '2',
          name: 'iPhone 14',
          device_type: 'mobile',
          fingerprint: 'B7:3A:9F:2E:6D:1C:5B:8A:4F:7E:3D:2C:9B:6A:5F:1E',
          last_seen: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          is_current: false,
        },
      ]

      setDevices(mockDevices)
    } catch (error) {
      console.error('Failed to load devices:', error)
      toast.error('Failed to load linked devices')
    } finally {
      setIsLoading(false)
    }
  }

  async function revokeDevice(deviceId: string, deviceName: string) {
    if (!confirm(`Are you sure you want to revoke access for "${deviceName}"? This device will need to re-link to access your vault.`)) {
      return
    }

    setDeletingId(deviceId)
    toast.loading('Revoking device access...', { id: 'revoke-device' })

    try {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/devices/${deviceId}`, { method: 'DELETE' })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))

      setDevices(devices.filter(d => d.id !== deviceId))
      toast.success('Device access revoked', { id: 'revoke-device' })
    } catch (error) {
      console.error('Failed to revoke device:', error)
      toast.error('Failed to revoke device access', { id: 'revoke-device' })
    } finally {
      setDeletingId(null)
    }
  }

  function getDeviceIcon(type: Device['device_type']) {
    switch (type) {
      case 'desktop':
        return Monitor
      case 'mobile':
        return Smartphone
      case 'tablet':
        return Tablet
      default:
        return Monitor
    }
  }

  function formatDate(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`

    return date.toLocaleDateString()
  }

  function formatFingerprint(fingerprint: string) {
    // Format fingerprint for better readability
    return fingerprint.match(/.{1,2}/g)?.join(':') || fingerprint
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
            Device Security Fingerprints
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Each device has a unique cryptographic fingerprint. Verify these fingerprints match
            your trusted devices. Revoke access for any unknown devices immediately.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {devices.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No linked devices found</p>
            <p className="text-sm mt-1">Link a device to see it here</p>
          </div>
        ) : (
          devices.map((device) => {
            const DeviceIcon = getDeviceIcon(device.device_type)

            return (
              <div
                key={device.id}
                className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700
                         hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                      <DeviceIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-gray-900 dark:text-gray-100">
                          {device.name}
                        </h4>
                        {device.is_current && (
                          <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 dark:bg-green-900/30
                                       text-green-700 dark:text-green-400 rounded text-xs font-medium">
                            <CheckCircle className="w-3 h-3" />
                            This Device
                          </span>
                        )}
                      </div>

                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                            Device Fingerprint:
                          </p>
                          <code className="text-xs font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded
                                       text-gray-800 dark:text-gray-200 break-all block">
                            {device.fingerprint}
                          </code>
                        </div>

                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>Last seen: {formatDate(device.last_seen)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span>Added: {formatDate(device.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {!device.is_current && (
                    <button
                      onClick={() => revokeDevice(device.id, device.name)}
                      disabled={deletingId === device.id}
                      className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                               rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Revoke device access"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>

      <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <p className="text-sm text-amber-700 dark:text-amber-300">
          <strong>Security Tip:</strong> Regularly review your linked devices. If you see an
          unfamiliar device, revoke its access immediately and change your vault password.
        </p>
      </div>
    </div>
  )
}
