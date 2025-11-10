import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Read backend port from environment (set by start_web.sh)
const backendPort = process.env.VITE_BACKEND_PORT || '8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 4200,
    strictPort: false, // Allow fallback ports if 4200 is in use
    hmr: {
      overlay: true,
    },
    watch: {
      usePolling: false,
    },
    headers: {
      'Cache-Control': 'no-store',
    },
    proxy: {
      '/api/v1/lan': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      '/api/v1/p2p': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://localhost:${backendPort}`,
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: true,
    // Chunk splitting strategy for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks - rarely change, cache effectively
          'react-vendor': ['react', 'react-dom', 'react/jsx-runtime'],
          'tanstack-vendor': ['@tanstack/react-query'],
          'ui-vendor': ['react-hot-toast', 'lucide-react'],

          // Heavy editor components - split by feature
          'editor-core': [
            './src/components/CodeEditor.tsx',
            './src/components/SQLEditor.tsx',
          ],

          // Chat components - lazy loaded but chunked together
          'chat-workspace': [
            './src/components/ChatSidebar.tsx',
            './src/components/ChatWindow.tsx',
          ],

          // Code workspace - lazy loaded but chunked together
          'code-workspace': [
            './src/components/CodeWorkspace.tsx',
            './src/components/CodeSidebar.tsx',
          ],

          // Team workspace - separate chunk
          'team-workspace': ['./src/components/TeamWorkspace.tsx'],

          // Settings modals - low priority, separate chunk
          'settings': [
            './src/components/SettingsModal.tsx',
            './src/components/CodeChatSettingsModal.tsx',
            './src/components/ServerControlModal.tsx',
          ],

          // Utility modals - separate chunk
          'modals': [
            './src/components/LibraryModal.tsx',
            './src/components/ProjectLibraryModal.tsx',
            './src/components/JsonConverterModal.tsx',
            './src/components/QueryHistoryModal.tsx',
          ],
        },
      },
    },
    // Chunk size warnings (500KB is reasonable for modern apps)
    chunkSizeWarningLimit: 500,
  },
  // Force cache busting in development
  cacheDir: '.vite',
})