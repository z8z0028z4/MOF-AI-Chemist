import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const frontendPort = Number(process.env.MOF_FRONTEND_PORT || 3000)
const backendPort = Number(process.env.MOF_BACKEND_PORT || 8000)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: frontendPort,
    host: '127.0.0.1', // 僅允許本機訪問
    proxy: {
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  optimizeDeps: {
    include: ['axios', 'antd', 'react', 'react-dom'],
  },
})
