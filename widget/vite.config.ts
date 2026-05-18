import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const AMY_BACKEND = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  define: {
    __AMY_BACKEND__: JSON.stringify(AMY_BACKEND),
  },
  build: {
    lib: {
      entry: 'src/main.tsx',
      name: 'AmyWidget',
      fileName: 'widget',
      formats: ['umd'],
    },
    rollupOptions: {
      // Bundle React so the widget is self-contained
      external: [],
    },
    cssCodeSplit: false,
    outDir: '../frontend/public',
  },
})
