import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  define: {
    global: 'globalThis',
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    emptyOutDir: false,
    outDir: 'dist',
    sourcemap: true,
    lib: {
      entry: path.resolve(__dirname, 'src/widget-bootstrap.ts'),
      name: 'ChatWidget',
      formats: ['iife'],
      fileName: () => 'widget.js',
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        banner: 'var process={env:{NODE_ENV:"production"}};',
      },
    },
  },
});
