import { SetupWizardState } from '../SetupWizard'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

export default function ModelsStep(props: StepProps) {
  return (
    <div className="text-center p-8">
      <h2 className="text-2xl font-bold mb-4">ModelsStep</h2>
      <p className="text-gray-600 mb-6">This step is under construction.</p>
      <button
        onClick={props.onNext || props.onComplete}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Continue
      </button>
    </div>
  )
}
