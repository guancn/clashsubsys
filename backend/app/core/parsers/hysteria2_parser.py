"""
Hysteria2 协议解析器
支持 Hysteria v2 基于 QUIC 的高性能代理协议解析和配置生成
"""

import json
import base64
import urllib.parse
from typing import List, Dict, Any, Optional

from ..protocol_parser_interface import (
    BaseProtocolParser, BaseConfigGenerator, ParseResult, ConfigGenerationResult,
    ProtocolVersion, ConfigFormat, performance_monitor, cache_result
)
from ...models.schemas import ProxyNode, ProxyType


class Hysteria2Parser(BaseProtocolParser):
    """Hysteria2 协议解析器"""

    def __init__(self):
        super().__init__(
            protocol_name="hysteria2",
            supported_versions=[ProtocolVersion.V2]
        )

    @property
    def protocol_schemes(self) -> List[str]:
        return ['hysteria2', 'hy2']

    def detect_version(self, url: str) -> ProtocolVersion:
        return ProtocolVersion.V2

    @performance_monitor
    def parse_url(self, url: str) -> ParseResult:
        """
        解析 Hysteria2 URL
        
        支持格式：
        1. hysteria2://auth@host:port?param=value#name
        2. hy2://password@host:port?up=100&down=200&obfs=salamander&sni=example.com#name
        3. hysteria2://host:port?auth=xxx&up=100&down=200#name
        """
        try:
            if not self.can_parse(url):
                return ParseResult(error=f"不支持的协议格式: {url}")

            scheme, username, password, hostname, port, path, query, fragment = self._extract_basic_info(url)
            
            if not hostname:
                return ParseResult(error="缺少服务器地址")

            port = port or 443
            params = self._parse_query_params(query)
            
            # 提取认证信息
            auth_str = None
            if username:  # 认证信息在用户名部分
                auth_str = username
            elif params.get('auth'):  # 认证信息在查询参数中
                auth_str = params.get('auth')
            elif params.get('password'):  # 密码形式的认证
                auth_str = params.get('password')

            # 节点名称
            name = urllib.parse.unquote(fragment) if fragment else f"{hostname}:{port}"

            # 构建节点
            node = ProxyNode(
                name=name,
                type=ProxyType.HYSTERIA2,
                server=hostname,
                port=port,
                auth_str=auth_str,
                udp=True  # Hysteria2 基于 QUIC/UDP
            )

            # 解析带宽配置
            if params.get('up'):
                node.up = params['up']
            if params.get('down'):
                node.down = params['down']

            # 解析 TLS 配置
            if params.get('sni'):
                node.sni = params['sni']
            else:
                node.sni = hostname  # 默认使用服务器地址作为 SNI

            # 证书验证配置
            node.skip_cert_verify = self._safe_bool(
                params.get('insecure', params.get('allowInsecure', False))
            )

            # 混淆配置（Hysteria2 特有）
            obfs_type = params.get('obfs')
            obfs_password = params.get('obfs-password', params.get('obfsPassword'))
            if obfs_type:
                # 将混淆配置存储在额外字段中
                if not hasattr(node, 'extra_config'):
                    node.extra_config = {}
                node.extra_config['obfs'] = {
                    'type': obfs_type,
                    'password': obfs_password
                }

            # QUIC 配置
            if params.get('disable_mtu_discovery'):
                if not hasattr(node, 'extra_config'):
                    node.extra_config = {}
                node.extra_config['quic'] = {
                    'disable_mtu_discovery': self._safe_bool(params['disable_mtu_discovery'])
                }

            # 验证节点
            warnings = self.validate_node(node)
            if not auth_str:
                warnings.append("缺少认证信息")

            result = ParseResult(success=True, node=node, warnings=warnings)
            return result

        except Exception as e:
            self.logger.error(f"解析 Hysteria2 URL 失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def parse_clash_config(self, config: Dict[str, Any]) -> ParseResult:
        """解析 Clash 格式的 Hysteria2 配置"""
        try:
            if config.get('type') != 'hysteria2':
                return ParseResult(error="配置类型不是 hysteria2")

            name = config.get('name', '')
            server = config.get('server', '')
            port = self._safe_int(config.get('port'), 443)

            if not server:
                return ParseResult(error="缺少服务器地址")

            node = ProxyNode(
                name=name,
                type=ProxyType.HYSTERIA2,
                server=server,
                port=port,
                udp=True
            )

            # 认证配置
            if config.get('auth'):
                node.auth_str = config['auth']
            elif config.get('auth-str'):
                node.auth_str = config['auth-str']
            elif config.get('password'):
                node.auth_str = config['password']

            # 带宽配置
            if config.get('up'):
                node.up = str(config['up'])
            if config.get('down'):
                node.down = str(config['down'])

            # TLS 配置
            node.sni = config.get('sni', server)
            node.skip_cert_verify = self._safe_bool(config.get('skip-cert-verify', False))

            # 混淆配置
            obfs_config = config.get('obfs')
            if obfs_config:
                if not hasattr(node, 'extra_config'):
                    node.extra_config = {}
                node.extra_config['obfs'] = obfs_config

            # 验证节点
            warnings = self.validate_node(node)

            return ParseResult(success=True, node=node, warnings=warnings)

        except Exception as e:
            self.logger.error(f"解析 Clash Hysteria2 配置失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")


class Hysteria2ConfigGenerator(BaseConfigGenerator):
    """Hysteria2 配置生成器"""

    def __init__(self):
        super().__init__(
            format_name="hysteria2",
            supported_formats=[ConfigFormat.CLASH, ConfigFormat.CLASH_META, ConfigFormat.SING_BOX]
        )

    def supports_protocol(self, protocol_name: str) -> bool:
        return protocol_name.lower() in ['hysteria2', 'hy2']

    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        defaults = {
            ConfigFormat.CLASH: {
                'udp': True,
                'skip_cert_verify': False,
            },
            ConfigFormat.CLASH_META: {
                'udp': True,
                'skip_cert_verify': False,
                'fast_open': False,
            },
            ConfigFormat.SING_BOX: {
                'type': 'hysteria2',
                'up_mbps': 100,
                'down_mbps': 100,
            }
        }
        return defaults.get(format_type, {})

    @performance_monitor
    def generate_proxy_config(self, 
                            node: ProxyNode, 
                            format_type: ConfigFormat,
                            options: Optional[Dict[str, Any]] = None) -> ConfigGenerationResult:
        """生成代理配置"""
        try:
            if not self.supports_protocol(node.type):
                return ConfigGenerationResult(error=f"不支持的协议类型: {node.type}")

            # 验证必需字段
            required_fields = ['name', 'server', 'port']
            errors = self._validate_required_fields(node, required_fields)
            if errors:
                return ConfigGenerationResult(error=f"配置验证失败: {'; '.join(errors)}")

            # 合并选项
            default_options = self.get_default_options(format_type)
            merged_options = self._merge_options(default_options, options)

            # 根据格式生成配置
            if format_type in [ConfigFormat.CLASH, ConfigFormat.CLASH_META]:
                config = self._generate_clash_config(node, merged_options)
            elif format_type == ConfigFormat.SING_BOX:
                config = self._generate_sing_box_config(node, merged_options)
            else:
                return ConfigGenerationResult(error=f"不支持的配置格式: {format_type}")

            warnings = []
            if not node.auth_str:
                warnings.append("缺少认证信息，可能导致连接失败")

            return ConfigGenerationResult(success=True, config=config, warnings=warnings)

        except Exception as e:
            self.logger.error(f"生成 Hysteria2 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def _generate_clash_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Clash 格式配置"""
        config = {
            'name': node.name,
            'type': 'hysteria2',
            'server': node.server,
            'port': int(node.port),
            'udp': options.get('udp', True),
        }

        # 认证配置
        if node.auth_str:
            config['auth'] = node.auth_str

        # 带宽配置
        if node.up:
            try:
                # 尝试解析为数字（Mbps）
                up_value = float(node.up.replace('Mbps', '').replace('mbps', ''))
                config['up'] = f"{int(up_value)} Mbps"
            except (ValueError, AttributeError):
                config['up'] = str(node.up)

        if node.down:
            try:
                down_value = float(node.down.replace('Mbps', '').replace('mbps', ''))
                config['down'] = f"{int(down_value)} Mbps"
            except (ValueError, AttributeError):
                config['down'] = str(node.down)

        # TLS 配置
        if node.sni and node.sni != node.server:
            config['sni'] = node.sni

        if node.skip_cert_verify:
            config['skip-cert-verify'] = True

        # 混淆配置
        if hasattr(node, 'extra_config') and node.extra_config.get('obfs'):
            obfs_config = node.extra_config['obfs']
            config['obfs'] = obfs_config['type']
            if obfs_config.get('password'):
                config['obfs-password'] = obfs_config['password']

        # Clash Meta 特有配置
        if options.get('fast_open'):
            config['tfo'] = True

        return self._filter_none_values(config)

    def _generate_sing_box_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 sing-box 格式配置"""
        config = {
            'type': 'hysteria2',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
        }

        # 认证配置
        if node.auth_str:
            config['auth'] = node.auth_str

        # 带宽配置
        if node.up:
            try:
                up_value = int(float(node.up.replace('Mbps', '').replace('mbps', '')))
                config['up_mbps'] = up_value
            except (ValueError, AttributeError):
                config['up_mbps'] = options.get('up_mbps', 100)
        else:
            config['up_mbps'] = options.get('up_mbps', 100)

        if node.down:
            try:
                down_value = int(float(node.down.replace('Mbps', '').replace('mbps', '')))
                config['down_mbps'] = down_value
            except (ValueError, AttributeError):
                config['down_mbps'] = options.get('down_mbps', 100)
        else:
            config['down_mbps'] = options.get('down_mbps', 100)

        # TLS 配置
        tls_config = {}
        if node.sni:
            tls_config['server_name'] = node.sni
        
        if node.skip_cert_verify:
            tls_config['insecure'] = True

        if tls_config:
            config['tls'] = tls_config

        # 混淆配置
        if hasattr(node, 'extra_config') and node.extra_config.get('obfs'):
            obfs_config = node.extra_config['obfs']
            config['obfs'] = {
                'type': obfs_config['type']
            }
            if obfs_config.get('password'):
                config['obfs']['password'] = obfs_config['password']

        return self._filter_none_values(config)


# 注册解析器和生成器
def register_hysteria2_support():
    """注册 Hysteria2 支持"""
    from ..protocol_parser_interface import protocol_registry
    
    parser = Hysteria2Parser()
    generator = Hysteria2ConfigGenerator()
    
    protocol_registry.register_parser(parser)
    protocol_registry.register_generator(generator)
    
    return parser, generator