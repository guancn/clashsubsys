/**
 * API 类型定义
 */

// 目标格式枚举
export type TargetFormat = 'clash' | 'surge' | 'quantumult-x' | 'loon' | 'surfboard'

// 转换请求
export interface ConversionRequest {
  url: string[]
  target: TargetFormat
  remote_config?: string
  custom_rules?: string[]
  include?: string
  exclude?: string
  rename?: string
  emoji: boolean
  udp: boolean
  tfo: boolean
  scv: boolean
  fdn: boolean
  sort: boolean
}

// 转换响应
export interface ConversionResponse {
  success: boolean
  message: string
  config?: string
  download_url?: string
  nodes_count: number
}

// 健康检查响应
export interface HealthResponse {
  status: string
  version: string
  timestamp: string
}

// 错误响应
export interface ErrorResponse {
  success: boolean
  error_code: string
  message: string
  detail?: string
}

// 配置信息
export interface ConfigInfo {
  config_id: string
  nodes_count: number
  created_at: string
  download_url: string
}

// 验证结果
export interface ValidationResult {
  url: string
  valid: boolean
  status_code?: number
  content_type?: string
  content_length?: string
  error?: string
}

// 支持的功能特性
export interface SupportedFeatures {
  supported_protocols: string[]
  supported_networks: string[]
  supported_features: string[]
  proxy_group_types: string[]
}

// 服务信息
export interface ServiceInfo {
  service: {
    name: string
    version: string
    description: string
    author: string
    license: string
  }
  api: {
    base_url: string
    docs_url: string
    redoc_url: string
    openapi_url: string
  }
  features: {
    supported_protocols: string[]
    supported_formats: string[]
    node_filters: boolean
    custom_rules: boolean
    remote_config: boolean
    emoji_support: boolean
  }
  limits: {
    max_subscription_size: string
    max_nodes_per_subscription: number
    cache_ttl: string
    request_timeout: string
  }
  status: {
    uptime: string
    timezone: string
    environment: string
  }
}

// 代理节点
export interface ProxyNode {
  name: string
  type: string
  server: string
  port: number
  cipher?: string
  password?: string
  uuid?: string
  alterId?: number
  network?: string
  tls?: boolean
  sni?: string
  host?: string
  path?: string
  protocol?: string
  obfs?: string
  obfs_param?: string
  protocol_param?: string
  auth_str?: string
  up?: string
  down?: string
  udp?: boolean
  skip_cert_verify?: boolean
}

// 代理组
export interface ProxyGroup {
  name: string
  type: string
  proxies: string[]
  url?: string
  interval?: number
  tolerance?: number
  lazy?: boolean
  disable_udp?: boolean
  filter?: string
  exclude_filter?: string
}

// 统计信息
export interface CacheStats {
  cached_configs: number
  total_memory_mb: number
}

// 转换历史项
export interface ConversionHistoryItem extends ConversionResponse {
  timestamp: string
  form_snapshot?: ConversionRequest
}

// 预设配置
export interface PresetConfig {
  name: string
  description: string
  config: Partial<ConversionRequest>
}

// 订阅信息
export interface SubscriptionInfo {
  url: string
  name?: string
  nodes_count?: number
  update_time?: string
  expire_time?: string
  upload?: number
  download?: number
  total?: number
}

// 节点统计
export interface NodeStats {
  total: number
  by_type: Record<string, number>
  by_country: Record<string, number>
  by_region: Record<string, number>
}

// 转换配置
export interface ConversionConfig {
  // 基础设置
  target_format: TargetFormat
  enable_emoji: boolean
  enable_udp: boolean
  enable_tfo: boolean
  skip_cert_verify: boolean
  filter_non_default_port: boolean
  sort_nodes: boolean
  
  // 过滤设置
  include_pattern?: string
  exclude_pattern?: string
  rename_pattern?: string
  
  // 规则设置
  remote_config_url?: string
  custom_rules: string[]
  
  // 高级设置
  timeout: number
  user_agent: string
  max_nodes: number
}

// API 响应包装器
export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
  success: boolean
  timestamp: string
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 文件信息
export interface FileInfo {
  name: string
  size: number
  type: string
  last_modified: string
}

// 导出类型
export type {
  // 请求/响应类型
  ConversionRequest as ConvertRequest,
  ConversionResponse as ConvertResponse,
  
  // 配置相关类型
  ConversionConfig as Config,
  PresetConfig as Preset,
  
  // 节点相关类型
  ProxyNode as Node,
  ProxyGroup as Group,
  NodeStats as Stats
}