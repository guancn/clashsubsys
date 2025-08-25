"""
协议解析器抽象接口定义
提供统一的协议解析和配置生成接口，支持新协议的快速集成
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, Union
from enum import Enum
import logging

from ..models.schemas import ProxyNode


class ProtocolVersion(Enum):
    """协议版本枚举"""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    V5 = "v5"


class ConfigFormat(Enum):
    """配置格式枚举"""
    CLASH = "clash"
    CLASH_META = "clash-meta"
    SING_BOX = "sing-box"
    V2RAY = "v2ray"
    XRAY = "xray"
    QUANTUMULT_X = "quantumult-x"
    SURGE = "surge"


class ParseResult:
    """解析结果封装"""
    def __init__(self, 
                 success: bool = False,
                 node: Optional[ProxyNode] = None,
                 error: Optional[str] = None,
                 warnings: Optional[List[str]] = None):
        self.success = success
        self.node = node
        self.error = error
        self.warnings = warnings or []

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    @property
    def is_valid(self) -> bool:
        return self.success and self.node is not None


class ConfigGenerationResult:
    """配置生成结果封装"""
    def __init__(self,
                 success: bool = False,
                 config: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 warnings: Optional[List[str]] = None):
        self.success = success
        self.config = config
        self.error = error
        self.warnings = warnings or []

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    @property
    def is_valid(self) -> bool:
        return self.success and self.config is not None


class IProtocolParser(ABC):
    """协议解析器抽象基类"""

    def __init__(self, protocol_name: str, supported_versions: List[ProtocolVersion]):
        self.protocol_name = protocol_name
        self.supported_versions = supported_versions
        self.logger = logging.getLogger(f"parser.{protocol_name}")

    @property
    @abstractmethod
    def protocol_schemes(self) -> List[str]:
        """支持的协议方案"""
        pass

    @abstractmethod
    def can_parse(self, url: str) -> bool:
        """检查是否能够解析指定的URL"""
        pass

    @abstractmethod
    def parse_url(self, url: str) -> ParseResult:
        """解析URL格式的协议链接"""
        pass

    def parse_clash_config(self, config: Dict[str, Any]) -> ParseResult:
        """解析Clash配置格式（可选实现）"""
        return ParseResult(error="Clash config parsing not supported")

    def validate_node(self, node: ProxyNode) -> List[str]:
        """验证节点配置的有效性，返回警告列表"""
        warnings = []
        
        # 基础字段验证
        if not node.name:
            warnings.append("节点名称为空")
        if not node.server:
            warnings.append("服务器地址为空")
        if not (1 <= node.port <= 65535):
            warnings.append(f"端口号无效: {node.port}")
        
        return warnings

    @abstractmethod
    def detect_version(self, url: str) -> ProtocolVersion:
        """检测协议版本"""
        pass

    def supports_version(self, version: ProtocolVersion) -> bool:
        """检查是否支持指定版本"""
        return version in self.supported_versions


class IConfigGenerator(ABC):
    """配置生成器抽象基类"""

    def __init__(self, format_name: str, supported_formats: List[ConfigFormat]):
        self.format_name = format_name
        self.supported_formats = supported_formats
        self.logger = logging.getLogger(f"generator.{format_name}")

    @abstractmethod
    def supports_protocol(self, protocol_name: str) -> bool:
        """检查是否支持指定协议"""
        pass

    @abstractmethod
    def generate_proxy_config(self, 
                            node: ProxyNode, 
                            format_type: ConfigFormat,
                            options: Optional[Dict[str, Any]] = None) -> ConfigGenerationResult:
        """生成代理配置"""
        pass

    def validate_options(self, options: Dict[str, Any]) -> List[str]:
        """验证配置选项，返回警告列表"""
        return []

    @abstractmethod
    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        pass


class ProtocolParserRegistry:
    """协议解析器注册表"""

    def __init__(self):
        self._parsers: Dict[str, IProtocolParser] = {}
        self._generators: Dict[str, IConfigGenerator] = {}
        self.logger = logging.getLogger("registry")

    def register_parser(self, parser: IProtocolParser):
        """注册协议解析器"""
        for scheme in parser.protocol_schemes:
            if scheme in self._parsers:
                self.logger.warning(f"协议方案 '{scheme}' 已存在，将被覆盖")
            self._parsers[scheme] = parser
        self.logger.info(f"已注册协议解析器: {parser.protocol_name}")

    def register_generator(self, generator: IConfigGenerator):
        """注册配置生成器"""
        self._generators[generator.format_name] = generator
        self.logger.info(f"已注册配置生成器: {generator.format_name}")

    def get_parser(self, url: str) -> Optional[IProtocolParser]:
        """根据URL获取合适的解析器"""
        scheme = url.split('://')[0].lower() if '://' in url else ''
        return self._parsers.get(scheme)

    def get_generator(self, format_name: str) -> Optional[IConfigGenerator]:
        """获取指定格式的配置生成器"""
        return self._generators.get(format_name.lower())

    def get_supported_protocols(self) -> List[str]:
        """获取所有支持的协议列表"""
        protocols = set()
        for parser in self._parsers.values():
            protocols.add(parser.protocol_name)
        return sorted(list(protocols))

    def get_supported_formats(self) -> List[str]:
        """获取所有支持的配置格式列表"""
        return sorted(list(self._generators.keys()))

    def list_parsers(self) -> Dict[str, List[str]]:
        """列出所有解析器及其支持的方案"""
        result = {}
        for parser in set(self._parsers.values()):
            result[parser.protocol_name] = parser.protocol_schemes
        return result

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'parsers_count': len(set(self._parsers.values())),
            'generators_count': len(self._generators),
            'supported_schemes': list(self._parsers.keys()),
            'supported_formats': list(self._generators.keys())
        }


# 全局注册表实例
protocol_registry = ProtocolParserRegistry()


class BaseProtocolParser(IProtocolParser):
    """协议解析器基础实现"""

    def __init__(self, protocol_name: str, supported_versions: List[ProtocolVersion]):
        super().__init__(protocol_name, supported_versions)

    def can_parse(self, url: str) -> bool:
        """默认实现：检查URL scheme是否匹配"""
        if '://' not in url:
            return False
        scheme = url.split('://')[0].lower()
        return scheme in self.protocol_schemes

    def _extract_basic_info(self, url: str) -> tuple:
        """提取URL中的基础信息：scheme, userinfo, host, port, path, query, fragment"""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return (
            parsed.scheme,
            parsed.username,
            parsed.password,
            parsed.hostname,
            parsed.port,
            parsed.path,
            parsed.query,
            parsed.fragment
        )

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """安全转换为整数"""
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default

    def _safe_bool(self, value: Any, default: bool = False) -> bool:
        """安全转换为布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return default

    def _parse_query_params(self, query_string: str) -> Dict[str, str]:
        """解析查询参数"""
        import urllib.parse
        if not query_string:
            return {}
        return dict(urllib.parse.parse_qsl(query_string))


class BaseConfigGenerator(IConfigGenerator):
    """配置生成器基础实现"""

    def __init__(self, format_name: str, supported_formats: List[ConfigFormat]):
        super().__init__(format_name, supported_formats)

    def _filter_none_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """过滤掉None值"""
        return {k: v for k, v in config.items() if v is not None}

    def _merge_options(self, default: Dict[str, Any], user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并默认选项和用户选项"""
        if not user:
            return default.copy()
        
        result = default.copy()
        result.update(user)
        return result

    def _validate_required_fields(self, node: ProxyNode, fields: List[str]) -> List[str]:
        """验证必需字段"""
        errors = []
        for field in fields:
            if not hasattr(node, field) or getattr(node, field) is None:
                errors.append(f"缺少必需字段: {field}")
        return errors


# 性能监控装饰器
def performance_monitor(func):
    """性能监控装饰器"""
    import time
    import functools

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            elapsed = time.time() - start_time
            if elapsed > 0.1:  # 超过100ms记录警告
                self.logger.warning(f"{func.__name__} 执行时间较长: {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"{func.__name__} 执行失败 (耗时 {elapsed:.3f}s): {e}")
            raise
    return wrapper


# 缓存装饰器
def cache_result(ttl: int = 300):
    """结果缓存装饰器"""
    import time
    import functools
    import hashlib

    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = hashlib.md5(f"{func.__name__}:{args}:{kwargs}".encode()).hexdigest()
            
            # 检查缓存
            if cache_key in cache:
                cached_result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return cached_result
                else:
                    del cache[cache_key]
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            # 清理过期缓存（简单实现）
            if len(cache) > 1000:  # 限制缓存大小
                current_time = time.time()
                expired_keys = [k for k, (_, t) in cache.items() if current_time - t >= ttl]
                for k in expired_keys:
                    del cache[k]
            
            return result
        return wrapper
    return decorator