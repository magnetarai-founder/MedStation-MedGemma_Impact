import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

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
    strictPort: true,
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
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api/v1/p2p': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
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