import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [vue()],
  base: '/ascii/',
  server: {
    port: 5173,
    strictPort: true,
    fs: { allow: [fileURLToPath(new URL('../../../', import.meta.url))] },
    proxy: { '/api': 'http://127.0.0.1:8010' },
  },
})
