/**
 * ProfileSettings Types
 *
 * TypeScript interfaces and types for the ProfileSettings component
 */

import { LucideIcon } from 'lucide-react'

export type ProfileTab = 'identity' | 'security' | 'updates' | 'privacy' | 'danger'

export interface UserProfile {
  user_id: string
  display_name: string
  device_name: string
  avatar_color: string
  bio: string
  role: string
  job_role: string
  role_changed_at?: string
  role_changed_by?: string
}

export interface SecuritySettings {
  stealth_labels: boolean
  decoy_mode_enabled: boolean
  require_touch_id: boolean
  lock_on_exit: boolean
  disable_screenshots: boolean
  inactivity_lock: 'instant' | '30s' | '1m' | '2m' | '3m' | '4m' | '5m'
}

export interface BiometricState {
  biometricAvailable: boolean
  biometricRegistered: boolean
  checkingBiometric: boolean
}

export interface ProfileFormState {
  displayName: string
  deviceName: string
  avatarColor: string
  bio: string
  jobRole: string
  hasUnsavedChanges: boolean
}

export interface ProfileFormHandlers {
  setDisplayName: (value: string) => void
  setDeviceName: (value: string) => void
  setAvatarColor: (value: string) => void
  setBio: (value: string) => void
  setJobRole: (value: string) => void
  handleSave: () => Promise<void>
}

export interface BiometricHandlers {
  handleRegisterBiometric: () => Promise<void>
}

export interface DangerHandlers {
  handleLogout: () => void
  handleResetIdentity: () => Promise<void>
  handleDeleteAllData: () => void
  handleFactoryReset: () => void
}

export interface ServerControlHandlers {
  handleStartOllama: () => Promise<void>
  handleStopOllama: () => Promise<void>
  handleRestartOllama: () => Promise<void>
  handleStartBackend: () => Promise<void>
  handleStopBackend: () => Promise<void>
  handleRestartBackend: () => Promise<void>
  handleStartWebSocket: () => Promise<void>
  handleStopWebSocket: () => Promise<void>
  handleRestartWebSocket: () => Promise<void>
}

export interface SystemRefreshHandlers {
  handleRefreshOllama: () => Promise<void>
  handleRefreshDatabases: () => Promise<void>
  handleReloadBackend: () => Promise<void>
  handleClearCache: () => Promise<void>
}

export interface PrivacyHandlers {
  handleExportData: () => void
  handleImportBackup: () => void
}

export interface TabConfig {
  id: ProfileTab
  label: string
  icon: LucideIcon
}
