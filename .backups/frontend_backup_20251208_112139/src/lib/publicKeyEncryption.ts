/**
 * Public Key Encryption Utilities for ElohimOS
 *
 * Implements Proton Drive-style file sharing with recipient-specific encryption.
 * Uses RSA-OAEP for asymmetric encryption and AES-GCM for file content.
 */

/**
 * Generate RSA key pair for a user
 */
export async function generateKeyPair(): Promise<CryptoKeyPair> {
  return await crypto.subtle.generateKey(
    {
      name: 'RSA-OAEP',
      modulusLength: 4096, // Strong security
      publicExponent: new Uint8Array([1, 0, 1]), // 65537
      hash: 'SHA-256',
    },
    true, // extractable
    ['encrypt', 'decrypt']
  )
}

/**
 * Export public key to base64 for sharing
 */
export async function exportPublicKey(publicKey: CryptoKey): Promise<string> {
  const exported = await crypto.subtle.exportKey('spki', publicKey)
  return arrayBufferToBase64(exported)
}

/**
 * Import public key from base64
 */
export async function importPublicKey(publicKeyBase64: string): Promise<CryptoKey> {
  const buffer = base64ToArrayBuffer(publicKeyBase64)
  return await crypto.subtle.importKey(
    'spki',
    buffer,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    true,
    ['encrypt']
  )
}

/**
 * Export private key to base64 (for secure storage)
 */
export async function exportPrivateKey(privateKey: CryptoKey): Promise<string> {
  const exported = await crypto.subtle.exportKey('pkcs8', privateKey)
  return arrayBufferToBase64(exported)
}

/**
 * Import private key from base64
 */
export async function importPrivateKey(privateKeyBase64: string): Promise<CryptoKey> {
  const buffer = base64ToArrayBuffer(privateKeyBase64)
  return await crypto.subtle.importKey(
    'pkcs8',
    buffer,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    true,
    ['decrypt']
  )
}

/**
 * Generate a random symmetric key for file encryption
 */
export async function generateFileKey(): Promise<CryptoKey> {
  return await crypto.subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true, // extractable
    ['encrypt', 'decrypt']
  )
}

/**
 * Encrypt file data with symmetric key
 */
export async function encryptFileData(
  data: ArrayBuffer,
  fileKey: CryptoKey
): Promise<{ encrypted: ArrayBuffer; iv: Uint8Array }> {
  const iv = crypto.getRandomValues(new Uint8Array(12))

  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv,
    },
    fileKey,
    data
  )

  return { encrypted, iv }
}

/**
 * Decrypt file data with symmetric key
 */
export async function decryptFileData(
  encryptedData: ArrayBuffer,
  fileKey: CryptoKey,
  iv: Uint8Array
): Promise<ArrayBuffer> {
  return await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: iv,
    },
    fileKey,
    encryptedData
  )
}

/**
 * Encrypt symmetric file key for a specific recipient
 */
export async function encryptKeyForRecipient(
  fileKey: CryptoKey,
  recipientPublicKey: CryptoKey
): Promise<string> {
  // Export the symmetric key as raw bytes
  const keyBytes = await crypto.subtle.exportKey('raw', fileKey)

  // Encrypt the key with recipient's public key
  const encryptedKey = await crypto.subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    recipientPublicKey,
    keyBytes
  )

  return arrayBufferToBase64(encryptedKey)
}

/**
 * Decrypt symmetric file key with private key
 */
export async function decryptKeyForRecipient(
  encryptedKeyBase64: string,
  recipientPrivateKey: CryptoKey
): Promise<CryptoKey> {
  const encryptedKey = base64ToArrayBuffer(encryptedKeyBase64)

  // Decrypt the key with recipient's private key
  const keyBytes = await crypto.subtle.decrypt(
    {
      name: 'RSA-OAEP',
    },
    recipientPrivateKey,
    encryptedKey
  )

  // Import the decrypted key as AES-GCM key
  return await crypto.subtle.importKey(
    'raw',
    keyBytes,
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt', 'decrypt']
  )
}

/**
 * Share a file with multiple recipients (Proton Drive style)
 */
export interface RecipientShare {
  recipientId: string
  recipientName: string
  recipientPublicKey: string
  encryptedFileKey: string // File key encrypted for this specific recipient
}

export interface EncryptedFileShare {
  fileId: string
  filename: string
  encryptedData: string
  iv: string
  recipients: RecipientShare[]
  uploadedBy: string
  uploadedAt: string
  fileSize: number
  mimeType: string
}

export async function createFileShare(
  file: File,
  recipients: Array<{ id: string; name: string; publicKey: string }>,
  uploadedBy: string
): Promise<EncryptedFileShare> {
  // 1. Generate a random symmetric key for the file
  const fileKey = await generateFileKey()

  // 2. Read and encrypt the file data
  const fileData = await file.arrayBuffer()
  const { encrypted, iv } = await encryptFileData(fileData, fileKey)

  // 3. Encrypt the file key for each recipient
  const recipientShares: RecipientShare[] = []

  for (const recipient of recipients) {
    const recipientPublicKey = await importPublicKey(recipient.publicKey)
    const encryptedFileKey = await encryptKeyForRecipient(fileKey, recipientPublicKey)

    recipientShares.push({
      recipientId: recipient.id,
      recipientName: recipient.name,
      recipientPublicKey: recipient.publicKey,
      encryptedFileKey,
    })
  }

  // 4. Return the encrypted file share
  return {
    fileId: generateFileId(),
    filename: file.name,
    encryptedData: arrayBufferToBase64(encrypted),
    iv: arrayBufferToBase64(iv),
    recipients: recipientShares,
    uploadedBy,
    uploadedAt: new Date().toISOString(),
    fileSize: file.size,
    mimeType: file.type || 'application/octet-stream',
  }
}

/**
 * Decrypt a shared file (recipient side)
 */
export async function decryptSharedFile(
  fileShare: EncryptedFileShare,
  recipientId: string,
  recipientPrivateKey: CryptoKey
): Promise<Blob> {
  // Find the recipient's encrypted key
  const recipientShare = fileShare.recipients.find((r) => r.recipientId === recipientId)

  if (!recipientShare) {
    throw new Error('You do not have access to this file')
  }

  // Decrypt the file key with recipient's private key
  const fileKey = await decryptKeyForRecipient(recipientShare.encryptedFileKey, recipientPrivateKey)

  // Decrypt the file data
  const encryptedData = base64ToArrayBuffer(fileShare.encryptedData)
  const iv = new Uint8Array(base64ToArrayBuffer(fileShare.iv))

  const decryptedData = await decryptFileData(encryptedData, fileKey, iv)

  // Return as Blob
  return new Blob([decryptedData], { type: fileShare.mimeType })
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
 * Generate unique file ID
 */
function generateFileId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`
}

/**
 * Store user key pair securely (encrypted with user's vault passphrase)
 */
export async function storeKeyPair(
  keyPair: CryptoKeyPair,
  vaultPassphrase: string
): Promise<{ publicKey: string; encryptedPrivateKey: string; salt: string; iv: string }> {
  // Export keys
  const publicKeyB64 = await exportPublicKey(keyPair.publicKey)
  const privateKeyB64 = await exportPrivateKey(keyPair.privateKey)

  // Encrypt private key with vault passphrase
  const { deriveKey } = await import('./encryption')
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const encryptionKey = await deriveKey(vaultPassphrase, salt)

  const encoder = new TextEncoder()
  const encryptedPrivateKey = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv,
    },
    encryptionKey,
    encoder.encode(privateKeyB64)
  )

  return {
    publicKey: publicKeyB64,
    encryptedPrivateKey: arrayBufferToBase64(encryptedPrivateKey),
    salt: arrayBufferToBase64(salt),
    iv: arrayBufferToBase64(iv),
  }
}

/**
 * Retrieve user private key (decrypt with vault passphrase)
 */
export async function retrievePrivateKey(
  encryptedPrivateKeyB64: string,
  salt: string,
  iv: string,
  vaultPassphrase: string
): Promise<CryptoKey> {
  const { deriveKey } = await import('./encryption')
  const saltBuffer = new Uint8Array(base64ToArrayBuffer(salt))
  const ivBuffer = new Uint8Array(base64ToArrayBuffer(iv))
  const encryptionKey = await deriveKey(vaultPassphrase, saltBuffer)

  const encryptedPrivateKey = base64ToArrayBuffer(encryptedPrivateKeyB64)

  const decryptedPrivateKeyBytes = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: ivBuffer,
    },
    encryptionKey,
    encryptedPrivateKey
  )

  const decoder = new TextDecoder()
  const privateKeyB64 = decoder.decode(decryptedPrivateKeyBytes)

  return await importPrivateKey(privateKeyB64)
}
