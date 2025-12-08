/**
 * Setup Wizard - First-run onboarding for MagnetarStudio
 *
 * "Trust in the Lord with all your heart" - Proverbs 3:5
 *
 * Multi-step wizard for new user onboarding:
 * 1. Welcome
 * 2. Account Creation
 * 3. Ollama Detection
 * 4. Model Recommendations
 * 5. Model Downloads (optional)
 * 6. Hot Slot Configuration
 * 7. Completion
 *
 * Features:
 * - Stepper UI showing progress
 * - Skip optional steps
 * - Auto-detection of system resources
 * - Ollama installation guidance
 * - Model download progress tracking
 * - Hot slot drag-and-drop assignment
 */

import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import WelcomeStep from './steps/WelcomeStep'
import AccountStep from './steps/AccountStep'
import OllamaStep from './steps/OllamaStep'
import ModelsStep from './steps/ModelsStep'
import DownloadStep from './steps/DownloadStep'
import HotSlotsStep from './steps/HotSlotsStep'
import CompletionStep from './steps/CompletionStep'
import StepIndicator from './components/StepIndicator'
import { setupWizardApi } from '../../lib/setupWizardApi'

export interface SetupWizardState {
  // Account
  username: string
  password: string
  founderPassword: string | null
  userId: string | null

  // Ollama
  ollamaInstalled: boolean
  ollamaRunning: boolean
  ollamaVersion: string | null

  // System
  ramGb: number
  diskFreeGb: number
  recommendedTier: string

  // Models
  selectedModels: string[]
  downloadedModels: string[]

  // Hot slots
  hotSlots: { [key: number]: string | null }
}

const STEPS = [
  { id: 'welcome', name: 'Welcome', component: WelcomeStep, skippable: false },
  { id: 'account', name: 'Account', component: AccountStep, skippable: false },
  { id: 'ollama', name: 'Ollama', component: OllamaStep, skippable: false },
  { id: 'models', name: 'Models', component: ModelsStep, skippable: true },
  { id: 'download', name: 'Download', component: DownloadStep, skippable: true },
  { id: 'hot-slots', name: 'Hot Slots', component: HotSlotsStep, skippable: true },
  { id: 'completion', name: 'Complete', component: CompletionStep, skippable: false },
]

interface SetupWizardProps {
  onComplete: () => void
}

export default function SetupWizard({ onComplete }: SetupWizardProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [wizardState, setWizardState] = useState<SetupWizardState>({
    username: '',
    password: '',
    founderPassword: null,
    userId: null,
    ollamaInstalled: false,
    ollamaRunning: false,
    ollamaVersion: null,
    ramGb: 0,
    diskFreeGb: 0,
    recommendedTier: 'essential',
    selectedModels: [],
    downloadedModels: [],
    hotSlots: { 1: null, 2: null, 3: null, 4: null },
  })

  const CurrentStepComponent = STEPS[currentStep].component

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    if (STEPS[currentStep].skippable) {
      handleNext()
    }
  }

  const handleComplete = async () => {
    try {
      // Mark setup as complete
      await setupWizardApi.completeSetup()

      // Call parent completion handler
      onComplete()
    } catch (error) {
      console.error('Failed to complete setup:', error)
    }
  }

  const updateWizardState = (updates: Partial<SetupWizardState>) => {
    setWizardState(prev => ({ ...prev, ...updates }))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col border border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Welcome to MagnetarStudio
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Let's get you set up in just a few steps
          </p>

          {/* Step Indicator */}
          <div className="mt-6">
            <StepIndicator
              steps={STEPS.map(s => s.name)}
              currentStep={currentStep}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <CurrentStepComponent
            wizardState={wizardState}
            updateWizardState={updateWizardState}
            onNext={handleNext}
            onBack={handleBack}
            onComplete={handleComplete}
          />
        </div>

        {/* Footer Navigation */}
        <div className="px-8 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between">
            {/* Back Button */}
            <button
              onClick={handleBack}
              disabled={currentStep === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </button>

            {/* Skip Button (if step is skippable) */}
            {STEPS[currentStep].skippable && currentStep < STEPS.length - 1 && (
              <button
                onClick={handleSkip}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                Skip
              </button>
            )}

            {/* Progress Text */}
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Step {currentStep + 1} of {STEPS.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
