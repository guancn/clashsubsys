import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const TIMEOUT = 30000 // 30秒超时

// 创建 axios 实例
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // 添加时间戳防止缓存
    if (config.method === 'get') {
      config.params = {
        ...config.params,
        _t: Date.now()
      }
    }
    
    // 记录请求日志
    if (import.meta.env.DEV) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data || config.params)
    }
    
    return config
  },
  (error) => {
    console.error('请求配置错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // 记录响应日志
    if (import.meta.env.DEV) {
      console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data)
    }
    
    return response
  },
  (error) => {
    // 记录错误日志
    console.error('API 响应错误:', error)
    
    // 统一错误处理
    let message = '网络请求失败'
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          message = data?.message || '请求参数错误'
          break
        case 401:
          message = '未授权访问'
          break
        case 403:
          message = '禁止访问'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 429:
          message = '请求过于频繁，请稍后重试'
          break
        case 500:
          message = data?.message || '服务器内部错误'
          break
        case 502:
          message = '网关错误'
          break
        case 503:
          message = '服务暂时不可用'
          break
        default:
          message = data?.message || `请求失败 (${status})`
      }
    } else if (error.request) {
      if (error.code === 'ECONNABORTED') {
        message = '请求超时，请检查网络连接'
      } else if (error.code === 'NETWORK_ERROR') {
        message = '网络连接失败，请检查网络设置'
      } else {
        message = '网络请求失败，请检查服务器状态'
      }
    } else {
      message = error.message || '请求配置错误'
    }
    
    // 显示错误消息
    ElMessage.error(message)
    
    return Promise.reject(error)
  }
)

// 通用请求方法
export const request = {
  // GET 请求
  get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
    return api.get(url, { params, ...config }).then(res => res.data)
  },
  
  // POST 请求
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return api.post(url, data, config).then(res => res.data)
  },
  
  // PUT 请求
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return api.put(url, data, config).then(res => res.data)
  },
  
  // DELETE 请求
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return api.delete(url, config).then(res => res.data)
  },
  
  // 文件下载
  download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<Blob> {
    return api.get(url, {
      ...config,
      responseType: 'blob'
    }).then(response => {
      // 如果提供了文件名，自动下载
      if (filename) {
        const blob = response.data
        const downloadUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(downloadUrl)
      }
      return response.data
    })
  },
  
  // 文件上传
  upload<T = any>(url: string, file: File, config?: AxiosRequestConfig): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }).then(res => res.data)
  }
}

// 健康检查
export const healthCheck = () => request.get('/health')

// 获取服务信息
export const getServiceInfo = () => request.get('/info')

export default api