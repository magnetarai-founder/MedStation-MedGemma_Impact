/**
 * InfoCard Component
 *
 * Gradient info card with icon, title, and description
 */

import { LucideIcon } from 'lucide-react'

interface InfoCardProps {
  title: string
  description: string | React.ReactNode
  icon: LucideIcon
  gradient: 'green' | 'blue' | 'amber' | 'red'
  children?: React.ReactNode
}

const gradientStyles = {
  green: 'from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800',
  blue: 'from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800',
  amber: 'from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20 border-amber-200 dark:border-amber-800',
  red: 'from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 border-red-200 dark:border-red-800',
}

const iconStyles = {
  green: 'text-green-600 dark:text-green-400',
  blue: 'text-blue-600 dark:text-blue-400',
  amber: 'text-amber-600 dark:text-amber-400',
  red: 'text-red-600 dark:text-red-400',
}

const titleStyles = {
  green: 'text-green-900 dark:text-green-100',
  blue: 'text-blue-900 dark:text-blue-100',
  amber: 'text-amber-900 dark:text-amber-100',
  red: 'text-red-900 dark:text-red-100',
}

const descStyles = {
  green: 'text-green-700 dark:text-green-300',
  blue: 'text-blue-700 dark:text-blue-300',
  amber: 'text-amber-700 dark:text-amber-300',
  red: 'text-red-700 dark:text-red-300',
}

export function InfoCard({ title, description, icon: Icon, gradient, children }: InfoCardProps) {
  return (
    <div className={`p-4 bg-gradient-to-br ${gradientStyles[gradient]} border rounded-lg`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className={`w-5 h-5 ${iconStyles[gradient]}`} />
        <h4 className={`font-semibold ${titleStyles[gradient]}`}>
          {title}
        </h4>
      </div>
      <div className={`text-sm ${descStyles[gradient]}`}>
        {description}
      </div>
      {children}
    </div>
  )
}
