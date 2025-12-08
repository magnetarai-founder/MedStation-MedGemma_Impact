export const CATEGORY_OPTIONS = [
  { value: 'clinic', label: 'Clinic', emoji: '🏥' },
  { value: 'ministry', label: 'Ministry', emoji: '⛪' },
  { value: 'admin', label: 'Admin', emoji: '💰' },
  { value: 'education', label: 'Education', emoji: '📚' },
  { value: 'travel', label: 'Travel', emoji: '✈️' }
] as const

export const CATEGORY_INFO = {
  clinic: { label: 'Clinic', emoji: '🏥', color: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' },
  ministry: { label: 'Ministry', emoji: '⛪', color: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800' },
  admin: { label: 'Admin', emoji: '💰', color: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' },
  education: { label: 'Education', emoji: '📚', color: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' },
  travel: { label: 'Travel', emoji: '✈️', color: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' }
}

export type TemplateCategory = 'clinic' | 'ministry' | 'admin' | 'education' | 'travel'
