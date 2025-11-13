/**
 * Welcome Step - Introduction to ElohimOS setup
 */

import { Zap } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'

interface WelcomeStepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
}

export default function WelcomeStep({ onNext }: WelcomeStepProps) {
  return (
    <div className="max-w-2xl mx-auto text-center">
      {/* Icon */}
      <div className="flex justify-center mb-6">
        <div className="p-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl shadow-lg">
          <Zap className="w-12 h-12 text-white" />
        </div>
      </div>

      {/* Title */}
      <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
        Welcome to ElohimOS
      </h2>

      <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
        Offline-First AI Operating System
      </p>

      {/* Scripture */}
      <blockquote className="mb-8 px-6 py-4 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg">
        <p className="text-sm italic text-gray-700 dark:text-gray-300">
          "Trust in the Lord with all your heart and lean not on your own understanding"
        </p>
        <footer className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          — Proverbs 3:5-6
        </footer>
      </blockquote>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-2xl mb-2">🔒</div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
            100% Offline
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            All data stays on your device
          </p>
        </div>

        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-2xl mb-2">🤖</div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
            Local AI
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Powered by Ollama models
          </p>
        </div>

        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-2xl mb-2">⚡</div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
            GPU Accelerated
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Metal 4 optimization
          </p>
        </div>
      </div>

      {/* Get Started Button */}
      <button
        onClick={onNext}
        className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg shadow-lg hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105"
      >
        Get Started
      </button>

      <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
        Setup takes about 5-10 minutes
      </p>
    </div>
  )
}
