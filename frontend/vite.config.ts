import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 简化配置，避免构建时的复杂依赖问题
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  // 从环境变量获取base路径，优先使用NODE_ENV中的设置
  const base = process.env.VITE_APP_PREFIX || env.VITE_APP_PREFIX || '/'
  
  console.log('Vite build config:', { 
    mode, 
    base, 
    VITE_APP_PREFIX: process.env.VITE_APP_PREFIX,
    VITE_API_BASE_URL: process.env.VITE_API_BASE_URL 
  })
  
  return {
    base,
    plugins: [
      vue()
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '~': resolve(__dirname, 'src')
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/styles/variables.scss" as *;`
        }
      }
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      open: true,
      cors: true
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      chunkSizeWarningLimit: 2000,
      rollupOptions: {
        external: [],
        output: {
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: 'assets/[ext]/[name]-[hash].[ext]'
        }
      }
    },
    define: {
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false
    }
  }
})