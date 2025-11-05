/**
 * Main Entry Point
 *
 * This demonstrates Monaco's TypeScript syntax highlighting
 * Using patterns from Continue + Codex + Jarvis + Big Query
 */

import { CodeWorkspace } from './components/CodeWorkspace'
import { FileBrowser } from './components/FileBrowser'

interface AppConfig {
  workspace: string
  readOnly: boolean
  enableMonaco: boolean
}

class ElohimOSCodeTab {
  private config: AppConfig

  constructor(config: AppConfig) {
    this.config = config
  }

  async initialize(): Promise<void> {
    console.log('🚀 Initializing ElohimOS Code Tab...')
    console.log('📁 Workspace:', this.config.workspace)
    console.log('🔒 Read-only mode:', this.config.readOnly)

    // Phase 2: Read-only file browsing
    await this.loadFileTree()

    console.log('✅ Code Tab ready!')
  }

  private async loadFileTree(): Promise<void> {
    // Using Continue's walkDir patterns
    const files = await fetch('/api/v1/code/files?recursive=true')
    const tree = await files.json()

    console.log(`📊 Loaded ${tree.items.length} items`)
  }
}

// Bootstrap
const app = new ElohimOSCodeTab({
  workspace: '/Users/indiedevhipps/Documents/ElohimOS',
  readOnly: true, // Phase 2 limitation
  enableMonaco: true
})

app.initialize()
