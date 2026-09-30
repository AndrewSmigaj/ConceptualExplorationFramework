import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// In development the Python server (`uv run python -m explorer serve`) owns /api;
// Vite serves the frontend and passes API calls through. In production the
// Python server serves the built dist/ itself, so there is one origin.
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
})
