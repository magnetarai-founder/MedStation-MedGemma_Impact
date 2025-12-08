/**
 * SettingToggle Component
 *
 * Reusable toggle switch with label, description, and icon
 */

import { LucideIcon } from 'lucide-react'

interface SettingToggleProps {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
  icon: LucideIcon
  className?: string
}

export function SettingToggle({
  label,
  description,
  checked,
  onChange,
  icon: Icon,
  className = '',
}: SettingToggleProps) {
  return (
    <div className={`flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg ${className}`}>
      <div className="flex items-center gap-3">
        <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {label}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </div>
        </div>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-5 h-5 rounded text-primary-600"
      />
    </div>
  )
}
