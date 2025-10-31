/**
 * Backup Codes Component
 *
 * Generates and manages one-time backup codes for vault access recovery
 * Critical security feature: allows vault access if biometric/password fails
 */

import { useState } from 'react'
import { Download, Key, AlertTriangle, Check, Copy } from 'lucide-react'
import toast from 'react-hot-toast'

interface BackupCodesProps {
  onGenerate?: (codes: string[]) => void
}

export function BackupCodes({ onGenerate }: BackupCodesProps) {
  const [codes, setCodes] = useState<string[]>([])
  const [revealed, setRevealed] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  async function generateCodes() {
    setIsGenerating(true)
    toast.loading('Generating backup codes...', { id: 'backup-codes' })

    try {
      // Generate 10 random backup codes (8 characters each)
      const newCodes = Array.from({ length: 10 }, () => {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' // Excluding similar chars
        return Array.from({ length: 8 }, () =>
          chars[Math.floor(Math.random() * chars.length)]
        ).join('')
      })

      // Format codes with dashes for readability: XXXX-XXXX
      const formattedCodes = newCodes.map(code =>
        `${code.slice(0, 4)}-${code.slice(4)}`
      )

      setCodes(formattedCodes)
      setRevealed(true)

      if (onGenerate) {
        onGenerate(formattedCodes)
      }

      toast.success('Backup codes generated!', { id: 'backup-codes' })
    } catch (error) {
      console.error('Failed to generate backup codes:', error)
      toast.error('Failed to generate backup codes', { id: 'backup-codes' })
    } finally {
      setIsGenerating(false)
    }
  }

  async function downloadCodes() {
    const text = [
      'ElohimOS Vault Backup Codes',
      '============================',
      '',
      'Save these codes securely. Each code can be used once to access your vault.',
      'Generated: ' + new Date().toLocaleDateString(),
      '',
      '⚠️  WARNING: Do not share these codes. Store them safely offline.',
      '',
      ...codes.map((code, i) => `${i + 1}.  ${code}`),
      '',
      '============================',
      'ElohimOS - Secure Field Intelligence Platform',
    ].join('\n')

    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = `elohimos-backup-codes-${Date.now()}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.success('Backup codes downloaded')
  }

  async function copyCode(code: string, index: number) {
    try {
      await navigator.clipboard.writeText(code)
      setCopiedIndex(index)
      toast.success('Code copied to clipboard')

      setTimeout(() => {
        setCopiedIndex(null)
      }, 2000)
    } catch (error) {
      toast.error('Failed to copy code')
    }
  }

  async function copyAllCodes() {
    try {
      const text = codes.join('\n')
      await navigator.clipboard.writeText(text)
      toast.success('All codes copied to clipboard')
    } catch (error) {
      toast.error('Failed to copy codes')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
            Backup Codes for Vault Access
          </h4>
          <p className="text-sm text-amber-700 dark:text-amber-300">
            Save these codes securely. Each code can be used <strong>once</strong> to access your vault
            if you lose access to your password or Touch ID. Store them offline in a safe location.
          </p>
        </div>
      </div>

      {!revealed ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <Key className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Generate Backup Codes
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            Create 10 one-time backup codes for emergency vault access
          </p>
          <button
            onClick={generateCodes}
            disabled={isGenerating}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? 'Generating...' : 'Generate 10 Backup Codes'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Your Backup Codes
            </h3>
            <div className="flex gap-2">
              <button
                onClick={copyAllCodes}
                className="px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200
                         dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg
                         flex items-center gap-2 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy All
              </button>
              <button
                onClick={downloadCodes}
                className="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                         flex items-center gap-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                Download as Text File
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {codes.map((code, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800
                         rounded-lg border border-gray-200 dark:border-gray-700 group"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400 w-6">
                    {i + 1}.
                  </span>
                  <code className="text-sm font-mono font-semibold text-gray-900 dark:text-gray-100 select-all">
                    {code}
                  </code>
                </div>
                <button
                  onClick={() => copyCode(code, i)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700
                           rounded transition-all"
                  title="Copy code"
                >
                  {copiedIndex === i ? (
                    <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  )}
                </button>
              </div>
            ))}
          </div>

          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-semibold text-red-900 dark:text-red-100 mb-1">
                  Important Security Notice
                </p>
                <ul className="text-red-700 dark:text-red-300 space-y-1 list-disc list-inside">
                  <li>Each code can only be used <strong>once</strong></li>
                  <li>Store these codes offline in a secure location</li>
                  <li>Do not share these codes with anyone</li>
                  <li>Generate new codes after using any code</li>
                  <li>These codes provide full vault access - treat like passwords</li>
                </ul>
              </div>
            </div>
          </div>

          <button
            onClick={generateCodes}
            disabled={isGenerating}
            className="w-full px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200
                     dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? 'Generating...' : 'Generate New Codes'}
          </button>
        </div>
      )}
    </div>
  )
}
