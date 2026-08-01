import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The wizard is served by setup/wizard.py from setup/ui/dist.
// base './' keeps asset URLs relative so it works on any IP or port.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    port: 3100,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
})
