import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev: Vite on 5175, API proxied to uvicorn on 4700.
// Prod: FastAPI serves web/dist on 4700 directly.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:4700',
    },
  },
})
