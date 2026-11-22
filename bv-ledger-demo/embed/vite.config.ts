import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

const here = (p: string) => fileURLToPath(new URL(p, import.meta.url))

// One IIFE script and one stylesheet for inlining into the guide's HTML.
// The playground's local font files are swapped for an empty stylesheet:
// the guide carries its own Pretendard.
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'drop-local-fonts',
      enforce: 'pre',
      resolveId(source) {
        if (source.endsWith('/fonts.css') || source === './fonts.css') return here('./empty.css')
        return null
      },
    },
  ],
  define: { 'process.env.NODE_ENV': '"production"' },
  build: {
    outDir: here('./dist'),
    emptyOutDir: true,
    cssCodeSplit: false,
    lib: { entry: here('./main.tsx'), formats: ['iife'], name: 'BvExpense', fileName: () => 'bv-expense.js' },
    rollupOptions: { output: { assetFileNames: 'bv-expense[extname]' } },
  },
})
