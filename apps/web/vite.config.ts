import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_TEST_SERVER === '1' ? '/' : '/auth-assets/',
  build: { outDir: 'dist', emptyOutDir: true },
  test: { environment: 'jsdom', globals: true, setupFiles: './src/__tests__/setup.ts', exclude: ['e2e/**','node_modules/**','dist/**'] }
})
