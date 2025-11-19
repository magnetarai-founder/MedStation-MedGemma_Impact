/**
 * SettingsTab - DEPRECATED
 *
 * This legacy component has been replaced by the modular settings architecture.
 * It is kept only as a thin wrapper around AppSettingsTab for backwards compatibility.
 *
 * The new modular settings architecture consists of:
 * - SettingsModal: Main settings modal with tabbed interface
 * - AppSettingsTab: App settings (replaces all of this file's functionality)
 * - ChatTab: Chat and AI settings
 * - ModelsTab: AI model management
 * - AutomationTab: Automation settings
 * - AdvancedTab: Advanced settings
 * - ProfileSettings: Profile settings
 *
 * @deprecated Use SettingsModal or AppSettingsTab directly instead.
 */

import AppSettingsTab from './AppSettingsTab'
import type { NavTab } from '@/stores/navigationStore'

interface SettingsTabProps {
  activeNavTab: NavTab
}

export default function SettingsTab({ activeNavTab }: SettingsTabProps) {
  return <AppSettingsTab activeNavTab={activeNavTab} />
}
