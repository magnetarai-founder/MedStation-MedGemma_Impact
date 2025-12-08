/**
 * Setup Wizard API Client
 *
 * API client for first-run setup wizard endpoints.
 * No authentication required (setup happens before login).
 */

import axios, { AxiosInstance } from 'axios'

const BASE_URL = '/api/v1/setup'

class SetupWizardApi {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 60000, // 60 seconds (model downloads can be slow)
    })
  }

  // Setup Status
  async getSetupStatus() {
    const { data } = await this.client.get('/status')
    return data
  }

  // Ollama Detection
  async checkOllama() {
    const { data } = await this.client.get('/ollama')
    return data
  }

  // System Resources
  async getSystemResources() {
    const { data } = await this.client.get('/resources')
    return data
  }

  // Model Recommendations
  async getModelRecommendations(tier?: string) {
    const { data } = await this.client.get('/models/recommendations', {
      params: tier ? { tier } : undefined,
    })
    return data
  }

  async getInstalledModels() {
    const { data } = await this.client.get('/models/installed')
    return data
  }

  async downloadModel(modelName: string) {
    const { data } = await this.client.post('/models/download', {
      model_name: modelName,
    })
    return data
  }

  // Hot Slots
  async configureHotSlots(slots: { [key: number]: string | null }) {
    const { data } = await this.client.post('/hot-slots', { slots })
    return data
  }

  // Account Creation
  async createAccount(
    username: string,
    password: string,
    confirmPassword: string,
    founderPassword?: string
  ) {
    const { data } = await this.client.post('/account', {
      username,
      password,
      confirm_password: confirmPassword,
      founder_password: founderPassword || undefined,
    })
    return data
  }

  // Complete Setup
  async completeSetup() {
    const { data } = await this.client.post('/complete')
    return data
  }
}

// Export singleton instance
export const setupWizardApi = new SetupWizardApi()
