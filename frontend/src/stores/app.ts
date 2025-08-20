import { defineStore } from 'pinia'

interface AppState {
  globalLoading: boolean
  sidebarCollapsed: boolean
  theme: 'light' | 'dark'
  language: string
  config: {
    apiBaseUrl: string
    version: string
    features: string[]
  }
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    globalLoading: false,
    sidebarCollapsed: false,
    theme: 'light',
    language: 'zh-cn',
    config: {
      apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
      version: '1.0.0',
      features: []
    }
  }),

  getters: {
    isDarkTheme: (state) => state.theme === 'dark',
    isLoading: (state) => state.globalLoading
  },

  actions: {
    // 设置全局加载状态
    setGlobalLoading(loading: boolean) {
      this.globalLoading = loading
    },

    // 切换侧边栏
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },

    // 设置主题
    setTheme(theme: 'light' | 'dark') {
      this.theme = theme
      localStorage.setItem('app-theme', theme)
      document.documentElement.setAttribute('data-theme', theme)
    },

    // 设置语言
    setLanguage(language: string) {
      this.language = language
      localStorage.setItem('app-language', language)
    },

    // 更新配置
    updateConfig(config: Partial<AppState['config']>) {
      this.config = { ...this.config, ...config }
    },

    // 初始化应用设置
    initializeApp() {
      // 从本地存储恢复设置
      const savedTheme = localStorage.getItem('app-theme') as 'light' | 'dark'
      if (savedTheme) {
        this.setTheme(savedTheme)
      }

      const savedLanguage = localStorage.getItem('app-language')
      if (savedLanguage) {
        this.setLanguage(savedLanguage)
      }

      // 检测系统主题偏好
      if (!savedTheme) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        this.setTheme(prefersDark ? 'dark' : 'light')
      }
    }
  }
})