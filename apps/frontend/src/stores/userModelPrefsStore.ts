/**
 * User Model Preferences Store
 *
 * Zustand store for managing user model preferences and hot slots.
 * Provides optimistic UI updates and cache management.
 */

import { create } from 'zustand'
import { userModelsApi, ModelPreferenceItem, HotSlots, ModelCatalogItem } from '../lib/userModelsApi'

interface UserModelPrefsState {
  // Model catalog (global)
  catalog: ModelCatalogItem[]
  catalogLoading: boolean
  catalogError: string | null

  // User preferences
  preferences: ModelPreferenceItem[]
  preferencesLoading: boolean
  preferencesError: string | null

  // Hot slots
  hotSlots: HotSlots
  hotSlotsLoading: boolean
  hotSlotsError: string | null

  // Actions
  loadCatalog: () => Promise<void>
  loadPreferences: () => Promise<void>
  loadHotSlots: () => Promise<void>
  loadAll: () => Promise<void>

  updatePreferences: (preferences: ModelPreferenceItem[]) => Promise<void>
  updateHotSlots: (slots: HotSlots) => Promise<void>

  toggleModelVisibility: (modelName: string) => Promise<void>
  setModelPreferred: (modelName: string, preferred: boolean) => Promise<void>
  reorderModels: (preferences: ModelPreferenceItem[]) => Promise<void>

  assignHotSlot: (slotNumber: 1 | 2 | 3 | 4, modelName: string | null) => Promise<void>
  clearHotSlot: (slotNumber: 1 | 2 | 3 | 4) => Promise<void>

  // Computed
  getVisibleModels: () => ModelPreferenceItem[]
  getAssignedHotSlots: () => Array<{ slot: number; model: string }>
}

export const useUserModelPrefsStore = create<UserModelPrefsState>((set, get) => ({
  // Initial state
  catalog: [],
  catalogLoading: false,
  catalogError: null,

  preferences: [],
  preferencesLoading: false,
  preferencesError: null,

  hotSlots: { 1: null, 2: null, 3: null, 4: null },
  hotSlotsLoading: false,
  hotSlotsError: null,

  // Load model catalog
  loadCatalog: async () => {
    set({ catalogLoading: true, catalogError: null })

    try {
      const response = await userModelsApi.getModelCatalog()
      set({
        catalog: response.models,
        catalogLoading: false
      })
    } catch (error) {
      set({
        catalogError: error instanceof Error ? error.message : 'Failed to load catalog',
        catalogLoading: false
      })
    }
  },

  // Load user preferences
  loadPreferences: async () => {
    set({ preferencesLoading: true, preferencesError: null })

    try {
      const response = await userModelsApi.getModelPreferences()
      set({
        preferences: response.preferences,
        preferencesLoading: false
      })
    } catch (error) {
      set({
        preferencesError: error instanceof Error ? error.message : 'Failed to load preferences',
        preferencesLoading: false
      })
    }
  },

  // Load hot slots
  loadHotSlots: async () => {
    set({ hotSlotsLoading: true, hotSlotsError: null })

    try {
      const response = await userModelsApi.getHotSlots()
      set({
        hotSlots: response.slots,
        hotSlotsLoading: false
      })
    } catch (error) {
      set({
        hotSlotsError: error instanceof Error ? error.message : 'Failed to load hot slots',
        hotSlotsLoading: false
      })
    }
  },

  // Load all data
  loadAll: async () => {
    const { loadCatalog, loadPreferences, loadHotSlots } = get()
    await Promise.all([
      loadCatalog(),
      loadPreferences(),
      loadHotSlots()
    ])
  },

  // Update preferences (batch)
  updatePreferences: async (preferences: ModelPreferenceItem[]) => {
    // Optimistic update
    const previousPreferences = get().preferences
    set({ preferences })

    try {
      await userModelsApi.updateModelPreferences(preferences)
    } catch (error) {
      // Rollback on error
      set({ preferences: previousPreferences })
      throw error
    }
  },

  // Update hot slots (batch)
  updateHotSlots: async (slots: HotSlots) => {
    // Optimistic update
    const previousSlots = get().hotSlots
    set({ hotSlots: slots })

    try {
      await userModelsApi.updateHotSlots(slots)
    } catch (error) {
      // Rollback on error
      set({ hotSlots: previousSlots })
      throw error
    }
  },

  // Toggle model visibility
  toggleModelVisibility: async (modelName: string) => {
    const { preferences } = get()

    // Find existing preference
    const existingIndex = preferences.findIndex(p => p.model_name === modelName)

    let updatedPreferences: ModelPreferenceItem[]

    if (existingIndex >= 0) {
      // Toggle existing preference
      updatedPreferences = [...preferences]
      updatedPreferences[existingIndex] = {
        ...updatedPreferences[existingIndex],
        visible: !updatedPreferences[existingIndex].visible
      }
    } else {
      // Add new preference (visible by default, but we're toggling it off)
      updatedPreferences = [
        ...preferences,
        {
          model_name: modelName,
          visible: false, // Toggling from default true to false
          preferred: false
        }
      ]
    }

    await get().updatePreferences(updatedPreferences)
  },

  // Set model preferred flag
  setModelPreferred: async (modelName: string, preferred: boolean) => {
    const { preferences } = get()

    const existingIndex = preferences.findIndex(p => p.model_name === modelName)

    let updatedPreferences: ModelPreferenceItem[]

    if (existingIndex >= 0) {
      updatedPreferences = [...preferences]
      updatedPreferences[existingIndex] = {
        ...updatedPreferences[existingIndex],
        preferred
      }
    } else {
      // Add new preference with preferred flag
      updatedPreferences = [
        ...preferences,
        {
          model_name: modelName,
          visible: true,
          preferred
        }
      ]
    }

    await get().updatePreferences(updatedPreferences)
  },

  // Reorder models (update display_order)
  reorderModels: async (preferences: ModelPreferenceItem[]) => {
    // Assign display_order based on array position
    const updatedPreferences = preferences.map((pref, index) => ({
      ...pref,
      display_order: index + 1
    }))

    await get().updatePreferences(updatedPreferences)
  },

  // Assign hot slot
  assignHotSlot: async (slotNumber: 1 | 2 | 3 | 4, modelName: string | null) => {
    const { hotSlots } = get()

    const updatedSlots: HotSlots = {
      ...hotSlots,
      [slotNumber]: modelName
    }

    await get().updateHotSlots(updatedSlots)
  },

  // Clear hot slot
  clearHotSlot: async (slotNumber: 1 | 2 | 3 | 4) => {
    await get().assignHotSlot(slotNumber, null)
  },

  // Get visible models (computed)
  getVisibleModels: () => {
    const { preferences } = get()

    return preferences
      .filter(p => p.visible)
      .sort((a, b) => {
        // Sort by display_order, then by name
        if (a.display_order !== undefined && b.display_order !== undefined) {
          return a.display_order - b.display_order
        }
        if (a.display_order !== undefined) return -1
        if (b.display_order !== undefined) return 1
        return a.model_name.localeCompare(b.model_name)
      })
  },

  // Get assigned hot slots (computed)
  getAssignedHotSlots: () => {
    const { hotSlots } = get()

    return Object.entries(hotSlots)
      .filter(([_, model]) => model !== null)
      .map(([slot, model]) => ({
        slot: parseInt(slot),
        model: model as string
      }))
      .sort((a, b) => a.slot - b.slot)
  }
}))
