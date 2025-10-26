/**
 * Secure Enclave API Client
 *
 * Communicates with the backend Secure Enclave service to store and retrieve
 * encryption keys in macOS Keychain (hardware-backed when Secure Enclave is available).
 *
 * Keys are stored in the Secure Enclave and only decrypted in memory - never written to disk.
 *
 * "The name of the Lord is a fortified tower; the righteous run to it and are safe." - Proverbs 18:10
 */

const API_BASE = '/api/v1/secure-enclave'

export interface KeyResponse {
  success: boolean
  key_exists: boolean
  message: string
  key_data?: string  // Base64 encoded key (only returned on retrieve)
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  keychain_accessible: boolean
  secure_enclave_available: boolean
  message: string
}

/**
 * Generate a new encryption key and store it in the Secure Enclave
 *
 * The key is hardware-backed when Secure Enclave is available on macOS.
 */
export async function generateAndStoreKey(
  keyId: string,
  passphrase: string
): Promise<KeyResponse> {
  const response = await fetch(`${API_BASE}/generate-key`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      key_id: keyId,
      passphrase,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate key')
  }

  return response.json()
}

/**
 * Retrieve encryption key from the Secure Enclave
 *
 * The key is decrypted in-memory only and returned as base64.
 * Use this to decrypt vault documents without ever writing the key to disk.
 */
export async function retrieveKey(
  keyId: string,
  passphrase: string
): Promise<KeyResponse> {
  const response = await fetch(`${API_BASE}/retrieve-key`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      key_id: keyId,
      passphrase,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to retrieve key')
  }

  return response.json()
}

/**
 * Delete encryption key from the Secure Enclave
 *
 * WARNING: This permanently deletes the key. Any data encrypted with this key
 * will be permanently unrecoverable.
 */
export async function deleteKey(keyId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/delete-key/${keyId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete key')
  }
}

/**
 * Check if a key exists in the Secure Enclave
 */
export async function checkKeyExists(keyId: string): Promise<boolean> {
  const response = await fetch(`${API_BASE}/check-key/${keyId}`)

  if (!response.ok) {
    throw new Error('Failed to check key existence')
  }

  const data = await response.json()
  return data.exists
}

/**
 * Check health status of Secure Enclave service
 */
export async function checkHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health`)

  if (!response.ok) {
    throw new Error('Failed to check Secure Enclave health')
  }

  return response.json()
}

/**
 * Convert base64 key to CryptoKey for use with Web Crypto API
 */
export async function importKeyFromBase64(keyBase64: string): Promise<CryptoKey> {
  // Decode from base64
  const keyData = Uint8Array.from(atob(keyBase64), c => c.charCodeAt(0))

  // Import as CryptoKey
  return crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'AES-GCM', length: 256 },
    false,  // Not extractable - stays in memory only
    ['encrypt', 'decrypt']
  )
}

/**
 * High-level function: Get encryption key for vault
 *
 * 1. Checks if Secure Enclave is available
 * 2. If key doesn't exist, generates one
 * 3. Retrieves the key (decrypted in-memory)
 * 4. Returns as CryptoKey ready for encryption/decryption
 */
export async function getVaultEncryptionKey(
  vaultId: string,
  passphrase: string
): Promise<CryptoKey> {
  const keyId = `vault_${vaultId}`

  // Check if key exists
  const exists = await checkKeyExists(keyId)

  if (!exists) {
    // Generate new key
    await generateAndStoreKey(keyId, passphrase)
  }

  // Retrieve key
  const response = await retrieveKey(keyId, passphrase)

  if (!response.success || !response.key_data) {
    throw new Error('Failed to retrieve vault encryption key')
  }

  // Convert to CryptoKey
  return importKeyFromBase64(response.key_data)
}

/**
 * Delete vault encryption key
 *
 * WARNING: This makes the vault permanently unrecoverable!
 */
export async function deleteVaultKey(vaultId: string): Promise<void> {
  const keyId = `vault_${vaultId}`
  await deleteKey(keyId)
}
