import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      // Dev-only: proxy API calls to the FastAPI backend while forcing the Host
      // header so backend host-policy checks still work.
      '/store': {
        target: apiTarget,
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('host', 'store-api.local')
          })
        },
      },
      '/health': {
        target: apiTarget,
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('host', 'store-api.local')
          })
        },
      },
      '/uploads': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
