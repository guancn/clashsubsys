"""
VLESS Reality 协议解析器
支持具有强伪装能力的 VLESS Reality 协议解析和配置生成
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


class VlessRealityParser(BaseProtocolParser):
    """VLESS Reality 协议解析器"""

    def __init__(self):
        super().__init__(
            protocol_name="vless-reality",
            supported_versions=[ProtocolVersion.V1]
        )

    @property
    def protocol_schemes(self) -> List[str]:
        return ['vless']

    def detect_version(self, url: str) -> ProtocolVersion:
        return ProtocolVersion.V1

    def can_parse(self, url: str) -> bool:
        """检查是否为VLESS Reality配置"""
        if not super().can_parse(url):
            return False
        
        # 检查是否包含Reality相关参数
        params = self._parse_query_params(url.split('?', 1)[1] if '?' in url else '')
        return (params.get('security') == 'reality' or 
                params.get('type') == 'reality' or 
                'pbk' in params or 'publicKey' in params)

    @performance_monitor
    def parse_url(self, url: str) -> ParseResult:
        """
        解析 VLESS Reality URL
        
        支持格式：
        vless://uuid@host:port?type=tcp&security=reality&pbk=publickey&fp=chrome&sni=example.com&sid=shortId#name
        """
        try:
            if not self.can_parse(url):
                return ParseResult(error=f"不支持的协议格式或缺少Reality配置: {url}")

            scheme, username, password, hostname, port, path, query, fragment = self._extract_basic_info(url)
            
            if not hostname:
                return ParseResult(error="缺少服务器地址")
            
            if not username:
                return ParseResult(error="缺少UUID")

            # 验证UUID格式
            try:
                uuid.UUID(username)
            except ValueError:
                return ParseResult(error=f"无效的UUID格式: {username}")

            port = port or 443
            params = self._parse_query_params(query)
            
            # 检查是否为Reality协议
            security = params.get('security', '').lower()
            if security != 'reality':
                return ParseResult(error="不是Reality协议配置")

            # 节点名称
            name = urllib.parse.unquote(fragment) if fragment else f"{hostname}:{port}"

            # 构建节点
            node = ProxyNode(
                name=name,
                type=ProxyType.VLESS,
                server=hostname,
                port=port,
                uuid=username,
                udp=True,
                tls=True,  # Reality 始终使用 TLS
                network=params.get('type', params.get('net', 'tcp')),
                path=params.get('path', ''),
                host=params.get('host', '')
            )

            # Reality 特有配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            reality_config = {}
            
            # 公钥 (必需)
            public_key = params.get('pbk', params.get('publicKey', params.get('pk')))
            if not public_key:
                return ParseResult(error="缺少Reality公钥 (pbk)")
            reality_config['public_key'] = public_key

            # 服务器名称指示 (SNI)
            sni = params.get('sni')
            if sni:
                node.sni = sni
                reality_config['server_name'] = sni

            # Short ID
            short_id = params.get('sid', params.get('shortId'))
            if short_id:
                reality_config['short_id'] = short_id

            # 指纹
            fingerprint = params.get('fp', params.get('fingerprint', 'chrome'))
            reality_config['fingerprint'] = fingerprint

            # Spider X (可选)
            spx = params.get('spx', params.get('spiderX'))
            if spx:
                reality_config['spider_x'] = spx

            node.extra_config['reality'] = reality_config

            # 传输层配置
            if node.network == 'tcp':
                # TCP 配置
                header_type = params.get('headerType', params.get('header'))
                if header_type and header_type != 'none':
                    node.extra_config['tcp'] = {
                        'header': {
                            'type': header_type
                        }
                    }
                    
                    # HTTP 伪装配置
                    if header_type == 'http':
                        http_request = {}
                        if params.get('host'):
                            http_request['headers'] = {'Host': [params['host']]}
                        if params.get('path'):
                            http_request['path'] = [params['path']]
                        
                        if http_request:
                            node.extra_config['tcp']['header']['request'] = http_request

            elif node.network == 'ws':
                # WebSocket 配置
                ws_config = {}
                if params.get('path'):
                    ws_config['path'] = params['path']
                if params.get('host'):
                    ws_config['headers'] = {'Host': params['host']}
                
                if ws_config:
                    node.extra_config['websocket'] = ws_config

            elif node.network == 'h2':
                # HTTP/2 配置
                h2_config = {}
                if params.get('path'):
                    h2_config['path'] = params['path']
                if params.get('host'):
                    h2_config['host'] = [params['host']]
                
                if h2_config:
                    node.extra_config['http2'] = h2_config

            elif node.network == 'grpc':
                # gRPC 配置
                if params.get('serviceName', params.get('path')):
                    node.extra_config['grpc'] = {
                        'service_name': params.get('serviceName', params.get('path'))
                    }
                
                # gRPC 模式
                grpc_mode = params.get('mode', 'gun')
                if grpc_mode:
                    node.extra_config.setdefault('grpc', {})['mode'] = grpc_mode

            # 流量控制
            flow = params.get('flow')
            if flow:
                node.extra_config['flow'] = flow

            # 验证节点
            warnings = self.validate_node(node)
            if not public_key:
                warnings.append("缺少Reality公钥")
            if not sni:
                warnings.append("建议配置SNI以提高连接成功率")

            result = ParseResult(success=True, node=node, warnings=warnings)
            return result

        except Exception as e:
            self.logger.error(f"解析 VLESS Reality URL 失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def parse_clash_config(self, config: Dict[str, Any]) -> ParseResult:
        """解析 Clash 格式的 VLESS Reality 配置"""
        try:
            if config.get('type') != 'vless':
                return ParseResult(error="配置类型不是 vless")

            # 检查是否为Reality配置
            reality_opts = config.get('reality-opts')
            tls_opts = config.get('tls-opts', {})
            
            if not reality_opts and tls_opts.get('type') != 'reality':
                return ParseResult(error="不是Reality配置")

            name = config.get('name', '')
            server = config.get('server', '')
            port = self._safe_int(config.get('port'), 443)
            uuid_val = config.get('uuid', '')

            if not server:
                return ParseResult(error="缺少服务器地址")
            if not uuid_val:
                return ParseResult(error="缺少UUID")

            node = ProxyNode(
                name=name,
                type=ProxyType.VLESS,
                server=server,
                port=port,
                uuid=uuid_val,
                udp=True,
                tls=True,
                network=config.get('network', 'tcp')
            )

            # Reality 配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            reality_config = {}
            
            if reality_opts:
                # 新格式 reality-opts
                if reality_opts.get('public-key'):
                    reality_config['public_key'] = reality_opts['public-key']
                if reality_opts.get('short-id'):
                    reality_config['short_id'] = reality_opts['short-id']
            elif tls_opts.get('type') == 'reality':
                # 集成在 tls-opts 中
                if tls_opts.get('public-key'):
                    reality_config['public_key'] = tls_opts['public-key']
                if tls_opts.get('short-id'):
                    reality_config['short_id'] = tls_opts['short-id']

            # SNI 配置
            node.sni = config.get('servername', config.get('sni', server))
            reality_config['server_name'] = node.sni

            # 指纹
            fingerprint = config.get('client-fingerprint', 'chrome')
            if reality_opts and reality_opts.get('fingerprint'):
                fingerprint = reality_opts['fingerprint']
            reality_config['fingerprint'] = fingerprint

            node.extra_config['reality'] = reality_config

            # 传输层配置
            self._parse_transport_config(node, config)

            # 验证节点
            warnings = self.validate_node(node)
            if not reality_config.get('public_key'):
                warnings.append("缺少Reality公钥")

            return ParseResult(success=True, node=node, warnings=warnings)

        except Exception as e:
            self.logger.error(f"解析 Clash VLESS Reality 配置失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def _parse_transport_config(self, node: ProxyNode, config: Dict[str, Any]):
        """解析传输层配置"""
        network = node.network
        
        if network == 'ws':
            ws_opts = config.get('ws-opts', {})
            if ws_opts:
                ws_config = {}
                if ws_opts.get('path'):
                    ws_config['path'] = ws_opts['path']
                if ws_opts.get('headers'):
                    ws_config['headers'] = ws_opts['headers']
                
                if ws_config:
                    node.extra_config['websocket'] = ws_config

        elif network == 'h2':
            h2_opts = config.get('h2-opts', {})
            if h2_opts:
                h2_config = {}
                if h2_opts.get('path'):
                    h2_config['path'] = h2_opts['path']
                if h2_opts.get('host'):
                    h2_config['host'] = h2_opts['host']
                
                if h2_config:
                    node.extra_config['http2'] = h2_config

        elif network == 'grpc':
            grpc_opts = config.get('grpc-opts', {})
            if grpc_opts:
                grpc_config = {}
                if grpc_opts.get('grpc-service-name'):
                    grpc_config['service_name'] = grpc_opts['grpc-service-name']
                
                if grpc_config:
                    node.extra_config['grpc'] = grpc_config


class VlessRealityConfigGenerator(BaseConfigGenerator):
    """VLESS Reality 配置生成器"""

    def __init__(self):
        super().__init__(
            format_name="vless-reality",
            supported_formats=[ConfigFormat.CLASH_META, ConfigFormat.SING_BOX, ConfigFormat.XRAY]
        )

    def supports_protocol(self, protocol_name: str) -> bool:
        return (protocol_name.lower() == 'vless' and 
                hasattr(self, 'node') and 
                hasattr(self.node, 'extra_config') and 
                'reality' in self.node.extra_config)

    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        defaults = {
            ConfigFormat.CLASH_META: {
                'udp': True,
                'tls': True,
                'client_fingerprint': 'chrome',
            },
            ConfigFormat.SING_BOX: {
                'type': 'vless',
                'tls_enabled': True,
                'tls_type': 'reality',
            },
            ConfigFormat.XRAY: {
                'protocol': 'vless',
                'security': 'reality',
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
            self.node = node  # 存储节点引用以供supports_protocol使用
            
            if node.type != ProxyType.VLESS:
                return ConfigGenerationResult(error=f"不支持的协议类型: {node.type}")

            # 检查是否为Reality配置
            if not (hasattr(node, 'extra_config') and node.extra_config.get('reality')):
                return ConfigGenerationResult(error="不是VLESS Reality配置")

            # 验证必需字段
            required_fields = ['name', 'server', 'port', 'uuid']
            errors = self._validate_required_fields(node, required_fields)
            if errors:
                return ConfigGenerationResult(error=f"配置验证失败: {'; '.join(errors)}")

            # 检查Reality配置
            reality_config = node.extra_config['reality']
            if not reality_config.get('public_key'):
                return ConfigGenerationResult(error="缺少Reality公钥")

            # 合并选项
            default_options = self.get_default_options(format_type)
            merged_options = self._merge_options(default_options, options)

            # 根据格式生成配置
            if format_type == ConfigFormat.CLASH_META:
                config = self._generate_clash_meta_config(node, merged_options)
            elif format_type == ConfigFormat.SING_BOX:
                config = self._generate_sing_box_config(node, merged_options)
            elif format_type == ConfigFormat.XRAY:
                config = self._generate_xray_config(node, merged_options)
            else:
                return ConfigGenerationResult(error=f"不支持的配置格式: {format_type}")

            warnings = []
            if not reality_config.get('server_name') and not node.sni:
                warnings.append("建议配置SNI以提高连接成功率")

            return ConfigGenerationResult(success=True, config=config, warnings=warnings)

        except Exception as e:
            self.logger.error(f"生成 VLESS Reality 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def _generate_clash_meta_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Clash Meta 格式配置"""
        config = {
            'name': node.name,
            'type': 'vless',
            'server': node.server,
            'port': int(node.port),
            'uuid': node.uuid,
            'tls': True,
            'udp': options.get('udp', True),
            'network': node.network,
        }

        # Reality 配置
        reality_config = node.extra_config['reality']
        reality_opts = {
            'public-key': reality_config['public_key'],
        }

        if reality_config.get('short_id'):
            reality_opts['short-id'] = reality_config['short_id']

        config['reality-opts'] = reality_opts

        # SNI 配置
        if node.sni:
            config['servername'] = node.sni
        elif reality_config.get('server_name'):
            config['servername'] = reality_config['server_name']

        # 客户端指纹
        fingerprint = reality_config.get('fingerprint', options.get('client_fingerprint', 'chrome'))
        config['client-fingerprint'] = fingerprint

        # 传输层配置
        if node.network == 'ws':
            ws_config = node.extra_config.get('websocket', {})
            if ws_config:
                ws_opts = {}
                if ws_config.get('path'):
                    ws_opts['path'] = ws_config['path']
                if ws_config.get('headers'):
                    ws_opts['headers'] = ws_config['headers']
                
                if ws_opts:
                    config['ws-opts'] = ws_opts

        elif node.network == 'h2':
            h2_config = node.extra_config.get('http2', {})
            if h2_config:
                h2_opts = {}
                if h2_config.get('path'):
                    h2_opts['path'] = h2_config['path']
                if h2_config.get('host'):
                    h2_opts['host'] = h2_config['host']
                
                if h2_opts:
                    config['h2-opts'] = h2_opts

        elif node.network == 'grpc':
            grpc_config = node.extra_config.get('grpc', {})
            if grpc_config and grpc_config.get('service_name'):
                config['grpc-opts'] = {
                    'grpc-service-name': grpc_config['service_name']
                }

        # 流量控制
        if node.extra_config.get('flow'):
            config['flow'] = node.extra_config['flow']

        return self._filter_none_values(config)

    def _generate_sing_box_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 sing-box 格式配置"""
        config = {
            'type': 'vless',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'uuid': node.uuid,
        }

        # Reality TLS 配置
        reality_config = node.extra_config['reality']
        tls_config = {
            'enabled': True,
            'server_name': node.sni or reality_config.get('server_name', node.server),
            'reality': {
                'enabled': True,
                'public_key': reality_config['public_key'],
            }
        }

        if reality_config.get('short_id'):
            tls_config['reality']['short_id'] = reality_config['short_id']

        # 客户端指纹
        fingerprint = reality_config.get('fingerprint', 'chrome')
        tls_config['utls'] = {
            'enabled': True,
            'fingerprint': fingerprint
        }

        config['tls'] = tls_config

        # 传输层配置
        if node.network == 'ws':
            ws_config = node.extra_config.get('websocket', {})
            transport_config = {
                'type': 'ws',
            }
            if ws_config.get('path'):
                transport_config['path'] = ws_config['path']
            if ws_config.get('headers'):
                transport_config['headers'] = ws_config['headers']
            
            config['transport'] = transport_config

        elif node.network == 'h2':
            h2_config = node.extra_config.get('http2', {})
            transport_config = {
                'type': 'http',
            }
            if h2_config.get('path'):
                transport_config['path'] = h2_config['path']
            if h2_config.get('host'):
                transport_config['host'] = h2_config['host']
            
            config['transport'] = transport_config

        elif node.network == 'grpc':
            grpc_config = node.extra_config.get('grpc', {})
            if grpc_config.get('service_name'):
                config['transport'] = {
                    'type': 'grpc',
                    'service_name': grpc_config['service_name'],
                    'idle_timeout': '15s',
                    'ping_timeout': '15s'
                }

        return self._filter_none_values(config)

    def _generate_xray_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Xray 格式配置"""
        config = {
            'tag': node.name,
            'protocol': 'vless',
            'settings': {
                'vnext': [{
                    'address': node.server,
                    'port': int(node.port),
                    'users': [{
                        'id': node.uuid,
                        'encryption': 'none'
                    }]
                }]
            },
            'streamSettings': {
                'network': node.network,
                'security': 'reality',
                'realitySettings': {
                    'serverName': node.sni or node.extra_config['reality'].get('server_name', node.server),
                    'publicKey': node.extra_config['reality']['public_key'],
                    'fingerprint': node.extra_config['reality'].get('fingerprint', 'chrome')
                }
            }
        }

        # Short ID
        if node.extra_config['reality'].get('short_id'):
            config['streamSettings']['realitySettings']['shortId'] = node.extra_config['reality']['short_id']

        # 流量控制
        if node.extra_config.get('flow'):
            config['settings']['vnext'][0]['users'][0]['flow'] = node.extra_config['flow']

        # 传输层配置
        if node.network == 'ws':
            ws_config = node.extra_config.get('websocket', {})
            config['streamSettings']['wsSettings'] = {
                'path': ws_config.get('path', '/'),
                'headers': ws_config.get('headers', {})
            }

        elif node.network == 'h2':
            h2_config = node.extra_config.get('http2', {})
            config['streamSettings']['httpSettings'] = {
                'path': h2_config.get('path', '/'),
                'host': h2_config.get('host', [])
            }

        elif node.network == 'grpc':
            grpc_config = node.extra_config.get('grpc', {})
            config['streamSettings']['grpcSettings'] = {
                'serviceName': grpc_config.get('service_name', ''),
                'multiMode': grpc_config.get('mode') == 'multi'
            }

        return self._filter_none_values(config)


# 注册解析器和生成器
def register_vless_reality_support():
    """注册 VLESS Reality 支持"""
    from ..protocol_parser_interface import protocol_registry
    
    parser = VlessRealityParser()
    generator = VlessRealityConfigGenerator()
    
    protocol_registry.register_parser(parser)
    protocol_registry.register_generator(generator)
    
    return parser, generator