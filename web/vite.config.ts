import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// VITE_BASE is /ground-truth/ for GitHub Pages. Results load from public/data (written by `gt export`);
// only the live Ask page calls the API.
export default defineConfig({
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  server: { proxy: { '/api': `http://localhost:${process.env.API_PORT ?? 8000}` } },
})
