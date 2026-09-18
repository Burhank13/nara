import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API is proxied so the browser sees one origin: the refresh cookie is SameSite=lax.
// Everything the API serves is under /api, so this list never needs touching again — and a page
// route like /overview reaches the SPA instead of being swallowed by the endpoint of that name.
const API_PATHS = ['/api', '/health']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Vite rejects requests arriving under a hostname it doesn't know. Allowing the tunnel
    // providers lets a real phone reach this dev server over HTTPS, which the clock-in demo
    // needs: browsers only hand out location on a secure origin.
    allowedHosts: ['.trycloudflare.com', '.ngrok-free.app', '.ngrok.app', '.loca.lt'],
    proxy: Object.fromEntries(
      API_PATHS.map((path) => [path, { target: 'http://localhost:8000', changeOrigin: true }]),
    ),
  },
})
