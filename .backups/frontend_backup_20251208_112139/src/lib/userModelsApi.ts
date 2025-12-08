/**
 * User Models API Client
 *
 * TypeScript client for per-user model preferences and hot slots endpoints.
 *
 * Endpoints:
 * - GET /api/v1/users/me/models/preferences - Get user model visibility
 * - PUT /api/v1/users/me/models/preferences - Update model visibility
 * - GET /api/v1/users/me/models/hot-slots - Get user hot slots
 * - PUT /api/v1/users/me/models/hot-slots - Update hot slots
 * - GET /api/v1/models/catalog - Get global model catalog
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ===== Type Definitions =====

export interface ModelCatalogItem {
  model_name: string
  size?: string
  status: 'installed' | 'downloading' | 'failed' | 'unknown'
  installed_at?: string
  last_seen?: string
}

export interface ModelCatalogResponse {
  models: ModelCatalogItem[]
  total_count: number
}

export interface ModelPreferenceItem {
  model_name: string
  visible: boolean
  preferred?: boolean
  display_order?: number
}

export interface ModelPreferencesResponse {
  preferences: ModelPreferenceItem[]
}

export interface UpdateModelPreferencesRequest {
  preferences: ModelPreferenceItem[]
}

export interface UpdateModelPreferencesResponse {
  success: boolean
  updated_count: number
}

export interface HotSlots {
  1: string | null
  2: string | null
  3: string | null
  4: string | null
}

export interface HotSlotsResponse {
  slots: HotSlots
}

export interface UpdateHotSlotsRequest {
  slots: HotSlots
}

export interface UpdateHotSlotsResponse {
  success: boolean
  message: string
}

// ===== API Client =====

class UserModelsApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  /**
   * Get authentication token from localStorage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token')
  }

  /**
   * Get default headers with authentication
   */
  private getHeaders(): HeadersInit {
    const token = this.getAuthToken()
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  /**
   * Get global model catalog
   *
   * Returns list of all models installed on the system.
   * Public endpoint - no authentication required.
   */
  async getModelCatalog(): Promise<ModelCatalogResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/models/catalog`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch model catalog: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get user's model preferences
   *
   * Returns list of models with visibility and display order settings.
   * Requires authentication.
   */
  async getModelPreferences(): Promise<ModelPreferencesResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/users/me/models/preferences`, {
      method: 'GET',
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch model preferences: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Update user's model preferences
   *
   * Sets which models the user wants to see and their display order.
   * Requires authentication.
   */
  async updateModelPreferences(
    preferences: ModelPreferenceItem[]
  ): Promise<UpdateModelPreferencesResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/users/me/models/preferences`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify({ preferences })
    })

    if (!response.ok) {
      throw new Error(`Failed to update model preferences: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get user's hot slots configuration
   *
   * Returns mapping of slot numbers (1-4) to model names.
   * Requires authentication.
   */
  async getHotSlots(): Promise<HotSlotsResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/users/me/models/hot-slots`, {
      method: 'GET',
      headers: this.getHeaders()
    })

    if (!response.ok) {
      throw new Error(`Failed to fetch hot slots: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Update user's hot slots configuration
   *
   * Assigns models to quick-access slots (1-4).
   * Requires authentication.
   */
  async updateHotSlots(slots: HotSlots): Promise<UpdateHotSlotsResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/users/me/models/hot-slots`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify({ slots })
    })

    if (!response.ok) {
      throw new Error(`Failed to update hot slots: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get list of visible model names for current user
   *
   * Convenience method that fetches preferences and filters to visible models.
   * Returns model names in display order.
   */
  async getVisibleModelNames(): Promise<string[]> {
    const { preferences } = await this.getModelPreferences()

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
      .map(p => p.model_name)
  }

  /**
   * Initialize default preferences for a new user
   *
   * Sets all installed models as visible by default.
   * Should be called during user setup wizard.
   */
  async initializeDefaultPreferences(): Promise<UpdateModelPreferencesResponse> {
    // Get all installed models from catalog
    const { models } = await this.getModelCatalog()

    // Create preferences with all models visible
    const preferences: ModelPreferenceItem[] = models.map((model, index) => ({
      model_name: model.model_name,
      visible: true,
      preferred: false,
      display_order: index + 1
    }))

    // Save preferences
    return this.updateModelPreferences(preferences)
  }

  /**
   * Clear a specific hot slot
   *
   * Convenience method to clear a single slot.
   */
  async clearHotSlot(slotNumber: 1 | 2 | 3 | 4): Promise<UpdateHotSlotsResponse> {
    // Get current slots
    const { slots } = await this.getHotSlots()

    // Clear the specified slot
    const updatedSlots: HotSlots = {
      ...slots,
      [slotNumber]: null
    }

    // Update
    return this.updateHotSlots(updatedSlots)
  }
}

// Export singleton instance
export const userModelsApi = new UserModelsApiClient()

// Export class for testing/custom instances
export { UserModelsApiClient }
