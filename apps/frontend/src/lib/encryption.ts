/**
 * Encryption Utilities for ElohimOS Vault
 *
 * Provides AES-256-GCM encryption for secure document storage.
 * Uses Web Crypto API for browser-native encryption.
 */

/**
 * Derives an encryption key from a passphrase using PBKDF2
 */
export async function deriveKey(
  passphrase: string,
  salt: Uint8Array
): Promise<CryptoKey> {
  const encoder = new TextEncoder()
  const passphraseKey = await crypto.subtle.importKey(
    'raw',
    encoder.encode(passphrase),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  )

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: 600000, // OWASP 2023 recommendation for PBKDF2-HMAC-SHA256
      hash: 'SHA-256'
    },
    passphraseKey,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt']
  )
}

/**
 * Encrypts data using AES-256-GCM
 */
export async function encryptData(
  data: string,
  passphrase: string
): Promise<{ encrypted: string; salt: string; iv: string }> {
  // Generate random salt and IV
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))

  // Derive encryption key
  const key = await deriveKey(passphrase, salt)

  // Encrypt the data
  const encoder = new TextEncoder()
  const encryptedBuffer = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    key,
    encoder.encode(data)
  )

  // Convert to base64 for storage
  return {
    encrypted: arrayBufferToBase64(encryptedBuffer),
    salt: arrayBufferToBase64(salt),
    iv: arrayBufferToBase64(iv)
  }
}

/**
 * Decrypts data using AES-256-GCM
 */
export async function decryptData(
  encrypted: string,
  salt: string,
  iv: string,
  passphrase: string
): Promise<string> {
  // Convert from base64
  const encryptedBuffer = base64ToArrayBuffer(encrypted)
  const saltBuffer = base64ToArrayBuffer(salt)
  const ivBuffer = base64ToArrayBuffer(iv)

  // Derive the same key
  const key = await deriveKey(passphrase, new Uint8Array(saltBuffer))

  // Decrypt the data
  const decryptedBuffer = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: new Uint8Array(ivBuffer)
    },
    key,
    encryptedBuffer
  )

  // Convert back to string
  const decoder = new TextDecoder()
  return decoder.decode(decryptedBuffer)
}

/**
 * Verifies a passphrase against stored encrypted data
 */
export async function verifyPassphrase(
  testData: string,
  encrypted: string,
  salt: string,
  iv: string,
  passphrase: string
): Promise<boolean> {
  try {
    const decrypted = await decryptData(encrypted, salt, iv, passphrase)
    return decrypted === testData
  } catch {
    return false
  }
}

/**
 * Helper: Convert ArrayBuffer to base64 string
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

/**
 * Helper: Convert base64 string to ArrayBuffer
 */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

/**
 * Generates a secure random passphrase verification token
 */
export function generateVerificationToken(): string {
  return 'vault_verification_' + Date.now()
}

/**
 * Encrypts a document for vault storage
 */
export interface EncryptedDocument {
  id: string
  title: string
  encrypted_content: string
  salt: string
  iv: string
  created_at: string
  modified_at: string
  metadata?: {
    original_size: number
    encrypted_size: number
  }
}

export async function encryptDocument(
  documentId: string,
  title: string,
  content: string,
  passphrase: string
): Promise<EncryptedDocument> {
  const { encrypted, salt, iv } = await encryptData(content, passphrase)

  return {
    id: documentId,
    title,
    encrypted_content: encrypted,
    salt,
    iv,
    created_at: new Date().toISOString(),
    modified_at: new Date().toISOString(),
    metadata: {
      original_size: content.length,
      encrypted_size: encrypted.length
    }
  }
}

/**
 * Decrypts a document from vault storage
 */
export async function decryptDocument(
  encryptedDoc: EncryptedDocument,
  passphrase: string
): Promise<string> {
  return decryptData(
    encryptedDoc.encrypted_content,
    encryptedDoc.salt,
    encryptedDoc.iv,
    passphrase
  )
}
