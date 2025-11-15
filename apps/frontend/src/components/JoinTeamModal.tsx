import { useState, useEffect } from 'react'
import { X, Users, Check } from 'lucide-react'
import { useUserStore } from '../stores/userStore'
import { useTeamStore } from '../stores/teamStore'
import toast from 'react-hot-toast'

interface JoinTeamModalProps {
  isOpen: boolean
  onClose: () => void
}

export function JoinTeamModal({ isOpen, onClose }: JoinTeamModalProps) {
  const { user } = useUserStore()
  const { setCurrentTeam, setMembershipStatus } = useTeamStore()
  const [inviteCode, setInviteCode] = useState('')
  const [isJoining, setIsJoining] = useState(false)
  const [joinedTeam, setJoinedTeam] = useState<{ name: string; teamId: string } | null>(null)

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [])

  if (!isOpen) return null

  const handleJoin = async () => {
    if (!inviteCode.trim()) {
      toast.error('Invite code is required')
      return
    }

    if (!user?.user_id) {
      toast.error('User not authenticated')
      return
    }

    setIsJoining(true)

    try {
      const response = await fetch('/api/v1/teams/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invite_code: inviteCode.trim(),
          user_id: user.user_id
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to join team')
      }

      const data = await response.json()

      // Update team store
      setCurrentTeam({
        team_id: data.team_id,
        team_name: data.team_name,
        created_at: new Date().toISOString(),
        created_by: 'unknown',
        member_count: 1
      })

      setMembershipStatus('member')

      // Update user role to member (local state only)
      if (user) {
        useUserStore.setState({
          user: {
            ...user,
            role: data.user_role,
            role_changed_at: new Date().toISOString(),
            role_changed_by: 'system'
          }
        })
      }

      // Show success
      setJoinedTeam({ name: data.team_name, teamId: data.team_id })
      toast.success(`Joined team "${data.team_name}" successfully!`)
    } catch (error: any) {
      console.error('Failed to join team:', error)
      toast.error(error.message || 'Failed to join team. Please check the invite code.')
    } finally {
      setIsJoining(false)
    }
  }

  const handleClose = () => {
    setInviteCode('')
    setJoinedTeam(null)
    onClose()
  }

  const formatInviteCode = (value: string) => {
    // Remove all non-alphanumeric characters
    const clean = value.replace(/[^A-Z0-9]/gi, '').toUpperCase()

    // Format as XXXXX-XXXXX-XXXXX
    const parts = []
    for (let i = 0; i < clean.length; i += 5) {
      parts.push(clean.slice(i, i + 5))
    }

    return parts.join('-').slice(0, 17) // Max length: XXXXX-XXXXX-XXXXX
  }

  const handleInviteCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatInviteCode(e.target.value)
    setInviteCode(formatted)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <Users className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {joinedTeam ? 'Success!' : 'Join Team'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <X size={20} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!joinedTeam ? (
            // Join Team Form
            <>
              <div className="space-y-4">
                {/* Invite Code Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Enter Invite Code <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={inviteCode}
                    onChange={handleInviteCodeChange}
                    placeholder="XXXXX-XXXXX-XXXXX"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-center text-lg tracking-wider"
                    disabled={isJoining}
                    maxLength={17}
                  />
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    Enter the 15-character invite code shared by your team admin
                  </p>
                </div>

                {/* Info Card */}
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-900 dark:text-blue-200">
                    <strong>You will join as a Member.</strong> Once you join, you'll have access to team documents, chat, and workflow features.
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  disabled={isJoining}
                >
                  Cancel
                </button>
                <button
                  onClick={handleJoin}
                  disabled={isJoining || inviteCode.length < 17}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {isJoining ? 'Joining...' : 'Join Team'}
                </button>
              </div>
            </>
          ) : (
            // Success Screen
            <>
              <div className="space-y-4">
                {/* Success Message */}
                <div className="flex items-center justify-center py-8">
                  <div className="flex flex-col items-center gap-4">
                    <div className="p-4 bg-green-100 dark:bg-green-900/30 rounded-full">
                      <Check className="text-green-600 dark:text-green-400" size={48} />
                    </div>
                    <div className="text-center">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        Welcome to {joinedTeam.name}!
                      </h3>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        You've successfully joined the team as a Member
                      </p>
                    </div>
                  </div>
                </div>

                {/* What's Next */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    What's next?
                  </h3>
                  <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    <li>• Access team documents and workflows</li>
                    <li>• Collaborate in team chat</li>
                    <li>• View shared vault items (from now forward)</li>
                    <li>• Contact an admin for role upgrades</li>
                  </ul>
                </div>
              </div>

              {/* Close Button */}
              <div className="mt-6">
                <button
                  onClick={handleClose}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  Done
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
