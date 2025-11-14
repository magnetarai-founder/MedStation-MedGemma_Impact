/**
 * useProfileForm Hook
 *
 * Manages profile form state and handles saving
 */

import { useState, useEffect } from 'react'
import { useUserStore } from '@/stores/userStore'
import toast from 'react-hot-toast'
import type { UserProfile } from '../types'

export function useProfileForm(user: UserProfile | null) {
  const { updateUser } = useUserStore()

  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [deviceName, setDeviceName] = useState(user?.device_name || '')
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#3b82f6')
  const [bio, setBio] = useState(user?.bio || '')
  const [jobRole, setJobRole] = useState(user?.job_role || 'unassigned')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Update local state when user changes
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '')
      setDeviceName(user.device_name || '')
      setAvatarColor(user.avatar_color || '#3b82f6')
      setBio(user.bio || '')
      setJobRole(user.job_role || 'unassigned')
    }
  }, [user])

  const handleSave = async () => {
    try {
      await updateUser({
        display_name: displayName,
        device_name: deviceName,
        avatar_color: avatarColor,
        bio: bio,
        job_role: jobRole,
      })
      setHasUnsavedChanges(false)
      toast.success('Profile updated successfully')
    } catch (error) {
      toast.error('Failed to update profile')
      console.error('Profile update error:', error)
    }
  }

  // Wrapper functions that mark unsaved changes
  const handleDisplayNameChange = (value: string) => {
    setDisplayName(value)
    setHasUnsavedChanges(true)
  }

  const handleDeviceNameChange = (value: string) => {
    setDeviceName(value)
    setHasUnsavedChanges(true)
  }

  const handleAvatarColorChange = (value: string) => {
    setAvatarColor(value)
    setHasUnsavedChanges(true)
  }

  const handleBioChange = (value: string) => {
    setBio(value)
    setHasUnsavedChanges(true)
  }

  const handleJobRoleChange = (value: string) => {
    setJobRole(value)
    setHasUnsavedChanges(true)
  }

  return {
    formState: {
      displayName,
      deviceName,
      avatarColor,
      bio,
      jobRole,
      hasUnsavedChanges,
    },
    handlers: {
      setDisplayName: handleDisplayNameChange,
      setDeviceName: handleDeviceNameChange,
      setAvatarColor: handleAvatarColorChange,
      setBio: handleBioChange,
      setJobRole: handleJobRoleChange,
      handleSave,
    },
  }
}
