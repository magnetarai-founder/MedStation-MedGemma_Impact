import { useState, useEffect } from 'react'
import { X, Users, Copy, Check } from 'lucide-react'
import { useUserStore } from '../stores/userStore'
import { useTeamStore } from '../stores/teamStore'
import toast from 'react-hot-toast'

interface CreateTeamModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CreateTeamModal({ isOpen, onClose }: CreateTeamModalProps) {
  const { user, updateUser } = useUserStore()
  const { createTeam } = useTeamStore()
  const [teamName, setTeamName] = useState('')
  const [teamDescription, setTeamDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

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

  const handleCreate = async () => {
    if (!teamName.trim()) {
      toast.error('Team name is required')
      return
    }

    if (!user?.user_id) {
      toast.error('User not authenticated')
      return
    }

    setIsCreating(true)

    try {
      const response = await fetch('/api/v1/teams/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: teamName.trim(),
          description: teamDescription.trim() || null,
          creator_user_id: user.user_id
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create team')
      }

      const data = await response.json()

      // Update team store with new team
      createTeam({
        teamId: data.team_id,
        teamName: data.name,
        teamDescription: data.description
      })

      // Update user role to super_admin (local state only)
      // The role is tracked in team_members table on backend
      if (user) {
        useUserStore.setState({
          user: {
            ...user,
            role: 'super_admin',
            role_changed_at: new Date().toISOString(),
            role_changed_by: 'system'
          }
        })
      }

      // Show invite code
      setInviteCode(data.invite_code)

      toast.success(`Team "${data.name}" created successfully!`)
    } catch (error) {
      console.error('Failed to create team:', error)
      toast.error('Failed to create team. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleCopyInviteCode = () => {
    if (inviteCode) {
      navigator.clipboard.writeText(inviteCode)
      setCopied(true)
      toast.success('Invite code copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleClose = () => {
    setTeamName('')
    setTeamDescription('')
    setInviteCode(null)
    setCopied(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
              <Users className="text-primary-600 dark:text-primary-400" size={20} />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {inviteCode ? 'Team Created!' : 'Create New Team'}
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
          {!inviteCode ? (
            // Team Creation Form
            <>
              <div className="space-y-4">
                {/* Team Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Team Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    placeholder="e.g., Medical Mission Trip 2025"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    disabled={isCreating}
                    maxLength={100}
                  />
                </div>

                {/* Team Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    value={teamDescription}
                    onChange={(e) => setTeamDescription(e.target.value)}
                    placeholder="Brief description of your team's purpose..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                    disabled={isCreating}
                    maxLength={500}
                  />
                </div>

                {/* Info Card */}
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-900 dark:text-blue-200">
                    <strong>You will be promoted to Super Admin</strong> of this team. You'll be able to invite members, assign roles, and manage team settings.
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleClose}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={isCreating || !teamName.trim()}
                  className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                >
                  {isCreating ? 'Creating...' : 'Create Team'}
                </button>
              </div>
            </>
          ) : (
            // Invite Code Display
            <>
              <div className="space-y-4">
                {/* Success Message */}
                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <p className="text-sm text-green-900 dark:text-green-200">
                    Your team <strong>{teamName}</strong> has been created! You are now a <strong>Super Admin</strong>.
                  </p>
                </div>

                {/* Invite Code */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Share this invite code with team members
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inviteCode}
                      readOnly
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm"
                    />
                    <button
                      onClick={handleCopyInviteCode}
                      className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
                    >
                      {copied ? (
                        <>
                          <Check size={16} />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy size={16} />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    This code expires in 30 days. You can regenerate it anytime from team settings.
                  </p>
                </div>

                {/* What's Next */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    What's next?
                  </h3>
                  <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    <li>• Share the invite code with team members</li>
                    <li>• They can join using the "Join Team" button</li>
                    <li>• Approve join requests and assign roles</li>
                    <li>• Start collaborating in Team Workspace!</li>
                  </ul>
                </div>
              </div>

              {/* Close Button */}
              <div className="mt-6">
                <button
                  onClick={handleClose}
                  className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
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
