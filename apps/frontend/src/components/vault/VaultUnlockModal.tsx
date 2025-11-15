import { useState, useEffect } from 'react'
import { Loader2, X, Fingerprint, Lock, AlertCircle } from 'lucide-react'
import api from '@/lib/api'
import { isBiometricAvailable, authenticateBiometric } from '@/lib/webauthn'

interface VaultUnlockModalProps {
  vaultId: string
  onUnlock: (sessionId: string) => void
  onCancel: () => void
  biometricEnabled?: boolean
  credentialId?: string
}

export function VaultUnlockModal({
  vaultId,
  onUnlock,
  onCancel,
  biometricEnabled = false,
  credentialId,
}: VaultUnlockModalProps) {
  const [unlockMode, setUnlockMode] = useState<'biometric' | 'passphrase'>(
    biometricEnabled ? 'biometric' : 'passphrase'
  )
  const [passphrase, setPassphrase] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [biometricSupported, setBiometricSupported] = useState(false)

  // Check biometric availability on mount
  useEffect(() => {
    const checkBiometric = async () => {
      const available = await isBiometricAvailable()
      setBiometricSupported(available)

      // If biometric not available but was selected, fallback to passphrase
      if (!available && unlockMode === 'biometric') {
        setUnlockMode('passphrase')
        setError('Touch ID not available. Please use passphrase.')
      }
    }

    checkBiometric()
  }, [unlockMode])

  const handleBiometricUnlock = async () => {
    if (!credentialId) {
      setError('Biometric unlock not configured')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Trigger Touch ID prompt
      const assertion = await authenticateBiometric(vaultId, credentialId)

      // Send to backend
      const res = await api.post('/api/v1/vault/unlock/biometric', {
        vault_id: vaultId,
        webauthn_assertion: assertion.authenticatorData,
        signature: assertion.signature,
      })

      if (res.data.success) {
        onUnlock(res.data.session_id)
      } else {
        setError('Failed to unlock vault')
      }
    } catch (e: any) {
      console.error('Biometric unlock failed:', e)

      // Handle specific errors
      if (e?.name === 'NotAllowedError') {
        setError('Touch ID cancelled or failed. Please try again.')
      } else if (e?.response?.status === 429) {
        setError('Too many unlock attempts. Please wait 5 minutes.')
      } else {
        setError(e?.response?.data?.detail || e?.message || 'Touch ID unlock failed')
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePassphraseUnlock = async () => {
    if (!passphrase || passphrase.length < 8) {
      setError('Passphrase must be at least 8 characters')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const res = await api.post('/api/v1/vault/unlock/passphrase', null, {
        params: {
          vault_id: vaultId,
          passphrase,
        },
      })

      if (res.data.success) {
        onUnlock(res.data.session_id)
      } else {
        setError('Failed to unlock vault')
      }
    } catch (e: any) {
      console.error('Passphrase unlock failed:', e)

      if (e?.response?.status === 429) {
        setError('Too many unlock attempts. Please wait 5 minutes.')
      } else {
        setError(e?.response?.data?.detail || e?.message || 'Incorrect passphrase')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (unlockMode === 'biometric') {
      handleBiometricUnlock()
    } else {
      handlePassphraseUnlock()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-[450px] max-w-[95vw] rounded-xl shadow-2xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Lock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Unlock Vault</h3>
          </div>
          <button
            onClick={onCancel}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Mode Selector (if biometric is enabled) */}
          {biometricEnabled && biometricSupported && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <Fingerprint className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <div className="flex-1">
                <div className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  Touch ID Available
                </div>
                <div className="text-xs text-blue-700 dark:text-blue-300">
                  Use Touch ID for quick unlock or enter passphrase
                </div>
              </div>
            </div>
          )}

          {/* Localhost Warning */}
          {window.location.protocol === 'http:' && window.location.hostname === 'localhost' && (
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 p-2 rounded border">
              Note: Touch ID requires localhost or HTTPS. You're on localhost.
            </div>
          )}

          {/* Biometric Mode */}
          {unlockMode === 'biometric' && (
            <div className="space-y-4">
              <button
                type="button"
                onClick={handleBiometricUnlock}
                disabled={loading}
                className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Fingerprint className="w-5 h-5" />
                )}
                <span>{loading ? 'Authenticating...' : 'Unlock with Touch ID'}</span>
              </button>

              <button
                type="button"
                onClick={() => setUnlockMode('passphrase')}
                className="w-full text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 underline"
              >
                Use Passphrase Instead
              </button>
            </div>
          )}

          {/* Passphrase Mode */}
          {unlockMode === 'passphrase' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Passphrase
                </label>
                <input
                  type="password"
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  placeholder="Enter vault passphrase"
                  autoFocus
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 dark:focus:ring-amber-400 focus:border-transparent"
                />
              </div>

              <button
                type="submit"
                disabled={loading || !passphrase}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{loading ? 'Unlocking...' : 'Unlock Vault'}</span>
              </button>

              {biometricEnabled && biometricSupported && (
                <button
                  type="button"
                  onClick={() => setUnlockMode('biometric')}
                  className="w-full text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 underline"
                >
                  Use Touch ID Instead
                </button>
              )}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="text-sm font-medium text-red-900 dark:text-red-100">Unlock Failed</div>
                <div className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</div>
              </div>
            </div>
          )}

          {/* Security Note */}
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center pt-2">
            Your vault is end-to-end encrypted. Server cannot access contents.
          </div>
        </form>
      </div>
    </div>
  )
}
