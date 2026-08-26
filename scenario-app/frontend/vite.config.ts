import fs from 'node:fs'
import path from 'path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

function chatWidgetDevPlugin(): Plugin {
  return {
    name: 'serve-chat-widget-dist',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = req.url?.split('?')[0]
        if (pathname !== '/widget.js') {
          next()
          return
        }
        const widgetPath = path.resolve(__dirname, '../../chat-app/frontend/dist/widget.js')
        if (!fs.existsSync(widgetPath)) {
          res.statusCode = 404
          res.setHeader('Content-Type', 'text/plain; charset=utf-8')
          res.end(
            'Missing chat-app/frontend/dist/widget.js. From repo root run: cd chat-app/frontend && npm run build',
          )
          return
        }
        res.setHeader('Content-Type', 'application/javascript; charset=utf-8')
        fs.createReadStream(widgetPath).pipe(res)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), chatWidgetDevPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query'],
  },
})