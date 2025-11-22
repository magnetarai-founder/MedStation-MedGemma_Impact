/**
 * WebAuthn Utility for Biometric Vault Unlock
 *
 * Provides Touch ID / Face ID authentication via Web Authentication API
 * Works on localhost (http://localhost:5173 or http://localhost:8000)
 *
 * Requirements:
 * - Modern browser with WebAuthn support
 * - Platform authenticator (Touch ID on macOS, Windows Hello, etc.)
 * - Secure context (localhost or HTTPS)
 */

export interface BiometricCredential {
  credentialId: string // base64
  publicKey: string // base64
  attestationObject?: string // base64
}

export interface BiometricAssertion {
  credentialId: string // base64
  authenticatorData: string // base64
  clientDataJSON: string // base64
  signature: string // base64
}

/**
 * Check if WebAuthn biometric authentication is available
 */
export async function isBiometricAvailable(): Promise<boolean> {
  try {
    // Check if PublicKeyCredential is supported
    if (!window.PublicKeyCredential) {
      return false
    }

    // Check if platform authenticator is available
    const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
    return available
  } catch (error) {
    console.error('Biometric availability check failed:', error)
    return false
  }
}

/**
 * Register a new biometric credential (Touch ID)
 *
 * @param vaultId - Vault UUID
 * @param userId - User UUID
 * @returns BiometricCredential with credentialId and publicKey
 */
export async function registerBiometric(
  vaultId: string,
  userId: string
): Promise<BiometricCredential> {
  try {
    // Check availability first
    const available = await isBiometricAvailable()
    if (!available) {
      throw new Error('Biometric authentication not available on this device')
    }

    // Generate challenge (random bytes)
    const challenge = new Uint8Array(32)
    crypto.getRandomValues(challenge)

    // Create credential options
    const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
      challenge,
      rp: {
        name: 'MagnetarStudio Vault',
        id: window.location.hostname, // 'localhost' for local dev
      },
      user: {
        id: new TextEncoder().encode(userId),
        name: userId,
        displayName: `Vault: ${vaultId.substring(0, 8)}...`,
      },
      pubKeyCredParams: [
        {
          type: 'public-key',
          alg: -7, // ES256 (ECDSA with SHA-256)
        },
        {
          type: 'public-key',
          alg: -257, // RS256 (RSA with SHA-256)
        },
      ],
      authenticatorSelection: {
        authenticatorAttachment: 'platform', // Require platform authenticator (Touch ID)
        userVerification: 'required', // Require biometric verification
        requireResidentKey: false,
      },
      timeout: 60000, // 60 seconds
      attestation: 'none', // Don't require attestation for privacy
    }

    // Create credential
    const credential = (await navigator.credentials.create({
      publicKey: publicKeyCredentialCreationOptions,
    })) as PublicKeyCredential | null

    if (!credential) {
      throw new Error('Failed to create biometric credential')
    }

    // Extract credential data
    const response = credential.response as AuthenticatorAttestationResponse
    const credentialId = arrayBufferToBase64(credential.rawId)
    const publicKey = arrayBufferToBase64(response.getPublicKey()!)
    const attestationObject = arrayBufferToBase64(response.attestationObject)

    return {
      credentialId,
      publicKey,
      attestationObject,
    }
  } catch (error) {
    console.error('Biometric registration failed:', error)
    throw error
  }
}

/**
 * Authenticate with biometric credential (Touch ID)
 *
 * @param vaultId - Vault UUID
 * @param credentialId - Credential ID from registration (base64)
 * @returns BiometricAssertion with signature and authenticator data
 */
export async function authenticateBiometric(
  vaultId: string,
  credentialId: string
): Promise<BiometricAssertion> {
  try {
    // Check availability first
    const available = await isBiometricAvailable()
    if (!available) {
      throw new Error('Biometric authentication not available on this device')
    }

    // Generate challenge
    const challenge = new Uint8Array(32)
    crypto.getRandomValues(challenge)

    // Create credential request options
    const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
      challenge,
      allowCredentials: [
        {
          type: 'public-key',
          id: base64ToArrayBuffer(credentialId),
        },
      ],
      userVerification: 'required', // Require biometric verification
      timeout: 60000, // 60 seconds
    }

    // Get credential (triggers Touch ID prompt)
    const credential = (await navigator.credentials.get({
      publicKey: publicKeyCredentialRequestOptions,
    })) as PublicKeyCredential | null

    if (!credential) {
      throw new Error('Failed to authenticate with biometric')
    }

    // Extract assertion data
    const response = credential.response as AuthenticatorAssertionResponse
    const authenticatorData = arrayBufferToBase64(response.authenticatorData)
    const clientDataJSON = arrayBufferToBase64(response.clientDataJSON)
    const signature = arrayBufferToBase64(response.signature)

    return {
      credentialId: arrayBufferToBase64(credential.rawId),
      authenticatorData,
      clientDataJSON,
      signature,
    }
  } catch (error) {
    console.error('Biometric authentication failed:', error)
    throw error
  }
}

/**
 * Helper: Convert ArrayBuffer to base64
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

/**
 * Helper: Convert base64 to ArrayBuffer
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}
