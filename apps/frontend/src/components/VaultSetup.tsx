/**
 * Vault Setup Modal
 *
 * FileVault-style setup for secure vault with real and decoy passwords
 */

import { useState } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { Lock, Shield, AlertTriangle, Eye, EyeOff, Check } from 'lucide-react'

interface VaultSetupProps {
  onComplete: () => void
  onCancel: () => void
}

export function VaultSetup({ onComplete, onCancel }: VaultSetupProps) {
  const { setVaultPasswords, securitySettings } = useDocsStore()
  const requireTouchID = securitySettings.require_touch_id

  const [step, setStep] = useState<'intro' | 'passwords' | 'confirm'>('intro')
  const [realPassword, setRealPassword] = useState('')
  const [realPassword2, setRealPassword2] = useState('')
  const [decoyPassword, setDecoyPassword] = useState('')
  const [confirmReal, setConfirmReal] = useState('')
  const [confirmReal2, setConfirmReal2] = useState('')
  const [confirmDecoy, setConfirmDecoy] = useState('')
  const [showPasswords, setShowPasswords] = useState(false)
  const [error, setError] = useState('')

  const validatePasswords = (): boolean => {
    setError('')

    if (realPassword.length < 8) {
      setError('Real password must be at least 8 characters')
      return false
    }

    if (realPassword !== confirmReal) {
      setError('Real password confirmation does not match')
      return false
    }

    // Validate second real password if Touch ID not required
    if (!requireTouchID) {
      if (realPassword2.length < 8) {
        setError('Second real password must be at least 8 characters')
        return false
      }

      if (realPassword2 !== confirmReal2) {
        setError('Second real password confirmation does not match')
        return false
      }

      if (realPassword === realPassword2) {
        setError('Real passwords must be different from each other')
        return false
      }

      if (realPassword2 === decoyPassword) {
        setError('Second real password cannot match decoy password')
        return false
      }
    }

    if (decoyPassword.length < 8) {
      setError('Decoy password must be at least 8 characters')
      return false
    }

    if (realPassword === decoyPassword) {
      setError('Real and decoy passwords must be different')
      return false
    }

    if (decoyPassword !== confirmDecoy) {
      setError('Decoy password confirmation does not match')
      return false
    }

    return true
  }

  const handleSetup = async () => {
    if (!validatePasswords()) return

    await setVaultPasswords(realPassword, decoyPassword, requireTouchID ? undefined : realPassword2)
    onComplete()
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full">
        {/* Intro Step */}
        {step === 'intro' && (
          <div className="p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="w-8 h-8 text-amber-600 dark:text-amber-400" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Set Up Secure Vault
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Protect your sensitive documents with encryption and plausible deniability
              </p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                    Real Password{!requireTouchID && 's (2)'}
                  </h3>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    {requireTouchID
                      ? 'Opens your actual secure vault with your real sensitive documents'
                      : 'You can set 2 different real passwords - either one opens your actual vault (for convenience)'
                    }
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
                    Decoy Password
                  </h3>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    Opens a fake vault with decoy documents for plausible deniability
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-700 dark:text-red-300">
                  <strong className="block mb-1">Important:</strong>
                  {requireTouchID
                    ? 'Both Touch ID AND password are required to access the vault. '
                    : 'Either of your 2 real passwords can unlock the vault. '
                  }
                  There is no password recovery. Write down your passwords in a secure location.
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={onCancel}
                className="flex-1 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep('passwords')}
                className="flex-1 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
              >
                Continue Setup
              </button>
            </div>
          </div>
        )}

        {/* Password Step */}
        {step === 'passwords' && (
          <div className="p-8">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Set Vault Passwords
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Choose strong, unique passwords (minimum 8 characters)
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            )}

            <div className="space-y-6 mb-6">
              {/* Real Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Real Vault Password {requireTouchID ? '' : '#1'}
                </label>
                <div className="relative">
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={realPassword}
                    onChange={(e) => setRealPassword(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter real password"
                  />
                </div>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={confirmReal}
                  onChange={(e) => setConfirmReal(e.target.value)}
                  className="w-full mt-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Confirm real password"
                />
              </div>

              {/* Second Real Password (only if Touch ID not required) */}
              {!requireTouchID && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Real Vault Password #2
                  </label>
                  <div className="relative">
                    <input
                      type={showPasswords ? 'text' : 'password'}
                      value={realPassword2}
                      onChange={(e) => setRealPassword2(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter second real password"
                    />
                  </div>
                  <input
                    type={showPasswords ? 'text' : 'password'}
                    value={confirmReal2}
                    onChange={(e) => setConfirmReal2(e.target.value)}
                    className="w-full mt-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Confirm second real password"
                  />
                </div>
              )}

              {/* Decoy Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Decoy Vault Password
                </label>
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={decoyPassword}
                  onChange={(e) => setDecoyPassword(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  placeholder="Enter decoy password"
                />
                <input
                  type={showPasswords ? 'text' : 'password'}
                  value={confirmDecoy}
                  onChange={(e) => setConfirmDecoy(e.target.value)}
                  className="w-full mt-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                  placeholder="Confirm decoy password"
                />
              </div>

              {/* Show Passwords Toggle */}
              <button
                onClick={() => setShowPasswords(!showPasswords)}
                className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showPasswords ? 'Hide' : 'Show'} passwords
              </button>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep('intro')}
                className="flex-1 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep('confirm')}
                className="flex-1 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Confirm Step */}
        {step === 'confirm' && (
          <div className="p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Confirm Setup
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Your vault will be created with the passwords you chose
              </p>
            </div>

            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-amber-700 dark:text-amber-300">
                  <strong className="block mb-1">Final Warning:</strong>
                  <ul className="list-disc ml-4 space-y-1">
                    <li>There is NO password recovery</li>
                    {requireTouchID ? (
                      <li>Both Touch ID AND password are required</li>
                    ) : (
                      <li>You set {realPassword2 ? '2' : '1'} real password{realPassword2 ? 's' : ''} - either can unlock the vault</li>
                    )}
                    <li>Write down your passwords securely</li>
                    <li>The decoy password opens a fake vault</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep('passwords')}
                className="flex-1 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleSetup}
                className="flex-1 py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
              >
                Create Vault
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
