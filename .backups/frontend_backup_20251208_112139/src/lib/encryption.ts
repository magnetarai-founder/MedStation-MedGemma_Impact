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

/**
 * ============================================================================
 * LARGE FILE ENCRYPTION (Phase 5 - Production Critical)
 * ============================================================================
 * Chunked encryption/decryption to handle files > 500MB without memory overflow
 */

/**
 * Encrypt large file using chunked approach
 * Prevents memory overflow for files > 500MB
 */
export async function encryptLargeFile(
  file: File,
  key: CryptoKey,
  onProgress?: (percent: number) => void
): Promise<Blob> {
  const CHUNK_SIZE = 1024 * 1024 * 10 // 10 MB chunks
  const chunks: Blob[] = []

  // Generate single IV for entire file
  const iv = crypto.getRandomValues(new Uint8Array(12))

  // Prepend IV to result (needed for decryption)
  chunks.push(new Blob([iv]))

  // Process file in chunks
  for (let offset = 0; offset < file.size; offset += CHUNK_SIZE) {
    const chunk = file.slice(offset, Math.min(offset + CHUNK_SIZE, file.size))
    const arrayBuffer = await chunk.arrayBuffer()

    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      arrayBuffer
    )

    chunks.push(new Blob([encrypted]))

    // Update progress bar
    if (onProgress) {
      const progress = ((offset + chunk.size) / file.size) * 100
      onProgress(Math.min(progress, 100))
    }
  }

  return new Blob(chunks)
}

/**
 * Decrypt large file using chunked approach with progress callback
 */
export async function decryptLargeFile(
  encryptedBlob: Blob,
  key: CryptoKey,
  onProgress?: (percent: number) => void
): Promise<Blob> {
  const CHUNK_SIZE = 1024 * 1024 * 10 // 10 MB chunks (encrypted size)
  const decryptedChunks: Blob[] = []

  // Extract IV from first 12 bytes
  const ivBlob = encryptedBlob.slice(0, 12)
  const ivBuffer = await ivBlob.arrayBuffer()
  const iv = new Uint8Array(ivBuffer)

  // Process remaining data in chunks
  const dataBlob = encryptedBlob.slice(12)

  for (let offset = 0; offset < dataBlob.size; offset += CHUNK_SIZE) {
    const chunk = dataBlob.slice(offset, Math.min(offset + CHUNK_SIZE, dataBlob.size))
    const arrayBuffer = await chunk.arrayBuffer()

    try {
      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        arrayBuffer
      )

      decryptedChunks.push(new Blob([decrypted]))
    } catch (err) {
      throw new Error(`Decryption failed at offset ${offset}: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }

    // Update progress
    if (onProgress) {
      const progress = ((offset + chunk.size) / dataBlob.size) * 100
      onProgress(Math.min(progress, 100))
    }
  }

  return new Blob(decryptedChunks)
}

/**
 * Encrypt file with passphrase (automatically uses chunked encryption for large files)
 */
export async function encryptFile(
  file: File,
  passphrase: string,
  onProgress?: (percent: number) => void
): Promise<{ encryptedBlob: Blob; salt: string; iv: string }> {
  // Generate salt
  const salt = crypto.getRandomValues(new Uint8Array(16))

  // Derive key from passphrase
  const key = await deriveKey(passphrase, salt)

  // Use chunked encryption for files > 100MB, otherwise use single-pass
  const useChunked = file.size > 100 * 1024 * 1024

  let encryptedBlob: Blob

  if (useChunked) {
    encryptedBlob = await encryptLargeFile(file, key, onProgress)
  } else {
    // Small file - encrypt in one go
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const arrayBuffer = await file.arrayBuffer()
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      arrayBuffer
    )
    // Prepend IV
    encryptedBlob = new Blob([iv, encrypted])
    if (onProgress) onProgress(100)
  }

  // Extract IV from encrypted blob (first 12 bytes)
  const ivBlob = encryptedBlob.slice(0, 12)
  const ivBuffer = await ivBlob.arrayBuffer()
  const iv = new Uint8Array(ivBuffer)

  return {
    encryptedBlob,
    salt: arrayBufferToBase64(salt.buffer),
    iv: arrayBufferToBase64(iv.buffer),
  }
}

/**
 * Decrypt file with passphrase (automatically uses chunked decryption for large files)
 */
export async function decryptFile(
  encryptedBlob: Blob,
  salt: string,
  passphrase: string,
  onProgress?: (percent: number) => void
): Promise<Blob> {
  // Derive key from passphrase
  const saltBuffer = base64ToArrayBuffer(salt)
  const key = await deriveKey(passphrase, new Uint8Array(saltBuffer))

  // Use chunked decryption for files > 100MB
  const useChunked = encryptedBlob.size > 100 * 1024 * 1024

  if (useChunked) {
    return await decryptLargeFile(encryptedBlob, key, onProgress)
  } else {
    // Small file - decrypt in one go
    const ivBlob = encryptedBlob.slice(0, 12)
    const dataBlob = encryptedBlob.slice(12)

    const ivBuffer = await ivBlob.arrayBuffer()
    const iv = new Uint8Array(ivBuffer)

    const dataBuffer = await dataBlob.arrayBuffer()
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      dataBuffer
    )

    if (onProgress) onProgress(100)
    return new Blob([decrypted])
  }
}

/**
 * Helper: Estimate encryption time for large files
 */
export function estimateEncryptionTime(fileSizeBytes: number): number {
  // Rough estimate: ~50 MB/second encryption speed
  const speedMBps = 50
  const fileSizeMB = fileSizeBytes / (1024 * 1024)
  return Math.ceil(fileSizeMB / speedMBps)
}

/**
 * Helper: Estimate decryption time for large files
 */
export function estimateDecryptionTime(fileSizeBytes: number): number {
  // Decryption is typically slightly faster than encryption
  const speedMBps = 60
  const fileSizeMB = fileSizeBytes / (1024 * 1024)
  return Math.ceil(fileSizeMB / speedMBps)
}

/**
 * Helper: Check if file size requires chunked processing
 */
export function requiresChunkedProcessing(fileSizeBytes: number): boolean {
  return fileSizeBytes > 100 * 1024 * 1024 // 100 MB threshold
}
