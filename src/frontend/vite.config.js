import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

function resolveBase(command) {
  if (command === 'serve') return '/'
  if (process.env.OKO_BUILD_TARGET === 'desktop') return '/'
  return '/static/'
}

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  base: resolveBase(command),
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/lucide-vue-next') || id.includes('node_modules/simple-icons')) {
            return 'vendor-icons'
          }
          if (id.includes('node_modules')) return 'vendor'
          return undefined
        },
      },
    },
  }
}))
