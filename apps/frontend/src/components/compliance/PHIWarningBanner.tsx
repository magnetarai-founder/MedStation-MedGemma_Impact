/**
 * PHI Warning Banner Component
 *
 * Detects potential Protected Health Information (PHI) in text content
 * Displays HIPAA compliance warnings when health data is detected
 */

import { useState, useEffect } from 'react'
import { AlertTriangle, X, Shield, FileText } from 'lucide-react'

interface PHIWarningBannerProps {
  content: string
  onDismiss?: () => void
  autoDetect?: boolean
  className?: string
}

// Common PHI indicators and medical terms
const PHI_KEYWORDS = [
  // Medical conditions
  'diagnosis', 'diagnosed', 'disease', 'disorder', 'syndrome', 'condition',
  'cancer', 'diabetes', 'hypertension', 'asthma', 'depression', 'anxiety',
  'infection', 'virus', 'bacterial', 'chronic', 'acute',

  // Medications
  'medication', 'prescription', 'drug', 'dosage', 'mg', 'ml',
  'antibiotic', 'insulin', 'aspirin', 'ibuprofen', 'treatment',

  // Medical procedures
  'surgery', 'operation', 'procedure', 'biopsy', 'scan', 'x-ray',
  'mri', 'ct scan', 'ultrasound', 'test results', 'lab work',

  // Medical professionals
  'doctor', 'physician', 'surgeon', 'psychiatrist', 'therapist',
  'nurse', 'medical', 'clinical', 'hospital', 'clinic',

  // Body systems
  'blood pressure', 'heart rate', 'pulse', 'temperature',
  'symptoms', 'pain', 'fever', 'nausea', 'vomiting',

  // Medical identifiers
  'patient', 'medical record', 'health insurance', 'ssn',
  'social security', 'medical history', 'allergies',

  // Sensitive health data
  'mental health', 'substance abuse', 'hiv', 'aids',
  'reproductive health', 'pregnancy', 'abortion',
]

export function PHIWarningBanner({
  content,
  onDismiss,
  autoDetect = true,
  className = '',
}: PHIWarningBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false)
  const [phiDetected, setPhiDetected] = useState(false)
  const [detectedTerms, setDetectedTerms] = useState<string[]>([])

  useEffect(() => {
    if (autoDetect && content) {
      detectPHI(content)
    }
  }, [content, autoDetect])

  function detectPHI(text: string) {
    const lowerText = text.toLowerCase()
    const detected: string[] = []

    for (const keyword of PHI_KEYWORDS) {
      if (lowerText.includes(keyword.toLowerCase())) {
        detected.push(keyword)
      }
    }

    // Check for potential patterns (SSN, phone, etc.)
    const ssnPattern = /\b\d{3}-\d{2}-\d{4}\b/
    const phonePattern = /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/
    const datePattern = /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/

    if (ssnPattern.test(text)) {
      detected.push('SSN pattern')
    }
    if (phonePattern.test(text)) {
      detected.push('phone number')
    }
    if (datePattern.test(text) && detected.length > 0) {
      // Only flag dates if other PHI indicators present
      detected.push('date')
    }

    setDetectedTerms(detected)
    setPhiDetected(detected.length > 0)
  }

  function handleDismiss() {
    setIsDismissed(true)
    onDismiss?.()
  }

  // Don't show banner if dismissed or no PHI detected
  if (isDismissed || !phiDetected) {
    return null
  }

  return (
    <div
      className={`bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 dark:border-amber-600 p-4 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />

        <div className="flex-1">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
              Potential Health Information Detected
            </h4>
            <button
              onClick={handleDismiss}
              className="p-1 text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40
                       rounded transition-colors"
              aria-label="Dismiss warning"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className="text-sm text-amber-800 dark:text-amber-300 mb-3">
            This document may contain Protected Health Information (PHI) subject to HIPAA regulations.
            Please ensure proper security measures are in place before sharing.
          </p>

          {detectedTerms.length > 0 && detectedTerms.length <= 5 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">
                Detected terms:
              </p>
              <div className="flex flex-wrap gap-1">
                {detectedTerms.slice(0, 5).map((term, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                             bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300"
                  >
                    {term}
                  </span>
                ))}
                {detectedTerms.length > 5 && (
                  <span className="text-xs text-amber-700 dark:text-amber-400">
                    +{detectedTerms.length - 5} more
                  </span>
                )}
              </div>
            </div>
          )}

          <div className="flex items-start gap-2 p-3 bg-white dark:bg-gray-800/50 rounded-lg border border-amber-200 dark:border-amber-800/50">
            <Shield className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-700 dark:text-amber-300">
              <p className="font-semibold mb-1">HIPAA Compliance Reminder:</p>
              <ul className="space-y-0.5">
                <li>• Store PHI in the encrypted vault only</li>
                <li>• Do not share PHI via unencrypted channels</li>
                <li>• Obtain patient consent before disclosure</li>
                <li>• Log all access to PHI for audit purposes</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Inline PHI Warning Badge
 *
 * Smaller inline version for use in document lists or chat messages
 */
interface PHIBadgeProps {
  onClick?: () => void
}

export function PHIBadge({ onClick }: PHIBadgeProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30
               text-amber-800 dark:text-amber-300 rounded text-xs font-medium
               hover:bg-amber-200 dark:hover:bg-amber-900/40 transition-colors"
      title="Contains potential health information"
    >
      <Shield className="w-3 h-3" />
      PHI
    </button>
  )
}

/**
 * PHI Modal Dialog
 *
 * Full-screen modal for detailed PHI compliance information
 */
interface PHIModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PHIModal({ isOpen, onClose }: PHIModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="phi-modal-title"
      >
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <Shield className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <h2
                id="phi-modal-title"
                className="text-xl font-bold text-gray-900 dark:text-gray-100"
              >
                Protected Health Information (PHI)
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              aria-label="Close dialog"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-6">
            <section>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                What is PHI?
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Protected Health Information (PHI) is any health information that can be linked to
                a specific individual. Under HIPAA regulations, PHI must be protected with appropriate
                safeguards to ensure confidentiality, integrity, and availability.
              </p>
            </section>

            <section>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Examples of PHI
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { icon: FileText, label: 'Medical Records', items: ['Diagnoses', 'Test results', 'Treatment plans'] },
                  { icon: Shield, label: 'Personal Identifiers', items: ['SSN', 'Medical record numbers', 'Insurance info'] },
                  { icon: FileText, label: 'Health Data', items: ['Prescriptions', 'Lab results', 'Clinical notes'] },
                  { icon: Shield, label: 'Demographic Info', items: ['Names with health data', 'Dates of service', 'Contact info'] },
                ].map((category, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <category.icon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                      <h4 className="font-medium text-sm text-gray-900 dark:text-gray-100">
                        {category.label}
                      </h4>
                    </div>
                    <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
                      {category.items.map((item, itemIdx) => (
                        <li key={itemIdx}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Best Practices
              </h3>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-0.5">✓</span>
                  <span>Store all PHI in the encrypted vault with appropriate access controls</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-0.5">✓</span>
                  <span>Use end-to-end encryption when sharing PHI electronically</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-0.5">✓</span>
                  <span>Maintain audit logs of all PHI access and modifications</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-600 dark:text-green-400 mt-0.5">✓</span>
                  <span>Obtain proper authorization before disclosing PHI</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-600 dark:text-red-400 mt-0.5">✗</span>
                  <span>Never share PHI via unencrypted email or messaging</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-600 dark:text-red-400 mt-0.5">✗</span>
                  <span>Avoid storing PHI in unencrypted documents or databases</span>
                </li>
              </ul>
            </section>

            <section className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-800 dark:text-blue-300">
                <strong>Note:</strong> ElohimOS provides encrypted vault storage and audit logging
                to help maintain HIPAA compliance. However, proper use of these features is the
                responsibility of each user and organization.
              </p>
            </section>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                       transition-colors"
            >
              I Understand
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
