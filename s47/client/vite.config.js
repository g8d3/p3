import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: {
      key: fs.readFileSync('/tmp/vibe-key.pem'),
      cert: fs.readFileSync('/tmp/vibe-cert.pem'),
    },
    proxy: {
      '/livekit': {
        target: 'ws://localhost:7880',
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/livekit/, ''),
      },
      '/token': {
        target: 'http://localhost:7882',
        changeOrigin: true,
      },
      '/log': {
        target: 'http://localhost:7882',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:7882',
        changeOrigin: true,
      },
    },
  },
});
