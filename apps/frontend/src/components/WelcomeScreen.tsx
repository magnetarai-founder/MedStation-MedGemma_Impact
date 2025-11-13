/**
 * Welcome Screen
 *
 * Entry point for ElohimOS shown before authentication.
 * Routes to Login, Sign Up, or Founder Login flows.
 *
 * "Trust in the Lord with all your heart" - Proverbs 3:5
 */

import { useState } from 'react'
import { Shield, UserPlus, LogIn, Crown } from 'lucide-react'
import { Login } from './Login'

interface WelcomeScreenProps {
  onLoginSuccess: (token: string, userId: string) => void
}

export function WelcomeScreen({ onLoginSuccess }: WelcomeScreenProps) {
  const [view, setView] = useState<'welcome' | 'login' | 'signup' | 'founder'>('welcome')

  // Handle successful login from Login component
  const handleLogin = (token: string) => {
    // Extract user info from token or localStorage
    const userStr = localStorage.getItem('user')
    const user = userStr ? JSON.parse(userStr) : null
    const userId = user?.user_id || user?.id || ''

    onLoginSuccess(token, userId)
  }

  // Show Login component if user selected Login or Sign Up
  if (view === 'login' || view === 'signup') {
    return <Login onLogin={handleLogin} />
  }

  // Show Founder Login (simple form)
  if (view === 'founder') {
    return <FounderLogin onBack={() => setView('welcome')} onLoginSuccess={handleLogin} />
  }

  // Welcome Screen (default)
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-primary-600 rounded-2xl shadow-lg mb-4">
            <Shield className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            ElohimOS
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Equipping the global Church with AI
          </p>
        </div>

        {/* Welcome Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2 text-center">
            Welcome
          </h2>
          <p className="text-gray-600 dark:text-gray-400 text-center mb-8">
            Choose how you'd like to continue
          </p>

          {/* Action Buttons */}
          <div className="space-y-3">
            {/* Login Button */}
            <button
              onClick={() => setView('login')}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl"
            >
              <LogIn className="w-5 h-5" />
              <span className="font-medium">Log In</span>
            </button>

            {/* Sign Up Button */}
            <button
              onClick={() => setView('signup')}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border-2 border-gray-300 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              <UserPlus className="w-5 h-5" />
              <span className="font-medium">Create Account</span>
            </button>

            {/* Divider */}
            <div className="relative py-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                  or
                </span>
              </div>
            </div>

            {/* Founder Login */}
            <button
              onClick={() => setView('founder')}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-xl hover:from-purple-700 hover:to-purple-800 transition-colors"
            >
              <Crown className="w-5 h-5" />
              <span className="font-medium">Founder Login</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>"Trust in the Lord with all your heart" - Proverbs 3:5</p>
        </div>
      </div>
    </div>
  )
}

// Founder Login Component (hardcoded credentials)
interface FounderLoginProps {
  onBack: () => void
  onLoginSuccess: (token: string) => void
}

function FounderLogin({ onBack, onLoginSuccess }: FounderLoginProps) {
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Get or create device fingerprint
  function getDeviceFingerprint(): string {
    const key = 'elohimos.device_id'
    let fingerprint = localStorage.getItem(key)

    if (!fingerprint) {
      fingerprint = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0
        const v = c === 'x' ? r : (r & 0x3 | 0x8)
        return v.toString(16)
      })
      localStorage.setItem(key, fingerprint)
    }

    return fingerprint
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!password) {
      setError('Password is required')
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: 'founder',  // Hardcoded founder username
          password: password,
          device_fingerprint: getDeviceFingerprint()
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Founder login failed')
      }

      const data = await response.json()
      const { token, user } = data

      // Store token and user
      localStorage.setItem('auth_token', token)
      localStorage.setItem('user', JSON.stringify(user))

      // Complete login
      onLoginSuccess(token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Founder login failed')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-600 to-purple-700 rounded-2xl shadow-lg mb-4">
            <Crown className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Founder Login
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Access with founder credentials
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Username (hardcoded, shown as disabled) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value="founder"
                disabled
                className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Founder Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter founder password"
                className="w-full px-4 py-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                autoFocus
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onBack}
                disabled={isLoading}
                className="flex-1 px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Logging in...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    Login
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Founder credentials are hardcoded and always available</p>
        </div>
      </div>
    </div>
  )
}
