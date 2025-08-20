import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// 样式文件
import 'element-plus/dist/index.css'
import './styles/main.scss'

// 创建应用实例
const app = createApp(App)

// 注册插件
app.use(createPinia())
app.use(router)

// 挂载应用
app.mount('#app')

// 移除加载动画
const loadingElement = document.getElementById('loading')
if (loadingElement) {
  loadingElement.remove()
}

// 全局错误处理
app.config.errorHandler = (err, vm, info) => {
  console.error('全局错误:', err, info)
}

// 性能监控
if (import.meta.env.DEV) {
  console.log('🚀 Clash 订阅转换服务 - 开发模式')
}