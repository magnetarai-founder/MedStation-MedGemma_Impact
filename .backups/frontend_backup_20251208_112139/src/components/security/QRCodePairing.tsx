/**
 * QR Code Pairing Component
 *
 * Generates QR codes for secure device linking
 * Uses E2E encryption keys for device verification
 */

import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Smartphone, RefreshCw, Copy, Check, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

interface PairingData {
  device_id: string
  public_key: string
  fingerprint: string
  expires_at: string
}

export function QRCodePairing() {
  const [pairingData, setPairingData] = useState<PairingData | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  async function generatePairingCode() {
    setIsGenerating(true)
    toast.loading('Generating pairing code...', { id: 'pairing-code' })

    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/v1/e2e/generate-keypair', { method: 'POST' })
      // const data = await response.json()

      // Mock data for now
      const mockData: PairingData = {
        device_id: `device_${Math.random().toString(36).substring(7)}`,
        public_key: btoa(Array.from({ length: 32 }, () =>
          Math.floor(Math.random() * 256)
        ).join(',')),
        fingerprint: Array.from({ length: 16 }, () =>
          Math.floor(Math.random() * 256).toString(16).padStart(2, '0')
        ).join(':').toUpperCase(),
        expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 minutes
      }

      setPairingData(mockData)
      toast.success('Pairing code generated', { id: 'pairing-code' })

      // Auto-refresh after expiration
      setTimeout(() => {
        if (pairingData) {
          toast('Pairing code expired. Generate a new one.', { icon: '⏰' })
          setPairingData(null)
        }
      }, 5 * 60 * 1000)
    } catch (error) {
      console.error('Failed to generate pairing code:', error)
      toast.error('Failed to generate pairing code', { id: 'pairing-code' })
    } finally {
      setIsGenerating(false)
    }
  }

  async function copyPairingData() {
    if (!pairingData) return

    const dataString = JSON.stringify(pairingData, null, 2)

    try {
      await navigator.clipboard.writeText(dataString)
      setCopied(true)
      toast.success('Pairing data copied to clipboard')

      setTimeout(() => {
        setCopied(false)
      }, 2000)
    } catch (error) {
      toast.error('Failed to copy pairing data')
    }
  }

  function getTimeRemaining() {
    if (!pairingData) return null

    const now = new Date().getTime()
    const expiry = new Date(pairingData.expires_at).getTime()
    const diff = expiry - now

    if (diff <= 0) return 'Expired'

    const minutes = Math.floor(diff / 60000)
    const seconds = Math.floor((diff % 60000) / 1000)

    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <Smartphone className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
            Link New Device
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Generate a QR code to securely link another device. The code expires in 5 minutes.
            Your devices will sync with end-to-end encryption.
          </p>
        </div>
      </div>

      {!pairingData ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <Smartphone className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Link a New Device
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Scan the QR code with your other device to establish a secure, encrypted connection
          </p>
          <button
            onClick={generatePairingCode}
            disabled={isGenerating}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                     flex items-center gap-2 mx-auto"
          >
            <Smartphone className="w-5 h-5" />
            {isGenerating ? 'Generating...' : 'Generate Pairing Code'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border-2 border-blue-200 dark:border-blue-800">
            <div className="flex flex-col items-center">
              <div className="bg-white p-4 rounded-lg mb-4">
                <QRCodeSVG
                  value={JSON.stringify(pairingData)}
                  size={256}
                  level="H"
                  includeMargin={true}
                />
              </div>

              <div className="text-center space-y-2">
                <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                  Scan this code with your other device
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Expires in: <span className="font-mono font-semibold">{getTimeRemaining()}</span>
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Device ID
              </label>
              <code className="block w-full p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-mono
                             text-gray-800 dark:text-gray-200 break-all">
                {pairingData.device_id}
              </code>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Security Fingerprint
              </label>
              <code className="block w-full p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-mono
                             text-gray-800 dark:text-gray-200 break-all">
                {pairingData.fingerprint}
              </code>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={copyPairingData}
              className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
                       text-gray-700 dark:text-gray-300 rounded-lg flex items-center justify-center gap-2
                       transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy Pairing Data
                </>
              )}
            </button>

            <button
              onClick={generatePairingCode}
              disabled={isGenerating}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                       flex items-center justify-center gap-2 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className="w-4 h-4" />
              Generate New Code
            </button>
          </div>

          <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                <strong>Security Note:</strong> Only scan this QR code on devices you own and trust.
                This grants full access to your encrypted vault. Verify the fingerprint matches on both devices.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 text-sm">
          How Device Linking Works
        </h4>
        <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-decimal list-inside">
          <li>Generate a pairing code on this device</li>
          <li>Open MagnetarStudio on your other device</li>
          <li>Go to Settings → Security → Link Device</li>
          <li>Scan the QR code or enter the pairing data manually</li>
          <li>Verify the security fingerprint matches on both devices</li>
          <li>Approve the pairing to sync encrypted data</li>
        </ol>
      </div>
    </div>
  )
}
