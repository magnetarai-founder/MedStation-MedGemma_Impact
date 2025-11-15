import { useState } from 'react'
import { Loader2, Shield, AlertCircle, CheckCircle2, Eye, EyeOff } from 'lucide-react'
import api from '@/lib/api'

interface DecoyModeTabProps {
  vaultId: string
  userId: string
}

export function DecoyModeTab({ vaultId, userId }: DecoyModeTabProps) {
  const [enabled, setEnabled] = useState(false)
  const [passwordReal, setPasswordReal] = useState('')
  const [passwordDecoy, setPasswordDecoy] = useState('')
  const [showPasswordReal, setShowPasswordReal] = useState(false)
  const [showPasswordDecoy, setShowPasswordDecoy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Password strength indicator
  const getPasswordStrength = (password: string): 'weak' | 'medium' | 'strong' => {
    if (password.length < 8) return 'weak'
    if (password.length < 12) return 'medium'

    const hasUpper = /[A-Z]/.test(password)
    const hasLower = /[a-z]/.test(password)
    const hasNumber = /[0-9]/.test(password)
    const hasSpecial = /[^A-Za-z0-9]/.test(password)

    const score = [hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length

    if (score >= 3 && password.length >= 12) return 'strong'
    if (score >= 2) return 'medium'
    return 'weak'
  }

  const strengthReal = passwordReal ? getPasswordStrength(passwordReal) : null
  const strengthDecoy = passwordDecoy ? getPasswordStrength(passwordDecoy) : null

  const getStrengthColor = (strength: 'weak' | 'medium' | 'strong' | null) => {
    if (!strength) return 'bg-gray-200 dark:bg-gray-700'
    if (strength === 'weak') return 'bg-red-500'
    if (strength === 'medium') return 'bg-amber-500'
    return 'bg-green-500'
  }

  const getStrengthText = (strength: 'weak' | 'medium' | 'strong' | null) => {
    if (!strength) return ''
    if (strength === 'weak') return 'Weak'
    if (strength === 'medium') return 'Medium'
    return 'Strong'
  }

  const handleSetup = async () => {
    // Validation
    if (!passwordReal || passwordReal.length < 8) {
      setError('Real vault password must be at least 8 characters')
      return
    }

    if (!passwordDecoy || passwordDecoy.length < 8) {
      setError('Decoy vault password must be at least 8 characters')
      return
    }

    if (passwordReal === passwordDecoy) {
      setError('Real and decoy passwords must differ')
      return
    }

    if (strengthReal === 'weak' || strengthDecoy === 'weak') {
      setError('Passwords are too weak. Please use stronger passwords.')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const res = await api.post('/api/v1/vault/setup/decoy', {
        vault_id: vaultId,
        password_real: passwordReal,
        password_decoy: passwordDecoy,
      })

      if (res.data.success) {
        setSuccess(true)
        setEnabled(true)

        // Clear passwords after setup
        setTimeout(() => {
          setPasswordReal('')
          setPasswordDecoy('')
          setShowPasswordReal(false)
          setShowPasswordDecoy(false)
        }, 2000)
      } else {
        setError('Failed to setup decoy mode')
      }
    } catch (e: any) {
      console.error('Decoy setup failed:', e)
      setError(e?.response?.data?.detail || e?.message || 'Failed to setup decoy mode')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-3">
          <Shield className="w-7 h-7 text-amber-600 dark:text-amber-400" />
          Decoy Mode (Dual-Password)
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          Create a secondary vault with a decoy password for plausible deniability.
        </p>
      </div>

      {/* Description */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
          How Decoy Mode Works
        </h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>• You set two passwords: one for your real vault, one for a decoy vault</li>
          <li>• When unlocking, the system reveals whichever vault matches your password</li>
          <li>• No visible indicator of which mode is active (plausible deniability)</li>
          <li>• The decoy vault can contain innocuous files to avoid suspicion</li>
          <li>• Switching between modes requires logging out and unlocking again</li>
        </ul>
      </div>

      {/* Warning */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-100">
              Security Notice
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
              Both passwords must be strong and unique. If coerced to unlock your vault, use the decoy
              password to reveal only innocuous files. Never disclose that you have a decoy vault.
            </p>
          </div>
        </div>
      </div>

      {/* Enable Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <div>
          <div className="font-medium text-gray-900 dark:text-gray-100">Enable Decoy Vault</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Create a dual-password system for plausible deniability
          </div>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 dark:peer-focus:ring-amber-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-amber-600"></div>
        </label>
      </div>

      {/* Password Setup (if enabled) */}
      {enabled && (
        <div className="space-y-4">
          {/* Real Vault Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Real Vault Password
            </label>
            <div className="relative">
              <input
                type={showPasswordReal ? 'text' : 'password'}
                value={passwordReal}
                onChange={(e) => setPasswordReal(e.target.value)}
                placeholder="Enter password for real vault"
                className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 dark:focus:ring-amber-400 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPasswordReal(!showPasswordReal)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showPasswordReal ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {/* Strength Indicator */}
            {passwordReal && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${getStrengthColor(strengthReal)}`}
                      style={{
                        width:
                          strengthReal === 'weak' ? '33%' : strengthReal === 'medium' ? '66%' : '100%',
                      }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-400 w-16">
                    {getStrengthText(strengthReal)}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Decoy Vault Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Decoy Vault Password
            </label>
            <div className="relative">
              <input
                type={showPasswordDecoy ? 'text' : 'password'}
                value={passwordDecoy}
                onChange={(e) => setPasswordDecoy(e.target.value)}
                placeholder="Enter password for decoy vault"
                className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 dark:focus:ring-amber-400 focus:border-transparent"
              />
              <button
                type="button"
                onClick={() => setShowPasswordDecoy(!showPasswordDecoy)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showPasswordDecoy ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {/* Strength Indicator */}
            {passwordDecoy && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${getStrengthColor(strengthDecoy)}`}
                      style={{
                        width:
                          strengthDecoy === 'weak' ? '33%' : strengthDecoy === 'medium' ? '66%' : '100%',
                      }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-400 w-16">
                    {getStrengthText(strengthDecoy)}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Password Match Warning */}
          {passwordReal && passwordDecoy && passwordReal === passwordDecoy && (
            <div className="text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Passwords must differ
            </div>
          )}

          {/* Setup Button */}
          <button
            onClick={handleSetup}
            disabled={
              loading ||
              !passwordReal ||
              !passwordDecoy ||
              passwordReal === passwordDecoy ||
              strengthReal === 'weak' ||
              strengthDecoy === 'weak'
            }
            className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>{loading ? 'Setting up...' : 'Setup Decoy Mode'}</span>
          </button>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="flex items-start gap-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-sm font-medium text-green-900 dark:text-green-100">
              Decoy Mode Enabled
            </div>
            <div className="text-sm text-green-700 dark:text-green-300 mt-1">
              Your vault now has dual-password protection. Remember both passwords.
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-sm font-medium text-red-900 dark:text-red-100">Setup Failed</div>
            <div className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</div>
          </div>
        </div>
      )}

      {/* Additional Info */}
      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p>
          <strong>Remember:</strong> Both passwords unlock the vault, but show different contents.
        </p>
        <p>
          <strong>Security Tip:</strong> Populate your decoy vault with believable but non-sensitive
          files to maintain plausible deniability.
        </p>
        <p>
          <strong>Switching:</strong> To switch between real and decoy modes, lock the vault and unlock
          with the other password.
        </p>
      </div>
    </div>
  )
}
