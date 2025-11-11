/**
 * Team Store
 *
 * Manages team/network state for role activation:
 * - Solo Mode: No P2P/LAN = No roles active, full local access
 * - Guest Mode: Connected but not on team = Chat/Files only
 * - Team Mode: On a team = Roles activate based on assignment
 */

import { createWithEqualityFn } from 'zustand/traditional'
import { persist } from 'zustand/middleware'

export type NetworkMode = 'solo' | 'lan' | 'p2p'
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected'
export type TeamMembershipStatus = 'none' | 'pending' | 'member'

export interface TeamInfo {
  team_id: string
  team_name: string
  created_at: string
  created_by: string
  member_count: number
}

export interface TeamMember {
  user_id: string
  display_name: string
  role: string
  joined_at: string
  last_seen?: string
}

interface TeamStore {
  // Network state
  networkMode: NetworkMode
  connectionStatus: ConnectionStatus
  isHub: boolean
  connectedDevices: number

  // Team membership
  membershipStatus: TeamMembershipStatus
  currentTeam: TeamInfo | null
  teamMembers: TeamMember[]

  // Actions
  setNetworkMode: (mode: NetworkMode) => void
  setConnectionStatus: (status: ConnectionStatus) => void
  setIsHub: (isHub: boolean) => void
  setConnectedDevices: (count: number) => void
  setMembershipStatus: (status: TeamMembershipStatus) => void
  setCurrentTeam: (team: TeamInfo | null) => void
  setTeamMembers: (members: TeamMember[]) => void
  createTeam: (params: { teamId: string; teamName: string; teamDescription?: string | null }) => void

  // Computed
  isConnected: () => boolean
  isOnTeam: () => boolean
  shouldActivateRoles: () => boolean
}

export const useTeamStore = createWithEqualityFn<TeamStore>()(
  persist(
    (set, get) => ({
      // Initial state
      networkMode: 'solo',
      connectionStatus: 'disconnected',
      isHub: false,
      connectedDevices: 0,
      membershipStatus: 'none',
      currentTeam: null,
      teamMembers: [],

      // Actions
      setNetworkMode: (mode) => {
        set({ networkMode: mode })

        // Reset connection status when switching modes
        if (mode === 'solo') {
          set({
            connectionStatus: 'disconnected',
            isHub: false,
            connectedDevices: 0,
          })
        }
      },

      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setIsHub: (isHub) => set({ isHub }),
      setConnectedDevices: (count) => set({ connectedDevices: count }),
      setMembershipStatus: (status) => set({ membershipStatus: status }),
      setCurrentTeam: (team) => set({ currentTeam: team }),
      setTeamMembers: (members) => set({ teamMembers: members }),

      createTeam: ({ teamId, teamName, teamDescription }) => {
        // Create team and update membership
        set({
          currentTeam: {
            team_id: teamId,
            team_name: teamName,
            created_at: new Date().toISOString(),
            created_by: 'current_user',
            member_count: 1
          },
          membershipStatus: 'member'
        })
      },

      // Computed getters
      isConnected: () => {
        const { connectionStatus, networkMode } = get()
        return networkMode !== 'solo' && connectionStatus === 'connected'
      },

      isOnTeam: () => {
        const { membershipStatus } = get()
        return membershipStatus === 'member'
      },

      shouldActivateRoles: () => {
        const { isOnTeam, isConnected } = get()
        // Roles only activate when:
        // 1. Connected to network (LAN or P2P)
        // 2. Member of a team
        return isConnected() && isOnTeam()
      },
    }),
    {
      name: 'elohimos.team',
      // Persist team state
      partialize: (state) => ({
        networkMode: state.networkMode,
        membershipStatus: state.membershipStatus,
        currentTeam: state.currentTeam,
        teamMembers: state.teamMembers,
        // Don't persist connection state (ephemeral)
      }),
    }
  )
)
