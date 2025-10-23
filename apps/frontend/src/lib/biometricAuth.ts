/**
 * Biometric Authentication Utility
 *
 * Uses Web Authentication API (WebAuthn) for Touch ID / Face ID
 * on macOS and biometric authentication on other platforms.
 *
 * "Guard your heart above all else, for it determines the course of your life." - Proverbs 4:23
 */

import toast from 'react-hot-toast'

/**
 * Check if biometric authentication is available
 */
export async function isBiometricAvailable(): Promise<boolean> {
  // Check if PublicKeyCredential is available (WebAuthn support)
  if (!window.PublicKeyCredential) {
    return false
  }

  try {
    // Check if platform authenticator (Touch ID/Face ID) is available
    const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
    return available
  } catch (error) {
    console.warn('Failed to check biometric availability:', error)
    return false
  }
}

/**
 * Register biometric credential for a document
 * This creates a credential that can be used to unlock the document
 */
export async function registerBiometric(documentId: string, userId: string): Promise<boolean> {
  try {
    const available = await isBiometricAvailable()
    if (!available) {
      toast.error('Biometric authentication not available on this device')
      return false
    }

    // Create credential options
    const challenge = new Uint8Array(32)
    crypto.getRandomValues(challenge)

    const publicKeyOptions: PublicKeyCredentialCreationOptions = {
      challenge,
      rp: {
        name: 'ElohimOS',
        id: window.location.hostname,
      },
      user: {
        id: new TextEncoder().encode(userId),
        name: `elohimos-user-${userId.slice(0, 8)}`,
        displayName: 'ElohimOS User',
      },
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },  // ES256
        { type: 'public-key', alg: -257 } // RS256
      ],
      authenticatorSelection: {
        authenticatorAttachment: 'platform', // Touch ID/Face ID
        userVerification: 'required',
        requireResidentKey: false,
      },
      timeout: 60000,
      attestation: 'none',
    }

    // Create credential
    const credential = await navigator.credentials.create({
      publicKey: publicKeyOptions,
    }) as PublicKeyCredential

    if (!credential) {
      throw new Error('Failed to create credential')
    }

    // Store credential ID for this document
    const credentialId = Array.from(new Uint8Array(credential.rawId))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')

    localStorage.setItem(`elohimos.biometric.${documentId}`, credentialId)

    return true
  } catch (error: any) {
    console.error('Biometric registration failed:', error)

    if (error.name === 'NotAllowedError') {
      toast.error('Biometric authentication was cancelled')
    } else {
      toast.error('Failed to register biometric authentication')
    }

    return false
  }
}

/**
 * Authenticate using biometric (Touch ID / Face ID)
 * Returns true if authentication successful
 */
export async function authenticateBiometric(documentId: string): Promise<boolean> {
  try {
    const available = await isBiometricAvailable()
    if (!available) {
      toast.error('Biometric authentication not available')
      return false
    }

    // Get stored credential ID
    const credentialId = localStorage.getItem(`elohimos.biometric.${documentId}`)

    if (!credentialId) {
      // No credential registered, create one
      toast.error('No biometric credential found. Please set up Touch ID first.')
      return false
    }

    // Create authentication challenge
    const challenge = new Uint8Array(32)
    crypto.getRandomValues(challenge)

    // Convert hex string back to Uint8Array
    const credentialIdBytes = new Uint8Array(
      credentialId.match(/.{2}/g)!.map(byte => parseInt(byte, 16))
    )

    const publicKeyOptions: PublicKeyCredentialRequestOptions = {
      challenge,
      allowCredentials: [
        {
          type: 'public-key',
          id: credentialIdBytes,
          transports: ['internal'], // Platform authenticator
        },
      ],
      userVerification: 'required',
      timeout: 60000,
    }

    // Request authentication
    const assertion = await navigator.credentials.get({
      publicKey: publicKeyOptions,
    }) as PublicKeyCredential

    if (!assertion) {
      throw new Error('Authentication failed')
    }

    // Authentication successful
    return true
  } catch (error: any) {
    console.error('Biometric authentication failed:', error)

    if (error.name === 'NotAllowedError') {
      toast.error('Authentication was cancelled')
    } else if (error.name === 'InvalidStateError') {
      toast.error('Biometric credential not found. Please set up Touch ID again.')
      // Clean up invalid credential
      localStorage.removeItem(`elohimos.biometric.${documentId}`)
    } else {
      toast.error('Authentication failed')
    }

    return false
  }
}

/**
 * Remove biometric credential for a document
 */
export function removeBiometric(documentId: string): void {
  localStorage.removeItem(`elohimos.biometric.${documentId}`)
}

/**
 * Check if document has biometric credential registered
 */
export function hasBiometricCredential(documentId: string): boolean {
  return localStorage.getItem(`elohimos.biometric.${documentId}`) !== null
}

/**
 * Fallback PIN authentication (if biometric fails or unavailable)
 */
export async function authenticateWithPIN(documentId: string, pin: string): Promise<boolean> {
  // Simple hash-based PIN check
  const storedPinHash = localStorage.getItem(`elohimos.pin.${documentId}`)

  if (!storedPinHash) {
    return false
  }

  const pinHash = await hashPIN(pin)
  return pinHash === storedPinHash
}

/**
 * Set PIN for document (fallback auth method)
 */
export async function setPIN(documentId: string, pin: string): Promise<void> {
  const pinHash = await hashPIN(pin)
  localStorage.setItem(`elohimos.pin.${documentId}`, pinHash)
}

/**
 * Hash PIN using Web Crypto API
 */
async function hashPIN(pin: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(pin)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}
