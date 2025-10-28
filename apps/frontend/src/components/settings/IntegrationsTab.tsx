// n8n integration disabled - keeping for future use
// import { N8NConfig } from '../N8NConfig'

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

      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <p>No integrations configured</p>
        <p className="text-sm mt-2">External integrations will be available in a future update</p>
      </div>

      {/* n8n integration disabled - keeping for future use */}
      {/* <N8NConfig /> */}
    </div>
  )
}
