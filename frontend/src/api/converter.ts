import { request } from './index'
import type { 
  ConversionRequest, 
  ConversionResponse, 
  ValidationResult,
  ConfigInfo,
  SupportedFeatures 
} from '@/types/api'

/**
 * 订阅转换 API
 */
export const converterApi = {
  /**
   * 转换订阅（POST 方式）
   */
  convert(data: ConversionRequest): Promise<ConversionResponse> {
    return request.post<ConversionResponse>('/convert', data)
  },

  /**
   * 转换订阅（GET 方式，兼容 subconverter API）
   */
  convertGet(params: {
    url: string
    target?: string
    remote_config?: string
    include?: string
    exclude?: string
    rename?: string
    emoji?: boolean
    udp?: boolean
    tfo?: boolean
    scv?: boolean
    fdn?: boolean
    sort?: boolean
  }): Promise<ConversionResponse> {
    return request.get<ConversionResponse>('/convert', params)
  },

  /**
   * 下载转换后的配置文件
   */
  downloadConfig(configId: string, format?: 'yaml' | 'json', filename?: string): Promise<Blob> {
    const params: any = {}
    if (format) params.format = format
    if (filename) params.filename = filename
    
    return request.download(`/sub/${configId}`, filename, { params })
  },

  /**
   * 获取配置文件内容（文本格式）
   */
  getConfig(configId: string, format?: 'yaml' | 'json'): Promise<string> {
    const params: any = {}
    if (format) params.format = format
    
    return request.get(`/sub/${configId}`, params, {
      headers: { 'Accept': 'text/plain' }
    })
  },

  /**
   * 获取配置信息
   */
  getConfigInfo(configId: string): Promise<ConfigInfo> {
    return request.get<ConfigInfo>(`/sub/${configId}/info`)
  },

  /**
   * 验证订阅链接
   */
  validateUrls(urls: string[]): Promise<{ results: ValidationResult[] }> {
    return request.post<{ results: ValidationResult[] }>('/validate', urls)
  },

  /**
   * 获取支持的功能特性
   */
  getFeatures(): Promise<SupportedFeatures> {
    return request.get<SupportedFeatures>('/features')
  },

  /**
   * 获取支持的协议列表
   */
  getProtocols(): Promise<{
    protocols: string[]
    networks: string[]
    proxy_groups: string[]
  }> {
    return request.get('/protocols')
  },

  /**
   * 删除缓存的配置
   */
  deleteConfig(configId: string): Promise<{ message: string }> {
    return request.delete<{ message: string }>(`/cache/${configId}`)
  },

  /**
   * 获取缓存统计信息
   */
  getCacheStats(): Promise<{
    cached_configs: number
    total_memory_mb: number
  }> {
    return request.get('/cache/stats')
  },

  /**
   * 清空所有缓存
   */
  clearCache(): Promise<{ message: string }> {
    return request.post<{ message: string }>('/cache/clear')
  }
}

/**
 * 构建订阅链接
 */
export const buildSubscriptionUrl = (
  baseUrl: string,
  params: {
    url: string | string[]
    target?: string
    remote_config?: string
    include?: string
    exclude?: string
    rename?: string
    emoji?: boolean
    udp?: boolean
    tfo?: boolean
    scv?: boolean
    fdn?: boolean
    sort?: boolean
  }
): string => {
  const searchParams = new URLSearchParams()
  
  // 处理订阅 URL
  if (Array.isArray(params.url)) {
    searchParams.set('url', params.url.join('|'))
  } else {
    searchParams.set('url', params.url)
  }
  
  // 添加其他参数
  Object.entries(params).forEach(([key, value]) => {
    if (key !== 'url' && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  
  return `${baseUrl}/api/convert?${searchParams.toString()}`
}

/**
 * 复制订阅链接到剪贴板
 */
export const copySubscriptionUrl = async (url: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(url)
    } else {
      // 降级方案
      const textArea = document.createElement('textarea')
      textArea.value = url
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
      document.body.prepend(textArea)
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    return true
  } catch (error) {
    console.error('复制到剪贴板失败:', error)
    return false
  }
}

/**
 * 验证 URL 格式
 */
export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url)
    return /^https?:\/\/.+/.test(url)
  } catch {
    return false
  }
}

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化节点数量
 */
export const formatNodeCount = (count: number): string => {
  if (count === 0) return '无节点'
  if (count === 1) return '1 个节点'
  return `${count} 个节点`
}

/**
 * 生成配置文件名
 */
export const generateConfigFilename = (
  prefix: string = 'clash_config',
  format: string = 'yaml'
): string => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  return `${prefix}_${timestamp}.${format}`
}