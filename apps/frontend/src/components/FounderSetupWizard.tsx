/**
 * Founder Password Setup Wizard
 *
 * "Trust in the Lord with all your heart" - Proverbs 3:5
 *
 * First-time founder password initialization wizard.
 * Integrates with /api/v1/founder-setup endpoints.
 *
 * Features:
 * - One-time password setup
 * - Strong password validation
 * - Real-time validation feedback
 * - macOS Keychain integration indicator
 * - Setup completion confirmation
 *
 * Security:
 * - Client-side password validation
 * - Server-side validation
 * - Password confirmation required
 * - No password storage in browser
 */

import { useState, useEffect } from 'react'
import { Shield, Lock, CheckCircle, AlertCircle, Eye, EyeOff, Key, Info } from 'lucide-react'

interface SetupStatus {
  setup_completed: boolean
  setup_timestamp: string | null
  password_storage_type: string | null
  is_macos: boolean
}

interface PasswordRequirement {
  label: string
  test: (password: string) => boolean
  met: boolean
}

export default function FounderSetupWizard() {
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Form state
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Password requirements
  const [requirements, setRequirements] = useState<PasswordRequirement[]>([
    { label: 'At least 12 characters', test: (p) => p.length >= 12, met: false },
    { label: 'One uppercase letter', test: (p) => /[A-Z]/.test(p), met: false },
    { label: 'One lowercase letter', test: (p) => /[a-z]/.test(p), met: false },
    { label: 'One number', test: (p) => /\d/.test(p), met: false },
    { label: 'One special character (!@#$%^&*)', test: (p) => /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(p), met: false }
  ])

  useEffect(() => {
    fetchSetupStatus()
  }, [])

  useEffect(() => {
    // Update password requirements
    setRequirements(reqs => reqs.map(req => ({
      ...req,
      met: req.test(password)
    })))
  }, [password])

  const fetchSetupStatus = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/founder-setup/status')
      if (!response.ok) throw new Error('Failed to fetch setup status')
      const data = await response.json()
      setSetupStatus(data)
    } catch (err: any) {
      console.error('Failed to fetch setup status:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    // Client-side validation
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      setSubmitting(false)
      return
    }

    const allRequirementsMet = requirements.every(req => req.met)
    if (!allRequirementsMet) {
      setError('Password does not meet all requirements')
      setSubmitting(false)
      return
    }

    try {
      const response = await fetch('/api/v1/founder-setup/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          password,
          confirm_password: confirmPassword
        })
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Setup failed')
      }

      setSuccess(true)
      setPassword('')
      setConfirmPassword('')

      // Refresh status
      setTimeout(() => {
        fetchSetupStatus()
      }, 1000)

    } catch (err: any) {
      console.error('Setup failed:', err)
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  // Already setup
  if (setupStatus?.setup_completed) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="w-8 h-8 text-green-500" />
            <h3 className="text-xl font-bold text-white">Setup Complete</h3>
          </div>
          <p className="text-gray-300 mb-4">
            Founder password has been configured successfully.
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-gray-400" />
              <span className="text-gray-400">
                Storage: <span className="text-white capitalize">
                  {setupStatus.password_storage_type?.replace(/_/g, ' ')}
                </span>
              </span>
            </div>
            {setupStatus.setup_timestamp && (
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-gray-400" />
                <span className="text-gray-400">
                  Configured: <span className="text-white">
                    {new Date(setupStatus.setup_timestamp).toLocaleString()}
                  </span>
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Setup form
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-blue-500" />
            <h2 className="text-2xl font-bold text-white">Founder Password Setup</h2>
          </div>
          <p className="text-gray-400">
            Configure your founder password for administrative access. This is a one-time setup.
          </p>
        </div>

        {/* macOS Keychain info */}
        {setupStatus?.is_macos && (
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="text-blue-300 font-semibold mb-1">Secure Storage</p>
                <p className="text-gray-300">
                  Your password will be stored securely in macOS Keychain and never saved to disk.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Success message */}
        {success && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-green-500">
              <CheckCircle className="w-5 h-5" />
              <span className="font-semibold">Setup successful!</span>
            </div>
            <p className="text-sm text-gray-300 mt-1">
              Your founder password has been configured.
            </p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-red-500">
              <AlertCircle className="w-5 h-5" />
              <span className="font-semibold">Error</span>
            </div>
            <p className="text-sm text-gray-300 mt-1">{error}</p>
          </div>
        )}

        {/* Setup form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Password field */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Founder Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="Enter a strong password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Confirm password field */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="Confirm your password"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {password && confirmPassword && password !== confirmPassword && (
              <p className="text-sm text-red-500 mt-1">Passwords do not match</p>
            )}
          </div>

          {/* Password requirements */}
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-3">Password Requirements:</h4>
            <div className="space-y-2">
              {requirements.map((req, index) => (
                <div key={index} className="flex items-center gap-2">
                  {req.met ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-gray-600" />
                  )}
                  <span className={`text-sm ${req.met ? 'text-green-500' : 'text-gray-400'}`}>
                    {req.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={submitting || !requirements.every(r => r.met) || password !== confirmPassword}
            className="w-full px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Setting up...
              </>
            ) : (
              <>
                <Lock className="w-5 h-5" />
                Setup Founder Password
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
