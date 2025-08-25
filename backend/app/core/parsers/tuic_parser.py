"""
TUIC v5 协议解析器
支持 TUIC (The Ultimate In Connections) v5 新一代 QUIC 代理协议解析和配置生成
"""

import json
import base64
import urllib.parse
import uuid
from typing import List, Dict, Any, Optional

from ..protocol_parser_interface import (
    BaseProtocolParser, BaseConfigGenerator, ParseResult, ConfigGenerationResult,
    ProtocolVersion, ConfigFormat, performance_monitor, cache_result
)
from ...models.schemas import ProxyNode, ProxyType


class TuicParser(BaseProtocolParser):
    """TUIC 协议解析器"""

    def __init__(self):
        super().__init__(
            protocol_name="tuic",
            supported_versions=[ProtocolVersion.V4, ProtocolVersion.V5]
        )

    @property
    def protocol_schemes(self) -> List[str]:
        return ['tuic', 'tuic4', 'tuic5']

    def detect_version(self, url: str) -> ProtocolVersion:
        """检测 TUIC 版本"""
        if 'tuic5://' in url:
            return ProtocolVersion.V5
        elif 'tuic4://' in url:
            return ProtocolVersion.V4
        
        # 通过查询参数检测版本
        params = self._parse_query_params(url.split('?', 1)[1] if '?' in url else '')
        version = params.get('version', params.get('v'))
        
        if version == '5':
            return ProtocolVersion.V5
        elif version == '4':
            return ProtocolVersion.V4
        
        # 默认为 v5
        return ProtocolVersion.V5

    @performance_monitor
    def parse_url(self, url: str) -> ParseResult:
        """
        解析 TUIC URL
        
        支持格式：
        1. tuic://uuid:password@host:port?congestion_control=bbr&udp_relay_mode=native#name
        2. tuic5://uuid:password@host:port?sni=example.com&allow_insecure=1#name
        3. tuic://host:port?uuid=xxx&password=yyy&version=5#name
        """
        try:
            if not self.can_parse(url):
                return ParseResult(error=f"不支持的协议格式: {url}")

            scheme, username, password, hostname, port, path, query, fragment = self._extract_basic_info(url)
            
            if not hostname:
                return ParseResult(error="缺少服务器地址")

            port = port or 443
            params = self._parse_query_params(query)
            
            # 检测版本
            version = self.detect_version(url)
            
            # 提取UUID和密码
            tuic_uuid = None
            tuic_password = None
            
            if username and password:
                # UUID和密码在URL认证部分
                tuic_uuid = username
                tuic_password = password
            elif params.get('uuid') and params.get('password'):
                # UUID和密码在查询参数中
                tuic_uuid = params.get('uuid')
                tuic_password = params.get('password')
            
            # 验证UUID格式
            if tuic_uuid:
                try:
                    uuid.UUID(tuic_uuid)
                except ValueError:
                    return ParseResult(error=f"无效的UUID格式: {tuic_uuid}")

            # 节点名称
            name = urllib.parse.unquote(fragment) if fragment else f"{hostname}:{port}"

            # 构建节点
            node = ProxyNode(
                name=name,
                type=ProxyType.TUIC,
                server=hostname,
                port=port,
                uuid=tuic_uuid,
                password=tuic_password,
                udp=True  # TUIC 基于 QUIC/UDP
            )

            # TLS 配置
            if params.get('sni'):
                node.sni = params['sni']
            else:
                node.sni = hostname  # 默认使用服务器地址作为 SNI

            # 证书验证配置
            node.skip_cert_verify = self._safe_bool(
                params.get('allow_insecure', params.get('allowInsecure', params.get('insecure', False)))
            )

            # TUIC 特有配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            # 拥塞控制算法
            congestion_control = params.get('congestion_control', params.get('congestion', 'cubic'))
            node.extra_config['congestion_control'] = congestion_control

            # UDP 中继模式 (v5 特有)
            if version == ProtocolVersion.V5:
                udp_relay_mode = params.get('udp_relay_mode', params.get('udp_mode', 'native'))
                node.extra_config['udp_relay_mode'] = udp_relay_mode
                
                # 减少 RTT 
                reduce_rtt = self._safe_bool(params.get('reduce_rtt', False))
                if reduce_rtt:
                    node.extra_config['reduce_rtt'] = True

            # ALPN 配置
            alpn = params.get('alpn')
            if alpn:
                node.extra_config['alpn'] = alpn.split(',')

            # 心跳间隔
            heartbeat_interval = params.get('heartbeat')
            if heartbeat_interval:
                try:
                    node.extra_config['heartbeat'] = f"{int(heartbeat_interval)}s"
                except ValueError:
                    node.extra_config['heartbeat'] = heartbeat_interval

            # 版本信息
            node.extra_config['version'] = version.value

            # 验证节点
            warnings = self.validate_node(node)
            if not tuic_uuid:
                warnings.append("缺少UUID")
            if not tuic_password:
                warnings.append("缺少密码")

            result = ParseResult(success=True, node=node, warnings=warnings)
            return result

        except Exception as e:
            self.logger.error(f"解析 TUIC URL 失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def parse_clash_config(self, config: Dict[str, Any]) -> ParseResult:
        """解析 Clash 格式的 TUIC 配置"""
        try:
            if config.get('type') != 'tuic':
                return ParseResult(error="配置类型不是 tuic")

            name = config.get('name', '')
            server = config.get('server', '')
            port = self._safe_int(config.get('port'), 443)

            if not server:
                return ParseResult(error="缺少服务器地址")

            node = ProxyNode(
                name=name,
                type=ProxyType.TUIC,
                server=server,
                port=port,
                udp=True
            )

            # 认证配置
            node.uuid = config.get('uuid', config.get('token'))  # token 是旧版本的字段
            node.password = config.get('password')

            # TLS 配置
            node.sni = config.get('sni', server)
            node.skip_cert_verify = self._safe_bool(config.get('skip-cert-verify', False))

            # TUIC 特有配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            # 版本检测
            version = config.get('version', 5)
            if version == 5:
                node.extra_config['version'] = ProtocolVersion.V5.value
            else:
                node.extra_config['version'] = ProtocolVersion.V4.value

            # 拥塞控制
            if config.get('congestion-control'):
                node.extra_config['congestion_control'] = config['congestion-control']

            # UDP 中继模式 (v5)
            if config.get('udp-relay-mode'):
                node.extra_config['udp_relay_mode'] = config['udp-relay-mode']

            # 减少 RTT (v5)
            if config.get('reduce-rtt'):
                node.extra_config['reduce_rtt'] = self._safe_bool(config['reduce-rtt'])

            # ALPN
            if config.get('alpn'):
                alpn = config['alpn']
                if isinstance(alpn, str):
                    node.extra_config['alpn'] = alpn.split(',')
                elif isinstance(alpn, list):
                    node.extra_config['alpn'] = alpn

            # 心跳
            if config.get('heartbeat'):
                node.extra_config['heartbeat'] = config['heartbeat']

            # 验证节点
            warnings = self.validate_node(node)

            return ParseResult(success=True, node=node, warnings=warnings)

        except Exception as e:
            self.logger.error(f"解析 Clash TUIC 配置失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")


class TuicConfigGenerator(BaseConfigGenerator):
    """TUIC 配置生成器"""

    def __init__(self):
        super().__init__(
            format_name="tuic",
            supported_formats=[ConfigFormat.CLASH, ConfigFormat.CLASH_META, ConfigFormat.SING_BOX]
        )

    def supports_protocol(self, protocol_name: str) -> bool:
        return protocol_name.lower() in ['tuic', 'tuic4', 'tuic5']

    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        defaults = {
            ConfigFormat.CLASH: {
                'udp': True,
                'skip_cert_verify': False,
                'version': 5,
            },
            ConfigFormat.CLASH_META: {
                'udp': True,
                'skip_cert_verify': False,
                'version': 5,
                'reduce_rtt': False,
            },
            ConfigFormat.SING_BOX: {
                'type': 'tuic',
                'version': 5,
                'congestion_control': 'cubic',
                'udp_relay_mode': 'native',
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
            required_fields = ['name', 'server', 'port', 'uuid', 'password']
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
            if not node.uuid:
                warnings.append("缺少UUID，可能导致连接失败")
            if not node.password:
                warnings.append("缺少密码，可能导致连接失败")

            return ConfigGenerationResult(success=True, config=config, warnings=warnings)

        except Exception as e:
            self.logger.error(f"生成 TUIC 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def _generate_clash_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Clash 格式配置"""
        config = {
            'name': node.name,
            'type': 'tuic',
            'server': node.server,
            'port': int(node.port),
            'uuid': node.uuid,
            'password': node.password,
            'udp': options.get('udp', True),
        }

        # 版本配置
        version = 5
        if hasattr(node, 'extra_config') and node.extra_config.get('version'):
            try:
                version = int(node.extra_config['version'].replace('v', ''))
            except (ValueError, AttributeError):
                pass
        config['version'] = version

        # TLS 配置
        if node.sni and node.sni != node.server:
            config['sni'] = node.sni

        if node.skip_cert_verify:
            config['skip-cert-verify'] = True

        # TUIC 特有配置
        if hasattr(node, 'extra_config') and node.extra_config:
            extra = node.extra_config
            
            # 拥塞控制
            if extra.get('congestion_control'):
                config['congestion-control'] = extra['congestion_control']
            
            # UDP 中继模式 (v5)
            if version >= 5 and extra.get('udp_relay_mode'):
                config['udp-relay-mode'] = extra['udp_relay_mode']
            
            # 减少 RTT (v5)
            if version >= 5 and extra.get('reduce_rtt'):
                config['reduce-rtt'] = extra['reduce_rtt']
            
            # ALPN
            if extra.get('alpn'):
                config['alpn'] = extra['alpn']
            
            # 心跳
            if extra.get('heartbeat'):
                config['heartbeat'] = extra['heartbeat']

        return self._filter_none_values(config)

    def _generate_sing_box_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 sing-box 格式配置"""
        config = {
            'type': 'tuic',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'uuid': node.uuid,
            'password': node.password,
        }

        # 版本配置
        version = options.get('version', 5)
        if hasattr(node, 'extra_config') and node.extra_config.get('version'):
            try:
                version = int(node.extra_config['version'].replace('v', ''))
            except (ValueError, AttributeError):
                pass
        
        # sing-box 使用不同的字段名
        if version >= 5:
            config['version'] = 5
        else:
            config['version'] = 4

        # 拥塞控制
        congestion_control = options.get('congestion_control', 'cubic')
        if hasattr(node, 'extra_config') and node.extra_config.get('congestion_control'):
            congestion_control = node.extra_config['congestion_control']
        config['congestion_control'] = congestion_control

        # UDP 中继模式 (v5)
        if version >= 5:
            udp_relay_mode = options.get('udp_relay_mode', 'native')
            if hasattr(node, 'extra_config') and node.extra_config.get('udp_relay_mode'):
                udp_relay_mode = node.extra_config['udp_relay_mode']
            config['udp_relay_mode'] = udp_relay_mode

        # TLS 配置
        tls_config = {}
        if node.sni:
            tls_config['server_name'] = node.sni
        
        if node.skip_cert_verify:
            tls_config['insecure'] = True

        # ALPN
        if hasattr(node, 'extra_config') and node.extra_config.get('alpn'):
            tls_config['alpn'] = node.extra_config['alpn']

        if tls_config:
            config['tls'] = tls_config

        # 心跳间隔
        if hasattr(node, 'extra_config') and node.extra_config.get('heartbeat'):
            heartbeat = node.extra_config['heartbeat']
            # 转换为 sing-box 格式的时间
            if isinstance(heartbeat, str) and heartbeat.endswith('s'):
                try:
                    config['heartbeat'] = heartbeat
                except:
                    config['heartbeat'] = '10s'

        return self._filter_none_values(config)


# 注册解析器和生成器
def register_tuic_support():
    """注册 TUIC 支持"""
    from ..protocol_parser_interface import protocol_registry
    
    parser = TuicParser()
    generator = TuicConfigGenerator()
    
    protocol_registry.register_parser(parser)
    protocol_registry.register_generator(generator)
    
    return parser, generator