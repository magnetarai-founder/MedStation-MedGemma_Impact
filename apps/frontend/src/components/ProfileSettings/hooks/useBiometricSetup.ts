/**
 * useBiometricSetup Hook
 *
 * Manages biometric authentication setup and state
 */

import { useState, useEffect } from 'react'
import { isBiometricAvailable, registerBiometric, hasBiometricCredential } from '@/lib/biometricAuth'
import toast from 'react-hot-toast'

export function useBiometricSetup(userId: string | undefined) {
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [biometricRegistered, setBiometricRegistered] = useState(false)
  const [checkingBiometric, setCheckingBiometric] = useState(true)

  // Check biometric availability on mount
  useEffect(() => {
    const checkBiometric = async () => {
      setCheckingBiometric(true)
      const available = await isBiometricAvailable()
      setBiometricAvailable(available)

      if (available && userId) {
        const registered = hasBiometricCredential(`vault-${userId}`)
        setBiometricRegistered(registered)
      }

      setCheckingBiometric(false)
    }

    if (userId) {
      checkBiometric()
    }
  }, [userId])

  const handleRegisterBiometric = async () => {
    if (!userId) {
      toast.error('User ID not found')
      return
    }

    const success = await registerBiometric(`vault-${userId}`, userId)
    if (success) {
      setBiometricRegistered(true)
      toast.success('Touch ID registered successfully')
    }
  }

  return {
    biometricState: {
      biometricAvailable,
      biometricRegistered,
      checkingBiometric,
    },
    handlers: {
      handleRegisterBiometric,
    },
  }
}
