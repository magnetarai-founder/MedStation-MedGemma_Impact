import { N8NConfig } from '../N8NConfig'

export default function IntegrationsTab() {
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Third-Party Integrations
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          Connect ElohimOS with external automation and workflow tools
        </p>
      </div>

      <N8NConfig />
    </div>
  )
}
