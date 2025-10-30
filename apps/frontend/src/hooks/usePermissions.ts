/**
 * usePermissions Hook
 *
 * Provides easy access to role-based permissions throughout the app
 */

import { useMemo } from 'react'
import { useUserStore } from '@/stores/userStore'
import {
  isGodRights,
  isSuperAdmin,
  isAdmin,
  isMember,
  isGuest,
  hasElevatedPermissions,
  canManageTeam,
  canManageWorkflows,
  canAccessTeamVault,
  canUseTerminal,
  canManageRole,
  getPromotableRoles,
  formatRole,
  getRoleDescription,
  getRoleColor,
  ROLES,
  type Role,
} from '@/lib/roles'

export interface Permissions {
  // Role checks
  isGodRights: boolean
  isSuperAdmin: boolean
  isAdmin: boolean
  isMember: boolean
  isGuest: boolean

  // General permissions
  hasElevatedPermissions: boolean
  canManageTeam: boolean
  canManageWorkflows: boolean
  canAccessTeamVault: boolean
  canUseTerminal: boolean

  // Feature access
  canAccessWorkflows: boolean
  canAccessDocuments: boolean
  canAccessVault: boolean
  canAccessAutomation: boolean
  canAccessChat: boolean
  canAccessTeamChat: boolean
  canAccessFileShare: boolean

  // UI helpers
  role?: string
  formatRole: string
  roleDescription: string
  roleColor: string

  // Management helpers
  canManageRole: (targetRole?: string) => boolean
  promotableRoles: Role[]
}

/**
 * Hook to get current user's permissions
 */
export function usePermissions(): Permissions {
  const { user } = useUserStore()
  const role = user?.role

  return useMemo(() => {
    // Role checks
    const _isGodRights = isGodRights(role)
    const _isSuperAdmin = isSuperAdmin(role)
    const _isAdmin = isAdmin(role)
    const _isMember = isMember(role)
    const _isGuest = isGuest(role)

    // General permissions
    const _hasElevatedPermissions = hasElevatedPermissions(role)
    const _canManageTeam = canManageTeam(role)
    const _canManageWorkflows = canManageWorkflows(role)
    const _canAccessTeamVault = canAccessTeamVault(role)
    const _canUseTerminal = canUseTerminal(role)

    // Feature access
    // Guests can only access Team Chat and File Share
    const _canAccessWorkflows = !_isGuest
    const _canAccessDocuments = !_isGuest
    const _canAccessVault = !_isGuest
    const _canAccessAutomation = !_isGuest
    const _canAccessChat = true // Everyone can use AI chat
    const _canAccessTeamChat = true // Everyone can use team chat
    const _canAccessFileShare = true // Everyone can share files

    return {
      // Role checks
      isGodRights: _isGodRights,
      isSuperAdmin: _isSuperAdmin,
      isAdmin: _isAdmin,
      isMember: _isMember,
      isGuest: _isGuest,

      // General permissions
      hasElevatedPermissions: _hasElevatedPermissions,
      canManageTeam: _canManageTeam,
      canManageWorkflows: _canManageWorkflows,
      canAccessTeamVault: _canAccessTeamVault,
      canUseTerminal: _canUseTerminal,

      // Feature access
      canAccessWorkflows: _canAccessWorkflows,
      canAccessDocuments: _canAccessDocuments,
      canAccessVault: _canAccessVault,
      canAccessAutomation: _canAccessAutomation,
      canAccessChat: _canAccessChat,
      canAccessTeamChat: _canAccessTeamChat,
      canAccessFileShare: _canAccessFileShare,

      // UI helpers
      role,
      formatRole: formatRole(role),
      roleDescription: getRoleDescription(role),
      roleColor: getRoleColor(role),

      // Management helpers
      canManageRole: (targetRole?: string) => canManageRole(role, targetRole),
      promotableRoles: getPromotableRoles(role),
    }
  }, [role])
}

/**
 * Hook to check if a specific feature is accessible
 */
export function useFeatureAccess(feature: keyof Pick<Permissions,
  'canAccessWorkflows' |
  'canAccessDocuments' |
  'canAccessVault' |
  'canAccessAutomation' |
  'canAccessChat' |
  'canAccessTeamChat' |
  'canAccessFileShare'
>): boolean {
  const permissions = usePermissions()
  return permissions[feature]
}

/**
 * Hook to check if user has a specific permission
 */
export function useHasPermission(permission: keyof Omit<Permissions,
  'role' |
  'formatRole' |
  'roleDescription' |
  'roleColor' |
  'canManageRole' |
  'promotableRoles'
>): boolean {
  const permissions = usePermissions()
  return permissions[permission] as boolean
}
