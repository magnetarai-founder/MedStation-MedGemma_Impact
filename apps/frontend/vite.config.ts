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
  },
  // Force cache busting in development
  cacheDir: '.vite',
})