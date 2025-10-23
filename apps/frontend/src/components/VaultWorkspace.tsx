/**
 * Vault Workspace
 *
 * Secure file browser (Proton Drive style) with Touch ID + Password authentication
 */

import { useState, useEffect } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { Lock, Fingerprint, AlertTriangle, FileText, Table2, Lightbulb, Eye, EyeOff } from 'lucide-react'
import { authenticateBiometric, isBiometricAvailable } from '@/lib/biometricAuth'
import toast from 'react-hot-toast'

export function VaultWorkspace() {
  const { vaultUnlocked, unlockVault, lockVault, currentVaultMode, securitySettings } = useDocsStore()
  const requireTouchID = securitySettings.require_touch_id
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [authError, setAuthError] = useState('')

  useEffect(() => {
    checkBiometric()
  }, [])

  const checkBiometric = async () => {
    const available = await isBiometricAvailable()
    setBiometricAvailable(available)
  }

  const handleUnlock = async () => {
    setAuthError('')
    setIsAuthenticating(true)

    try {
      // Step 1: Touch ID authentication (only if required)
      if (requireTouchID) {
        if (biometricAvailable) {
          const biometricSuccess = await authenticateBiometric()
          if (!biometricSuccess) {
            setAuthError('Touch ID authentication failed')
            setIsAuthenticating(false)
            return
          }
        } else {
          setAuthError('Touch ID is required but not available on this device')
          setIsAuthenticating(false)
          return
        }
      }

      // Step 2: Password authentication
      if (!password) {
        setAuthError('Please enter your vault password')
        setIsAuthenticating(false)
        return
      }

      const success = await unlockVault(password)
      if (!success) {
        setAuthError('Incorrect password')
        setPassword('')
        setIsAuthenticating(false)
        return
      }

      // Success!
      setPassword('')
      toast.success(currentVaultMode === 'decoy' ? 'Vault unlocked' : 'Vault unlocked')
      setIsAuthenticating(false)
    } catch (error) {
      console.error('Vault unlock error:', error)
      setAuthError('Authentication failed')
      setIsAuthenticating(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleUnlock()
    }
  }

  // Locked State - Show Authentication
  if (!vaultUnlocked) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50 dark:from-gray-900 dark:to-gray-800">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="w-20 h-20 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                <Lock className="w-10 h-10 text-amber-600 dark:text-amber-400" />
                {biometricAvailable && requireTouchID && (
                  <Fingerprint className="absolute -top-2 -right-2 w-8 h-8 text-blue-600 dark:text-blue-400" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Secure Vault
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                {requireTouchID
                  ? 'Touch ID and password required'
                  : 'Password required'
                }
              </p>
            </div>

            {/* Error Message */}
            {authError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">{authError}</p>
              </div>
            )}

            {/* Password Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Vault Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your password"
                  disabled={isAuthenticating}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Unlock Button */}
            <button
              onClick={handleUnlock}
              disabled={isAuthenticating || !password}
              className="w-full py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {biometricAvailable && <Fingerprint className="w-5 h-5" />}
              {isAuthenticating ? 'Authenticating...' : 'Unlock Vault'}
            </button>

            {/* Info */}
            <p className="mt-4 text-xs text-center text-gray-500 dark:text-gray-400">
              Both Touch ID and password verification required
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Unlocked State - Show Vault Contents
  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Vault Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/10 dark:to-orange-900/10">
        <div className="flex items-center gap-3">
          <Lock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Secure Vault
            </h2>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {currentVaultMode === 'decoy' ? 'Standard Mode' : 'Protected Mode'}
            </p>
          </div>
        </div>
        <button
          onClick={lockVault}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <Lock className="w-4 h-4" />
          Lock Vault
        </button>
      </div>

      {/* Vault Content - Proton Drive Style */}
      <div className="flex-1 p-6">
        <div className="max-w-6xl mx-auto">
          {/* Empty State */}
          <div className="text-center py-12">
            <div className="w-24 h-24 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Lock className="w-12 h-12 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Your Vault is Empty
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Save documents to your vault for encrypted storage
            </p>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto mt-8">
              <button className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group">
                <FileText className="w-8 h-8 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Secure Document
                </p>
              </button>
              <button className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-green-500 dark:hover:border-green-400 hover:bg-green-50 dark:hover:bg-green-900/10 transition-all group">
                <Table2 className="w-8 h-8 text-gray-400 group-hover:text-green-600 dark:group-hover:text-green-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Secure Spreadsheet
                </p>
              </button>
              <button className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-amber-500 dark:hover:border-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/10 transition-all group">
                <Lightbulb className="w-8 h-8 text-gray-400 group-hover:text-amber-600 dark:group-hover:text-amber-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Secure Insight
                </p>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
