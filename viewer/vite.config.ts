import {defineConfig} from 'vite';

export default defineConfig({
  // Relative base so the built site works from any sub-path (GitHub Pages etc.)
  base: './',
  server: {
    // allow importing the committed tables in ../data/tables
    fs: {allow: ['..']}
  },
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 3000
  }
});
