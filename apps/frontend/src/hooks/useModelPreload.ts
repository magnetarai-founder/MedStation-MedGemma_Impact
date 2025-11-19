import { useEffect } from 'react'
import { api } from '@/lib/api'
import { useChatStore } from '@/stores/chatStore'
import { useSessionStore } from '@/stores/sessionStore'

/**
 * Hook to pre-load the default AI model after session creation.
 * Only runs if auto-preload is enabled in settings.
 */
export function useModelPreload() {
  const { settings } = useChatStore()
  const { sessionId } = useSessionStore()

  useEffect(() => {
    // Only preload if enabled in settings
    if (!settings.autoPreloadModel) {
      console.debug('Auto-preload disabled in settings')
      return
    }

    // Only preload if we have a valid session
    if (!sessionId) return
    if (!localStorage.getItem('auth_token')) return

    const preloadDefaultModel = async () => {
      try {
        console.log(`🔄 Auto-preloading default model: ${settings.defaultModel} (source: frontend_default)`)
        await api.preloadModel(settings.defaultModel, '1h', 'frontend_default')
        console.log(`✅ Model '${settings.defaultModel}' pre-loaded successfully (source: frontend_default)`)
      } catch (error: any) {
        // Non-critical - models load on first use anyway
        console.debug('⚠️ Model preload failed (non-critical):', error?.response?.status || error.message)
      }
    }

    // Delay to ensure Ollama server is ready
    const timeoutId = setTimeout(preloadDefaultModel, 3000)
    return () => clearTimeout(timeoutId)
  }, [sessionId, settings.defaultModel, settings.autoPreloadModel])
}
