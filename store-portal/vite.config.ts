import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      // Dev-only: proxy API calls to the FastAPI backend while forcing the Host
      // header so backend host-policy checks still work.
      '/store': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('host', 'store-api.local')
          })
        },
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('host', 'store-api.local')
          })
        },
      },
    },
  },
})
