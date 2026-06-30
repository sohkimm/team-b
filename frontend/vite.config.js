import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api 요청은 FastAPI 백엔드(:8000)로 프록시 → CORS 신경 안 써도 됨.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
