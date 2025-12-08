interface FormatNamingRowProps {
  format: string
  defaultPattern: string
  value: string | null | undefined
  onChange: (val: string | null) => void
}

export default function FormatNamingRow({
  format,
  defaultPattern,
  value,
  onChange
}: FormatNamingRowProps) {
  const mode = value ? 'custom' : 'default'

  return (
    <div className="flex items-center space-x-3 mb-2">
      <label className="w-20 text-sm text-gray-700 dark:text-gray-300">{format}:</label>
      <select
        value={mode}
        onChange={(e) => {
          if (e.target.value === 'default') {
            onChange(null)
          } else {
            onChange(defaultPattern)
          }
        }}
        className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
      >
        <option value="default">Default</option>
        <option value="custom">Custom</option>
      </select>
      {mode === 'custom' && (
        <input
          type="text"
          value={value || defaultPattern}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Custom pattern"
          className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
        />
      )}
    </div>
  )
}
