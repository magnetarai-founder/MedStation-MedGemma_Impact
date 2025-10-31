/**
 * Focus Mode Selector Component
 *
 * Allows users to filter content by focus area (work, health, finance, etc.)
 * Displayed in the application header for quick access
 */

import { useState, useEffect, useRef } from 'react'
import {
  Briefcase,
  Heart,
  DollarSign,
  Home,
  Sparkles,
  GraduationCap,
  Users,
  Globe,
  ChevronDown,
  Check,
} from 'lucide-react'

export type FocusMode =
  | 'all'
  | 'work'
  | 'health'
  | 'finance'
  | 'personal'
  | 'learning'
  | 'social'
  | 'travel'

interface FocusModeConfig {
  id: FocusMode
  label: string
  icon: any
  color: string
  description: string
}

const FOCUS_MODES: FocusModeConfig[] = [
  {
    id: 'all',
    label: 'All',
    icon: Sparkles,
    color: 'text-gray-600 dark:text-gray-400',
    description: 'Show all content without filtering',
  },
  {
    id: 'work',
    label: 'Work',
    icon: Briefcase,
    color: 'text-blue-600 dark:text-blue-400',
    description: 'Focus on work-related tasks and documents',
  },
  {
    id: 'health',
    label: 'Health',
    icon: Heart,
    color: 'text-red-600 dark:text-red-400',
    description: 'Health data, medical records, and wellness tracking',
  },
  {
    id: 'finance',
    label: 'Finance',
    icon: DollarSign,
    color: 'text-green-600 dark:text-green-400',
    description: 'Financial documents, budgets, and transactions',
  },
  {
    id: 'personal',
    label: 'Personal',
    icon: Home,
    color: 'text-purple-600 dark:text-purple-400',
    description: 'Personal notes, journals, and private documents',
  },
  {
    id: 'learning',
    label: 'Learning',
    icon: GraduationCap,
    color: 'text-amber-600 dark:text-amber-400',
    description: 'Educational content, courses, and study materials',
  },
  {
    id: 'social',
    label: 'Social',
    icon: Users,
    color: 'text-pink-600 dark:text-pink-400',
    description: 'Social connections, events, and communications',
  },
  {
    id: 'travel',
    label: 'Travel',
    icon: Globe,
    color: 'text-cyan-600 dark:text-cyan-400',
    description: 'Travel plans, itineraries, and trip documents',
  },
]

interface FocusModeSelectorProps {
  currentMode?: FocusMode
  onChange?: (mode: FocusMode) => void
  className?: string
}

export function FocusModeSelector({
  currentMode: controlledMode,
  onChange,
  className = '',
}: FocusModeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [internalMode, setInternalMode] = useState<FocusMode>('all')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Use controlled mode if provided, otherwise use internal state
  const currentMode = controlledMode ?? internalMode

  // Load saved focus mode on mount
  useEffect(() => {
    if (!controlledMode) {
      const savedMode = localStorage.getItem('elohim_focus_mode') as FocusMode
      if (savedMode && FOCUS_MODES.some((m) => m.id === savedMode)) {
        setInternalMode(savedMode)
      }
    }
  }, [controlledMode])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  function handleModeChange(mode: FocusMode) {
    if (!controlledMode) {
      setInternalMode(mode)
      localStorage.setItem('elohim_focus_mode', mode)
    }

    onChange?.(mode)
    setIsOpen(false)

    // Emit custom event for other components to listen to
    window.dispatchEvent(
      new CustomEvent('focusModeChanged', {
        detail: { mode },
      })
    )
  }

  const currentConfig = FOCUS_MODES.find((m) => m.id === currentMode) || FOCUS_MODES[0]
  const CurrentIcon = currentConfig.icon

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label="Select focus mode"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <CurrentIcon className={`w-4 h-4 ${currentConfig.color}`} />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {currentConfig.label}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-gray-400 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                   rounded-lg shadow-xl z-50 overflow-hidden"
          role="menu"
        >
          <div className="p-2">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Focus Mode
            </div>
            {FOCUS_MODES.map((mode) => {
              const Icon = mode.icon
              const isSelected = mode.id === currentMode

              return (
                <button
                  key={mode.id}
                  onClick={() => handleModeChange(mode.id)}
                  className="w-full flex items-start gap-3 px-3 py-2.5 rounded-lg
                           hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
                           text-left group"
                  role="menuitem"
                >
                  <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${mode.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`text-sm font-medium ${
                          isSelected
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-gray-900 dark:text-gray-100'
                        }`}
                      >
                        {mode.label}
                      </span>
                      {isSelected && (
                        <Check className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {mode.description}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Compact Focus Mode Badge
 *
 * Small inline indicator of current focus mode
 */
interface FocusModeBadgeProps {
  mode: FocusMode
  onClick?: () => void
}

export function FocusModeBadge({ mode, onClick }: FocusModeBadgeProps) {
  const config = FOCUS_MODES.find((m) => m.id === mode) || FOCUS_MODES[0]
  const Icon = config.icon

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
               bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
               transition-colors border border-gray-200 dark:border-gray-600"
      title={`Focus: ${config.label}`}
    >
      <Icon className={`w-3 h-3 ${config.color}`} />
      <span className="text-gray-700 dark:text-gray-300">{config.label}</span>
    </button>
  )
}

/**
 * Hook to access current focus mode
 */
export function useFocusMode() {
  const [mode, setMode] = useState<FocusMode>(() => {
    const saved = localStorage.getItem('elohim_focus_mode') as FocusMode
    return saved && FOCUS_MODES.some((m) => m.id === saved) ? saved : 'all'
  })

  useEffect(() => {
    function handleModeChange(event: Event) {
      const customEvent = event as CustomEvent<{ mode: FocusMode }>
      setMode(customEvent.detail.mode)
    }

    window.addEventListener('focusModeChanged', handleModeChange)
    return () => window.removeEventListener('focusModeChanged', handleModeChange)
  }, [])

  function changeMode(newMode: FocusMode) {
    setMode(newMode)
    localStorage.setItem('elohim_focus_mode', newMode)
    window.dispatchEvent(
      new CustomEvent('focusModeChanged', {
        detail: { mode: newMode },
      })
    )
  }

  return { mode, changeMode }
}

/**
 * Helper function to check if content matches current focus mode
 */
export function matchesFocusMode(contentTags: string[], currentMode: FocusMode): boolean {
  if (currentMode === 'all') return true

  // Check if any content tag matches the focus mode
  return contentTags.some((tag) => tag.toLowerCase() === currentMode.toLowerCase())
}

/**
 * Focus Mode Context Banner
 *
 * Shows a banner indicating current focus mode (optional, for visibility)
 */
interface FocusModeContextBannerProps {
  mode: FocusMode
  onClear?: () => void
}

export function FocusModeContextBanner({ mode, onClear }: FocusModeContextBannerProps) {
  if (mode === 'all') return null

  const config = FOCUS_MODES.find((m) => m.id === mode)
  if (!config) return null

  const Icon = config.icon

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
      <div className="flex items-center gap-2">
        <Icon className={`w-4 h-4 ${config.color}`} />
        <span className="text-sm text-blue-800 dark:text-blue-300">
          Filtering by <strong>{config.label}</strong> mode
        </span>
      </div>
      {onClear && (
        <button
          onClick={onClear}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Show all
        </button>
      )}
    </div>
  )
}
