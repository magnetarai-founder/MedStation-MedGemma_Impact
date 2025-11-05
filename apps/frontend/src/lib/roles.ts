/**
 * Role Management System
 *
 * Defines role hierarchy, permissions, and utility functions for ElohimOS
 */

// ============================================
// ROLE CONSTANTS
// ============================================

export const ROLES = {
  GOD_RIGHTS: 'founder_rights', // Matches backend role name
  SUPER_ADMIN: 'super_admin',
  ADMIN: 'admin',
  MEMBER: 'member',
  GUEST: 'guest',
} as const

export type Role = typeof ROLES[keyof typeof ROLES]

// ============================================
// ROLE METADATA
// ============================================

export const ROLE_INFO: Record<Role, {
  label: string
  emoji: string
  description: string
  color: string
  level: number // Higher = more permissions
}> = {
  [ROLES.GOD_RIGHTS]: {
    label: 'God Rights',
    emoji: '👑',
    description: 'Full system access - Can do everything',
    color: 'text-purple-600 dark:text-purple-400',
    level: 5,
  },
  [ROLES.SUPER_ADMIN]: {
    label: 'Super Admin',
    emoji: '🔑',
    description: 'Team leader - Can manage all users and workflows',
    color: 'text-red-600 dark:text-red-400',
    level: 4,
  },
  [ROLES.ADMIN]: {
    label: 'Admin',
    emoji: '⚙️',
    description: 'Trusted helper - Can manage users and edit workflows',
    color: 'text-orange-600 dark:text-orange-400',
    level: 3,
  },
  [ROLES.MEMBER]: {
    label: 'Member',
    emoji: '👤',
    description: 'Regular user - Can create and use workflows',
    color: 'text-blue-600 dark:text-blue-400',
    level: 2,
  },
  [ROLES.GUEST]: {
    label: 'Guest',
    emoji: '👋',
    description: 'Visitor - Team chat and file share only',
    color: 'text-gray-600 dark:text-gray-400',
    level: 1,
  },
}

// ============================================
// ROLE CHECK FUNCTIONS
// ============================================

export function isGodRights(role?: string): boolean {
  // Accept both 'founder_rights' (current) and 'god_rights' (legacy) for safety
  return role === ROLES.GOD_RIGHTS || role === 'god_rights'
}

export function isSuperAdmin(role?: string): boolean {
  return role === ROLES.SUPER_ADMIN
}

export function isAdmin(role?: string): boolean {
  return role === ROLES.ADMIN
}

export function isMember(role?: string): boolean {
  return role === ROLES.MEMBER
}

export function isGuest(role?: string): boolean {
  // Treat undefined/null/invalid as guest (restrictive security model)
  if (!role) return true

  // Check if it's a valid role at all
  const validRoles = Object.values(ROLES)
  if (!validRoles.includes(role as Role)) return true

  return role === ROLES.GUEST
}

/**
 * Check if role has elevated permissions (Admin or higher)
 */
export function hasElevatedPermissions(role?: string): boolean {
  return isGodRights(role) || isSuperAdmin(role) || isAdmin(role)
}

/**
 * Check if role has team management permissions (Super Admin or higher)
 */
export function canManageTeam(role?: string): boolean {
  return isGodRights(role) || isSuperAdmin(role)
}

/**
 * Check if role can manage workflows (Admin or higher)
 */
export function canManageWorkflows(role?: string): boolean {
  return hasElevatedPermissions(role)
}

/**
 * Check if role can access team vault
 */
export function canAccessTeamVault(role?: string): boolean {
  return !isGuest(role) // Everyone except guests
}

/**
 * Check if role can use terminal
 * Note: This can also be granted via custom permissions
 */
export function canUseTerminal(role?: string): boolean {
  return hasElevatedPermissions(role)
}

// ============================================
// ROLE HIERARCHY UTILITIES
// ============================================

/**
 * Get the numeric level of a role (higher = more permissions)
 */
export function getRoleLevel(role?: string): number {
  if (!role) return 0
  return ROLE_INFO[role as Role]?.level || 0
}

/**
 * Check if role1 has higher permissions than role2
 */
export function hasHigherRole(role1?: string, role2?: string): boolean {
  return getRoleLevel(role1) > getRoleLevel(role2)
}

/**
 * Check if role1 can manage role2 (promote/demote)
 * God Rights can manage everyone
 * Super Admin can manage Admin, Member, Guest
 * Admin can manage Member, Guest
 */
export function canManageRole(managerRole?: string, targetRole?: string): boolean {
  if (isGodRights(managerRole)) return true // God Rights can manage everyone
  if (isSuperAdmin(managerRole)) {
    // Super Admin can manage everyone except God Rights
    return !isGodRights(targetRole)
  }
  if (isAdmin(managerRole)) {
    // Admin can manage Member and Guest only
    return isMember(targetRole) || isGuest(targetRole)
  }
  return false
}

/**
 * Get list of roles that a user can promote others to
 */
export function getPromotableRoles(currentRole?: string): Role[] {
  if (isGodRights(currentRole)) {
    return [ROLES.GOD_RIGHTS, ROLES.SUPER_ADMIN, ROLES.ADMIN, ROLES.MEMBER, ROLES.GUEST]
  }
  if (isSuperAdmin(currentRole)) {
    return [ROLES.ADMIN, ROLES.MEMBER, ROLES.GUEST]
  }
  if (isAdmin(currentRole)) {
    return [ROLES.MEMBER, ROLES.GUEST]
  }
  return []
}

// ============================================
// SUPER ADMIN LIMITS
// ============================================

/**
 * Calculate max Super Admins based on team size
 */
export function getMaxSuperAdmins(teamSize: number): number {
  if (teamSize <= 5) return 1
  if (teamSize <= 15) return 2
  if (teamSize <= 30) return 3
  if (teamSize <= 50) return 4
  return 5
}

/**
 * Check if team can have more Super Admins
 */
export function canAddMoreSuperAdmins(
  currentSuperAdminCount: number,
  teamSize: number,
  requestorRole?: string
): boolean {
  // God Rights can always override limits
  if (isGodRights(requestorRole)) return true

  // Otherwise check against the limit
  return currentSuperAdminCount < getMaxSuperAdmins(teamSize)
}

// ============================================
// ROLE FORMATTING
// ============================================

/**
 * Get formatted role display with emoji
 */
export function formatRole(role?: string): string {
  if (!role) return 'No Role'
  const info = ROLE_INFO[role as Role]
  if (!info) return role
  return `${info.emoji} ${info.label}`
}

/**
 * Get role description
 */
export function getRoleDescription(role?: string): string {
  if (!role) return ''
  return ROLE_INFO[role as Role]?.description || ''
}

/**
 * Get role color class for Tailwind
 */
export function getRoleColor(role?: string): string {
  if (!role) return 'text-gray-600 dark:text-gray-400'
  return ROLE_INFO[role as Role]?.color || 'text-gray-600 dark:text-gray-400'
}
