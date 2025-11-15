/**
 * Medical Disclaimer Modal Component
 *
 * Displays medical disclaimer before showing AI-generated health insights
 * Required for compliance with medical information regulations
 */

import { useState, useEffect } from 'react'
import { AlertTriangle, Heart, Phone, X, Shield } from 'lucide-react'

interface MedicalDisclaimerModalProps {
  isOpen: boolean
  onAccept: () => void
  onDecline: () => void
  insightType?: 'general' | 'symptom' | 'medication' | 'diagnosis'
}

export function MedicalDisclaimerModal({
  isOpen,
  onAccept,
  onDecline,
  insightType = 'general',
}: MedicalDisclaimerModalProps) {
  const [dontShowAgain, setDontShowAgain] = useState(false)

  // Handle Escape key to decline
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onDecline()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onDecline])

  if (!isOpen) return null

  function handleAccept() {
    if (dontShowAgain) {
      // Store preference in localStorage
      localStorage.setItem('elohim_medical_disclaimer_accepted', 'true')
      localStorage.setItem('elohim_medical_disclaimer_accepted_at', new Date().toISOString())
    }
    onAccept()
  }

  function handleDecline() {
    onDecline()
  }

  const insightTypeLabels = {
    general: 'health insights',
    symptom: 'symptom analysis',
    medication: 'medication information',
    diagnosis: 'diagnostic insights',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="medical-disclaimer-title"
      >
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h2
                  id="medical-disclaimer-title"
                  className="text-2xl font-bold text-gray-900 dark:text-gray-100"
                >
                  Medical Disclaimer
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Important information about {insightTypeLabels[insightType]}
                </p>
              </div>
            </div>
          </div>

          {/* Emergency Warning */}
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg">
            <div className="flex items-start gap-3">
              <Phone className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-red-900 dark:text-red-100 mb-1">
                  Medical Emergency?
                </h3>
                <p className="text-sm text-red-800 dark:text-red-300">
                  If you are experiencing a medical emergency, call <strong>911</strong> immediately
                  or go to the nearest emergency room. Do not rely on AI-generated information
                  for emergency medical situations.
                </p>
              </div>
            </div>
          </div>

          {/* Main Disclaimer Content */}
          <div className="space-y-4 mb-6">
            <section className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Not Medical Advice
              </h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                The information provided by ElohimOS, including AI-generated insights, is for
                <strong> educational and informational purposes only</strong>. It is not intended
                to be a substitute for professional medical advice, diagnosis, or treatment.
              </p>
            </section>

            <section className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
                <Heart className="w-4 h-4" />
                Always Consult Healthcare Professionals
              </h3>
              <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                  <span>
                    Always seek the advice of your physician or other qualified health provider
                    with any questions regarding a medical condition
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                  <span>
                    Never disregard professional medical advice or delay seeking it because of
                    information provided by this application
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 dark:text-blue-400 mt-0.5">•</span>
                  <span>
                    If you think you may have a medical emergency, call your doctor or 911 immediately
                  </span>
                </li>
              </ul>
            </section>

            <section className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                AI Limitations
              </h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                AI-generated health insights are based on patterns in training data and may not
                account for your unique medical history, current conditions, medications, or other
                individual factors. AI systems can make mistakes and should never be used as the
                sole basis for medical decisions.
              </p>
            </section>

            <section className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                No Doctor-Patient Relationship
              </h3>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                Use of this application does not create a doctor-patient relationship. ElohimOS
                and its AI features are not a substitute for professional medical care, and no
                warranties or guarantees are made regarding the accuracy or completeness of
                health-related information.
              </p>
            </section>
          </div>

          {/* Legal Notice */}
          <div className="mb-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <p className="text-xs text-blue-800 dark:text-blue-300 leading-relaxed">
              <strong>Legal Notice:</strong> By accepting this disclaimer, you acknowledge that
              you have read and understood these terms. You agree to use ElohimOS's health insights
              at your own risk and will consult with appropriate healthcare professionals for all
              medical decisions. ElohimOS, its developers, and affiliates assume no liability for
              any decisions made based on AI-generated information.
            </p>
          </div>

          {/* Don't Show Again Option */}
          <div className="mb-6">
            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={(e) => setDontShowAgain(e.target.checked)}
                className="mt-1 w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded
                         focus:ring-blue-500 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100">
                I understand and accept the terms above. Don't show this disclaimer again.
              </span>
            </label>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleDecline}
              className="px-6 py-2.5 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600
                       text-gray-800 dark:text-gray-200 rounded-lg font-medium transition-colors"
            >
              Decline
            </button>
            <button
              onClick={handleAccept}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                       transition-colors shadow-sm"
            >
              I Understand & Accept
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Hook to check if medical disclaimer has been accepted
 */
export function useMedicalDisclaimerStatus() {
  const [isAccepted, setIsAccepted] = useState(() => {
    return localStorage.getItem('elohim_medical_disclaimer_accepted') === 'true'
  })

  const acceptDisclaimer = () => {
    localStorage.setItem('elohim_medical_disclaimer_accepted', 'true')
    localStorage.setItem('elohim_medical_disclaimer_accepted_at', new Date().toISOString())
    setIsAccepted(true)
  }

  const resetDisclaimer = () => {
    localStorage.removeItem('elohim_medical_disclaimer_accepted')
    localStorage.removeItem('elohim_medical_disclaimer_accepted_at')
    setIsAccepted(false)
  }

  return {
    isAccepted,
    acceptDisclaimer,
    resetDisclaimer,
  }
}

/**
 * Inline Medical Disclaimer Notice
 *
 * Small inline notice for use in health-related features
 */
export function MedicalDisclaimerNotice() {
  return (
    <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
      <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
      <p className="text-xs text-amber-800 dark:text-amber-300">
        This information is for educational purposes only and is not medical advice.
        Consult a healthcare professional for medical concerns.
      </p>
    </div>
  )
}
