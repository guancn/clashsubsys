"""
数据模型定义
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, HttpUrl, Field, validator
from enum import Enum


class ProxyType(str, Enum):
    """代理类型枚举"""
    SS = "ss"
    SSR = "ssr"
    VMESS = "vmess"
    VLESS = "vless"
    TROJAN = "trojan"
    HYSTERIA = "hysteria"
    HYSTERIA2 = "hysteria2"
    TUIC = "tuic"
    WIREGUARD = "wireguard"


class TargetFormat(str, Enum):
    """目标格式枚举"""
    CLASH = "clash"
    SURGE = "surge"
    QUANTUMULT_X = "quantumult-x"
    LOON = "loon"
    SURFBOARD = "surfboard"


class ConversionRequest(BaseModel):
    """转换请求模型"""
    url: Union[str, List[str]] = Field(..., description="订阅链接，支持单个或多个")
    target: TargetFormat = Field(default=TargetFormat.CLASH, description="目标格式")
    remote_config: Optional[HttpUrl] = Field(None, description="远程配置规则地址")
    custom_rules: Optional[List[str]] = Field(None, description="自定义规则列表")
    include: Optional[str] = Field(None, description="节点包含过滤规则（正则）")
    exclude: Optional[str] = Field(None, description="节点排除过滤规则（正则）")
    rename: Optional[str] = Field(None, description="节点重命名规则")
    emoji: bool = Field(default=True, description="是否添加 Emoji")
    udp: bool = Field(default=True, description="是否启用 UDP")
    tfo: bool = Field(default=False, description="是否启用 TCP Fast Open")
    scv: bool = Field(default=False, description="是否跳过证书验证")
    fdn: bool = Field(default=False, description="是否过滤非默认端口")
    sort: bool = Field(default=False, description="是否按节点名排序")

    @validator('url', pre=True)
    def validate_url(cls, v):
        """验证 URL 格式"""
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            if not v:
                raise ValueError("URL list cannot be empty")
            return v
        else:
            raise ValueError("URL must be string or list of strings")


class ProxyNode(BaseModel):
    """代理节点模型"""
    name: str = Field(..., description="节点名称")
    type: ProxyType = Field(..., description="代理类型")
    server: str = Field(..., description="服务器地址")
    port: int = Field(..., description="端口号")
    cipher: Optional[str] = Field(None, description="加密方式")
    password: Optional[str] = Field(None, description="密码")
    uuid: Optional[str] = Field(None, description="UUID")
    alterId: Optional[int] = Field(None, description="alterID")
    network: Optional[str] = Field(None, description="传输协议")
    tls: Optional[bool] = Field(None, description="是否启用 TLS")
    sni: Optional[str] = Field(None, description="SNI")
    host: Optional[str] = Field(None, description="Host")
    path: Optional[str] = Field(None, description="路径")
    
    # 其他协议特定字段
    protocol: Optional[str] = Field(None, description="协议（SSR）")
    obfs: Optional[str] = Field(None, description="混淆（SSR/SS）")
    obfs_param: Optional[str] = Field(None, description="混淆参数")
    protocol_param: Optional[str] = Field(None, description="协议参数")
    
    # Hysteria 相关
    auth_str: Optional[str] = Field(None, description="认证字符串")
    up: Optional[str] = Field(None, description="上传速度")
    down: Optional[str] = Field(None, description="下载速度")
    
    # 通用配置
    udp: Optional[bool] = Field(True, description="是否支持 UDP")
    skip_cert_verify: Optional[bool] = Field(False, description="是否跳过证书验证")


class ProxyGroup(BaseModel):
    """代理组模型"""
    name: str = Field(..., description="代理组名称")
    type: str = Field(..., description="代理组类型")
    proxies: List[str] = Field(..., description="代理节点列表")
    url: Optional[str] = Field(None, description="测试 URL")
    interval: Optional[int] = Field(None, description="测试间隔")
    tolerance: Optional[int] = Field(None, description="容差")
    lazy: Optional[bool] = Field(None, description="是否懒加载")
    disable_udp: Optional[bool] = Field(None, description="是否禁用 UDP")
    filter: Optional[str] = Field(None, description="节点过滤规则")
    exclude_filter: Optional[str] = Field(None, description="节点排除规则")


class Rule(BaseModel):
    """规则模型"""
    type: str = Field(..., description="规则类型")
    payload: str = Field(..., description="规则内容")
    proxy: str = Field(..., description="策略")
    params: Optional[Dict[str, Any]] = Field(None, description="额外参数")


class ClashConfig(BaseModel):
    """Clash 配置模型"""
    port: int = Field(7890, description="HTTP 代理端口")
    socks_port: int = Field(7891, description="SOCKS5 代理端口")
    mixed_port: Optional[int] = Field(None, description="混合端口")
    redir_port: Optional[int] = Field(None, description="透明代理端口")
    tproxy_port: Optional[int] = Field(None, description="TProxy 端口")
    
    allow_lan: bool = Field(False, description="是否允许局域网连接")
    bind_address: str = Field("*", description="绑定地址")
    mode: str = Field("rule", description="模式")
    log_level: str = Field("info", description="日志级别")
    external_controller: str = Field("127.0.0.1:9090", description="外部控制器")
    secret: Optional[str] = Field(None, description="API 密钥")
    
    dns: Optional[Dict[str, Any]] = Field(None, description="DNS 配置")
    proxies: List[ProxyNode] = Field(..., description="代理节点列表")
    proxy_groups: List[ProxyGroup] = Field(..., description="代理组列表")
    rules: List[str] = Field(..., description="规则列表")


class ConversionResponse(BaseModel):
    """转换响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    config: Optional[Union[str, Dict[str, Any]]] = Field(None, description="转换后的配置")
    download_url: Optional[str] = Field(None, description="下载链接")
    nodes_count: int = Field(0, description="节点数量")
    
    
class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field("healthy", description="服务状态")
    version: str = Field("1.0.0", description="版本信息")
    timestamp: str = Field(..., description="时间戳")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(False, description="是否成功")
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细信息")