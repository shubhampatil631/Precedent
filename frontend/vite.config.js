import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/handle-message': 'http://localhost:8000',
      '/eval-results': 'http://localhost:8000',
      '/taxonomy': 'http://localhost:8000'
    }
  }
})
