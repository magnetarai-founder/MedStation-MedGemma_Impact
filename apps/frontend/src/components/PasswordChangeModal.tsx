import { useState, useEffect } from 'react'
import { Lock, AlertCircle, CheckCircle, Loader2, X } from 'lucide-react'

interface PasswordChangeModalProps {
  isOpen: boolean
  username: string
  onClose: () => void
  onSuccess: (newPassword: string) => void
}

export function PasswordChangeModal({ isOpen, username, onClose, onSuccess }: PasswordChangeModalProps) {
  const [tempPassword, setTempPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  // Password complexity validation
  const validatePassword = (pwd: string): { valid: boolean; errors: string[] } => {
    const errors: string[] = []

    if (pwd.length < 12) {
      errors.push('At least 12 characters')
    }
    if (!/[A-Z]/.test(pwd)) {
      errors.push('One uppercase letter')
    }
    if (!/[a-z]/.test(pwd)) {
      errors.push('One lowercase letter')
    }
    if (!/[0-9]/.test(pwd)) {
      errors.push('One digit')
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) {
      errors.push('One special character')
    }

    return { valid: errors.length === 0, errors }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate all fields filled
    if (!tempPassword || !newPassword || !confirmPassword) {
      setError('All fields are required')
      return
    }

    // Validate password match
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password complexity
    const validation = validatePassword(newPassword)
    if (!validation.valid) {
      setError(`Password must have: ${validation.errors.join(', ')}`)
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/auth/change-password-first-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          temp_password: tempPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      })

      if (!response.ok) {
        const data = await response.json()
        const errorMessage = data.detail?.message || data.detail || data.message || 'Password change failed'
        throw new Error(errorMessage)
      }

      // Success - notify parent to retry login with new password
      onSuccess(newPassword)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password change failed')
      setIsLoading(false)
    }
  }

  const passwordRequirements = validatePassword(newPassword)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full border border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Password Change Required
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                For user: {username}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Info Message */}
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              Your password was reset by an administrator. Please enter the temporary password and choose a new secure password.
            </p>
          </div>

          {/* Temporary Password */}
          <div>
            <label htmlFor="temp-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Temporary Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="temp-password"
                type="password"
                name="temp_password"
                value={tempPassword}
                onChange={(e) => setTempPassword(e.target.value)}
                placeholder="Enter temporary password"
                autoComplete="current-password"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={isLoading}
                autoFocus
              />
            </div>
          </div>

          {/* New Password */}
          <div>
            <label htmlFor="new-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              New Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="new-password"
                type="password"
                name="new_password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                autoComplete="new-password"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Confirm Password */}
          <div>
            <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="confirm-password"
                type="password"
                name="confirm_password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                autoComplete="new-password"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Password Requirements */}
          {newPassword && (
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Password Requirements:</p>
              <div className="space-y-1">
                {[
                  { label: 'At least 12 characters', valid: newPassword.length >= 12 },
                  { label: 'One uppercase letter', valid: /[A-Z]/.test(newPassword) },
                  { label: 'One lowercase letter', valid: /[a-z]/.test(newPassword) },
                  { label: 'One digit', valid: /[0-9]/.test(newPassword) },
                  { label: 'One special character', valid: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword) }
                ].map((req, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {req.valid ? (
                      <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-gray-400" />
                    )}
                    <span className={`text-xs ${req.valid ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}`}>
                      {req.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !passwordRequirements.valid}
            className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Changing Password...
              </>
            ) : (
              <>
                <Lock className="w-5 h-5" />
                Change Password
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
