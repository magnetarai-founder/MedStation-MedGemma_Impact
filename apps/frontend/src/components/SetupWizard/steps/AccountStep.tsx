import { useState } from 'react'
import { User, Lock, AlertCircle, CheckCircle, Info } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

export default function AccountStep(props: StepProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [founderPassword, setFounderPassword] = useState('')
  const [enableFounder, setEnableFounder] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  // Validate form fields
  const validate = (): boolean => {
    const errors: Record<string, string> = {}

    // Username validation
    if (!username) {
      errors.username = 'Username is required'
    } else if (username.length < 3) {
      errors.username = 'Username must be at least 3 characters'
    } else if (username.length > 20) {
      errors.username = 'Username must be at most 20 characters'
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      errors.username = 'Username can only contain letters, numbers, and underscores'
    }

    // Password validation
    if (!password) {
      errors.password = 'Password is required'
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters'
    }

    // Confirm password validation
    if (!confirmPassword) {
      errors.confirmPassword = 'Please confirm your password'
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match'
    }

    // Founder password validation (if enabled)
    if (enableFounder && !founderPassword) {
      errors.founderPassword = 'Founder password is required when enabled'
    } else if (enableFounder && founderPassword.length < 12) {
      errors.founderPassword = 'Founder password must be at least 12 characters'
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate form
    if (!validate()) {
      return
    }

    setIsLoading(true)

    try {
      // Create account via API
      const result = await setupWizardApi.createAccount(
        username,
        password,
        confirmPassword,
        enableFounder ? founderPassword : undefined
      )

      if (result.success && result.user_id) {
        // Store user_id in wizard state
        props.updateWizardState({
          accountCreated: true,
          userId: result.user_id
        })

        // Move to next step
        if (props.onNext) {
          props.onNext()
        }
      } else {
        setError(result.error || 'Failed to create account')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <User className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Create Local Account
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          This account will have super_admin privileges on your local ElohimOS instance.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Banner */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                {error}
              </p>
            </div>
          </div>
        )}

        {/* Username Field */}
        <div>
          <label htmlFor="setup-username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Username
          </label>
          <input
            id="setup-username"
            type="text"
            name="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 ${
              validationErrors.username ? 'border-red-500' : ''
            }`}
            placeholder="johndoe"
            disabled={isLoading}
          />
          {validationErrors.username && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {validationErrors.username}
            </p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <label htmlFor="setup-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Password
          </label>
          <input
            id="setup-password"
            type="password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 ${
              validationErrors.password ? 'border-red-500' : ''
            }`}
            placeholder="••••••••"
            disabled={isLoading}
          />
          {validationErrors.password && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {validationErrors.password}
            </p>
          )}
        </div>

        {/* Confirm Password Field */}
        <div>
          <label htmlFor="setup-confirm-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Confirm Password
          </label>
          <input
            id="setup-confirm-password"
            type="password"
            name="confirm_password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 ${
              validationErrors.confirmPassword ? 'border-red-500' : ''
            }`}
            placeholder="••••••••"
            disabled={isLoading}
          />
          {validationErrors.confirmPassword && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {validationErrors.confirmPassword}
            </p>
          )}
        </div>

        {/* Founder Password (Optional) */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <div className="flex items-center gap-3 mb-4">
            <input
              id="enable-founder"
              type="checkbox"
              name="enable_founder"
              checked={enableFounder}
              onChange={(e) => setEnableFounder(e.target.checked)}
              className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              disabled={isLoading}
            />
            <label htmlFor="enable-founder" className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Lock className="w-4 h-4" />
              Enable Founder Password (Optional)
            </label>
          </div>

          {enableFounder && (
            <>
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-blue-800 dark:text-blue-200">
                    The founder password grants <strong>founder_rights</strong> - the highest privilege level that bypasses all permission checks. Keep this extremely secure.
                  </p>
                </div>
              </div>

              <input
                id="founder-password"
                type="password"
                name="founder_password"
                value={founderPassword}
                onChange={(e) => setFounderPassword(e.target.value)}
                autoComplete="new-password"
                className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-100 ${
                  validationErrors.founderPassword ? 'border-red-500' : ''
                }`}
                placeholder="Min 12 characters (highly secure)"
                disabled={isLoading}
              />
              {validationErrors.founderPassword && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {validationErrors.founderPassword}
                </p>
              )}
            </>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          {props.onBack && (
            <button
              type="button"
              onClick={props.onBack}
              disabled={isLoading}
              className="flex-1 px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>
          )}
          <button
            type="submit"
            disabled={isLoading}
            className="flex-1 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Creating Account...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                Create Account
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
