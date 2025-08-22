import { defineStore } from 'pinia'
import type { ConversionRequest, ConversionResponse } from '@/types/api'

interface ConverterState {
  // 转换表单数据
  form: ConversionRequest
  // 转换历史
  history: ConversionResponse[]
  // 当前转换结果
  currentResult: ConversionResponse | null
  // 转换状态
  converting: boolean
  // 预设配置
  presets: {
    name: string
    config: Partial<ConversionRequest>
    description: string
  }[]
}

export const useConverterStore = defineStore('converter', {
  state: (): ConverterState => ({
    form: {
      url: [''],
      target: 'clash',
      remote_config: '',
      include: '',
      exclude: '',
      filename: '',
      emoji: true,
      udp: true,
      tfo: false,
      scv: false,
      fdn: false,
      sort: false
    },
    history: [],
    currentResult: null,
    converting: false,
    presets: [
      {
        name: '默认配置',
        description: '适用于大多数用户的基础配置',
        config: {
          emoji: true,
          udp: true,
          tfo: false,
          scv: false
        }
      },
      {
        name: '全功能配置',
        description: '启用所有功能特性',
        config: {
          emoji: true,
          udp: true,
          tfo: true,
          scv: false,
          sort: true
        }
      },
      {
        name: '精简配置',
        description: '仅保留核心功能，适合低性能设备',
        config: {
          emoji: false,
          udp: false,
          tfo: false,
          scv: false,
          sort: false
        }
      },
      {
        name: '安全优先配置',
        description: '启用更严格的安全检查',
        config: {
          emoji: true,
          udp: true,
          tfo: false,
          scv: false,
          fdn: true,
          exclude: '(?i)free|trial|test|demo'
        }
      }
    ]
  }),

  getters: {
    // 获取有效的订阅 URL
    validUrls: (state) => state.form.url.filter(url => url.trim() !== ''),
    
    // 获取转换配置摘要
    configSummary: (state) => {
      const features = []
      if (state.form.emoji) features.push('Emoji')
      if (state.form.udp) features.push('UDP')
      if (state.form.tfo) features.push('TFO')
      if (state.form.scv) features.push('跳过证书验证')
      if (state.form.sort) features.push('节点排序')
      return features.join(', ') || '无额外功能'
    },

    // 获取最近的转换记录
    recentHistory: (state) => state.history.slice(-10).reverse(),

    // 检查是否有转换结果
    hasResult: (state) => state.currentResult !== null,

    // 检查转换是否成功
    isConversionSuccess: (state) => state.currentResult?.success === true
  },

  actions: {
    // 更新表单数据
    updateForm(data: Partial<ConversionRequest>) {
      this.form = { ...this.form, ...data }
    },

    // 添加订阅 URL
    addUrl() {
      this.form.url.push('')
    },

    // 删除订阅 URL
    removeUrl(index: number) {
      if (this.form.url.length > 1) {
        this.form.url.splice(index, 1)
      }
    },

    // 应用预设配置
    applyPreset(presetIndex: number) {
      const preset = this.presets[presetIndex]
      if (preset) {
        this.updateForm(preset.config)
      }
    },


    // 设置转换状态
    setConverting(status: boolean) {
      this.converting = status
    },

    // 设置转换结果
    setResult(result: ConversionResponse) {
      this.currentResult = result
      
      // 添加到历史记录
      if (result.success) {
        this.addToHistory(result)
      }
    },

    // 添加到历史记录
    addToHistory(result: ConversionResponse) {
      const historyItem = {
        ...result,
        timestamp: new Date().toISOString(),
        form_snapshot: JSON.parse(JSON.stringify(this.form))
      }
      
      this.history.unshift(historyItem as ConversionResponse)
      
      // 限制历史记录数量
      if (this.history.length > 50) {
        this.history = this.history.slice(0, 50)
      }
      
      // 保存到本地存储
      this.saveHistoryToLocal()
    },

    // 清空历史记录
    clearHistory() {
      this.history = []
      localStorage.removeItem('conversion-history')
    },

    // 从历史记录恢复配置
    restoreFromHistory(index: number) {
      const historyItem = this.history[index]
      if (historyItem && (historyItem as any).form_snapshot) {
        this.form = (historyItem as any).form_snapshot
      }
    },

    // 重置表单
    resetForm() {
      this.form = {
        url: [''],
        target: 'clash',
        remote_config: '',
        include: '',
        exclude: '',
        filename: '',
        emoji: true,
        udp: true,
        tfo: false,
        scv: false,
        fdn: false,
        sort: false
      }
    },

    // 验证表单
    validateForm(): { valid: boolean; errors: string[] } {
      const errors: string[] = []
      
      // 检查订阅 URL
      const validUrls = this.validUrls
      if (validUrls.length === 0) {
        errors.push('请至少输入一个有效的订阅链接')
      }
      
      // 验证 URL 格式
      const urlPattern = /^https?:\/\/.+/
      for (const url of validUrls) {
        if (!urlPattern.test(url)) {
          errors.push(`无效的订阅链接: ${url}`)
        }
      }
      
      // 验证远程配置 URL（如果提供）
      if (this.form.remote_config && !urlPattern.test(this.form.remote_config)) {
        errors.push('无效的远程配置链接')
      }
      
      return {
        valid: errors.length === 0,
        errors
      }
    },

    // 保存历史记录到本地存储
    saveHistoryToLocal() {
      try {
        localStorage.setItem('conversion-history', JSON.stringify(this.history))
      } catch (error) {
        console.warn('无法保存历史记录到本地存储:', error)
      }
    },

    // 从本地存储加载历史记录
    loadHistoryFromLocal() {
      try {
        const saved = localStorage.getItem('conversion-history')
        if (saved) {
          this.history = JSON.parse(saved)
        }
      } catch (error) {
        console.warn('无法从本地存储加载历史记录:', error)
      }
    },

    // 导出配置
    exportConfig() {
      const config = {
        form: this.form,
        timestamp: new Date().toISOString(),
        version: '1.0.0'
      }
      
      const blob = new Blob([JSON.stringify(config, null, 2)], {
        type: 'application/json'
      })
      
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `clash-converter-config-${Date.now()}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },

    // 导入配置
    importConfig(file: File): Promise<boolean> {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const config = JSON.parse(e.target?.result as string)
            if (config.form) {
              this.form = { ...this.form, ...config.form }
              resolve(true)
            } else {
              reject(new Error('无效的配置文件格式'))
            }
          } catch (error) {
            reject(error)
          }
        }
        
        reader.onerror = () => reject(new Error('文件读取失败'))
        reader.readAsText(file)
      })
    }
  }
})