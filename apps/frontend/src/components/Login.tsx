import { useState, useEffect } from 'react'
import { Shield, User, Lock, Fingerprint, Loader2, UserPlus } from 'lucide-react'
import { authenticateBiometric } from '@/lib/biometricAuth'
import { SetupWizard } from './SetupWizard'

interface LoginProps {
  onLogin: (token: string) => void
}

// Get or create stable device fingerprint
function getDeviceFingerprint(): string {
  const key = 'elohimos.device_id'
  let fingerprint = localStorage.getItem(key)

  if (!fingerprint) {
    // Generate UUID v4
    fingerprint = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
    localStorage.setItem(key, fingerprint)
  }

  return fingerprint
}

export function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSetupWizard, setShowSetupWizard] = useState(false)
  const [deviceFingerprint, setDeviceFingerprint] = useState('')

  useEffect(() => {
    setDeviceFingerprint(getDeviceFingerprint())
  }, [])

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!username || !password) {
      setError('Username and password are required')
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password,
          device_fingerprint: deviceFingerprint
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      const data = await response.json()
      const { token, user } = data

      // Store token
      localStorage.setItem('auth_token', token)
      localStorage.setItem('user', JSON.stringify(user))

      // Complete login
      onLogin(token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setIsLoading(false)
    }
  }

  const handleTouchIDTest = async () => {
    // Test Touch ID availability (not for server login)
    setError(null)

    try {
      const success = await authenticateBiometric()
      if (success) {
        setError('Touch ID test successful! (Note: Touch ID is for UI unlock only)')
      } else {
        setError('Touch ID test failed or cancelled')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Touch ID test failed')
    }
  }

  // Show setup wizard if user clicks "Create Account"
  if (showSetupWizard) {
    return (
      <SetupWizard
        onComplete={(token) => onLogin(token)}
        onBack={() => setShowSetupWizard(false)}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Shield className="w-12 h-12 text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Welcome Back
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Sign in to access your ElohimOS workspace
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
          <form onSubmit={handlePasswordLogin} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isLoading}
                  autoFocus
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5" />
                  Sign In
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                New to this device?
              </span>
            </div>
          </div>

          {/* Create Account Button */}
          <button
            onClick={() => setShowSetupWizard(true)}
            disabled={isLoading}
            className="w-full py-3 px-4 bg-white dark:bg-gray-900 border-2 border-primary-600 dark:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 text-primary-600 dark:text-primary-400 font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <UserPlus className="w-5 h-5" />
            Create New Account
          </button>

          {/* Divider */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
            </div>
          </div>

          {/* Touch ID Test Button (UI unlock test only) */}
          <button
            type="button"
            onClick={handleTouchIDTest}
            disabled={isLoading}
            className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Fingerprint className="w-4 h-4" />
            Test Touch ID (UI Unlock Only)
          </button>

          {/* Info */}
          <div className="mt-6 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-800 dark:text-blue-200">
              Your credentials are stored locally and never leave this device. Multiple users can share this device securely.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
