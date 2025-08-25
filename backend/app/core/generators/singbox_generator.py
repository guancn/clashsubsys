"""
sing-box 配置生成器
支持新兴的统一配置格式 sing-box，提供现代化的代理配置生成
"""

import json
from typing import List, Dict, Any, Optional
from enum import Enum

from ..protocol_parser_interface import (
    BaseConfigGenerator, ConfigGenerationResult, ConfigFormat, performance_monitor
)
from ...models.schemas import ProxyNode, ProxyType


class SingBoxProtocolType(str, Enum):
    """sing-box 支持的协议类型"""
    SHADOWSOCKS = "shadowsocks"
    VMESS = "vmess"
    VLESS = "vless"
    TROJAN = "trojan"
    HYSTERIA = "hysteria"
    HYSTERIA2 = "hysteria2"
    TUIC = "tuic"
    WIREGUARD = "wireguard"
    SSH = "ssh"
    HTTP = "http"
    SOCKS = "socks"


class SingBoxConfigGenerator(BaseConfigGenerator):
    """sing-box 配置生成器"""

    def __init__(self):
        super().__init__(
            format_name="sing-box",
            supported_formats=[ConfigFormat.SING_BOX]
        )

    def supports_protocol(self, protocol_name: str) -> bool:
        """检查是否支持指定协议"""
        protocol_mapping = {
            'ss': SingBoxProtocolType.SHADOWSOCKS,
            'shadowsocks': SingBoxProtocolType.SHADOWSOCKS,
            'vmess': SingBoxProtocolType.VMESS,
            'vless': SingBoxProtocolType.VLESS,
            'trojan': SingBoxProtocolType.TROJAN,
            'hysteria': SingBoxProtocolType.HYSTERIA,
            'hysteria2': SingBoxProtocolType.HYSTERIA2,
            'tuic': SingBoxProtocolType.TUIC,
            'wireguard': SingBoxProtocolType.WIREGUARD,
            'wg': SingBoxProtocolType.WIREGUARD,
        }
        return protocol_name.lower() in protocol_mapping

    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        return {
            'log_level': 'info',
            'enable_statistics': True,
            'enable_memory_limit': True,
            'memory_limit': '128M',
            'dns_strategy': 'prefer_ipv4',
            'domain_strategy': 'prefer_ipv4',
        }

    @performance_monitor
    def generate_proxy_config(self, 
                            node: ProxyNode, 
                            format_type: ConfigFormat,
                            options: Optional[Dict[str, Any]] = None) -> ConfigGenerationResult:
        """生成单个代理节点的配置"""
        try:
            if not self.supports_protocol(node.type):
                return ConfigGenerationResult(error=f"不支持的协议类型: {node.type}")

            # 验证必需字段
            required_fields = ['name', 'server', 'port', 'type']
            errors = self._validate_required_fields(node, required_fields)
            if errors:
                return ConfigGenerationResult(error=f"配置验证失败: {'; '.join(errors)}")

            # 合并选项
            default_options = self.get_default_options(format_type)
            merged_options = self._merge_options(default_options, options)

            # 根据协议类型生成配置
            config = self._generate_outbound_config(node, merged_options)
            
            warnings = []
            return ConfigGenerationResult(success=True, config=config, warnings=warnings)

        except Exception as e:
            self.logger.error(f"生成 sing-box 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def generate_full_config(self, 
                           nodes: List[ProxyNode], 
                           options: Optional[Dict[str, Any]] = None) -> ConfigGenerationResult:
        """生成完整的 sing-box 配置"""
        try:
            # 合并选项
            default_options = self.get_default_options(ConfigFormat.SING_BOX)
            merged_options = self._merge_options(default_options, options)

            # 生成出站配置
            outbounds = []
            node_tags = []
            
            for node in nodes:
                try:
                    outbound_result = self.generate_proxy_config(node, ConfigFormat.SING_BOX, options)
                    if outbound_result.is_valid:
                        outbounds.append(outbound_result.config)
                        node_tags.append(node.name)
                    else:
                        self.logger.warning(f"跳过无效节点: {node.name} - {outbound_result.error}")
                except Exception as e:
                    self.logger.error(f"生成节点配置失败 {node.name}: {e}")
                    continue

            if not outbounds:
                return ConfigGenerationResult(error="没有有效的代理节点")

            # 生成完整配置
            config = self._build_full_config(outbounds, node_tags, merged_options)

            return ConfigGenerationResult(
                success=True, 
                config=config, 
                warnings=[f"成功生成 {len(outbounds)} 个节点配置"]
            )

        except Exception as e:
            self.logger.error(f"生成完整 sing-box 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def _generate_outbound_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """根据节点类型生成出站配置"""
        protocol = node.type.lower() if hasattr(node.type, 'lower') else str(node.type).lower()
        
        if protocol in ['ss', 'shadowsocks']:
            return self._generate_shadowsocks_config(node, options)
        elif protocol == 'vmess':
            return self._generate_vmess_config(node, options)
        elif protocol == 'vless':
            return self._generate_vless_config(node, options)
        elif protocol == 'trojan':
            return self._generate_trojan_config(node, options)
        elif protocol == 'hysteria':
            return self._generate_hysteria_config(node, options)
        elif protocol == 'hysteria2':
            return self._generate_hysteria2_config(node, options)
        elif protocol == 'tuic':
            return self._generate_tuic_config(node, options)
        elif protocol in ['wireguard', 'wg']:
            return self._generate_wireguard_config(node, options)
        else:
            raise ValueError(f"不支持的协议类型: {protocol}")

    def _generate_shadowsocks_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Shadowsocks 配置"""
        config = {
            'type': 'shadowsocks',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'method': node.cipher,
            'password': node.password,
        }

        # 插件配置
        if hasattr(node, 'plugin') and node.plugin:
            plugin_config = {'enabled': True}
            if node.plugin == 'obfs-local':
                plugin_config.update({
                    'type': 'obfs-local',
                    'mode': getattr(node, 'plugin_opts', {}).get('obfs', 'http'),
                    'host': getattr(node, 'plugin_opts', {}).get('obfs-host', '')
                })
            elif node.plugin == 'v2ray-plugin':
                plugin_config.update({
                    'type': 'v2ray-plugin',
                    'mode': 'websocket' if getattr(node, 'plugin_opts', {}).get('mode') == 'websocket' else 'quic',
                    'host': getattr(node, 'plugin_opts', {}).get('host', ''),
                    'path': getattr(node, 'plugin_opts', {}).get('path', '/'),
                    'tls': getattr(node, 'plugin_opts', {}).get('tls', False)
                })
            
            if plugin_config.get('type'):
                config['plugin'] = plugin_config

        return self._filter_none_values(config)

    def _generate_vmess_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 VMess 配置"""
        config = {
            'type': 'vmess',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'uuid': node.uuid,
            'security': node.cipher or 'auto',
        }

        # alterId (V2Ray legacy)
        if node.alterId is not None:
            config['alter_id'] = int(node.alterId)

        # TLS 配置
        if node.tls:
            tls_config = {
                'enabled': True,
                'server_name': node.sni or node.server,
                'insecure': node.skip_cert_verify or False,
            }
            config['tls'] = tls_config

        # 传输配置
        transport_config = self._build_transport_config(node)
        if transport_config:
            config['transport'] = transport_config

        return self._filter_none_values(config)

    def _generate_vless_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 VLESS 配置"""
        config = {
            'type': 'vless',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'uuid': node.uuid,
        }

        # TLS 配置
        if node.tls:
            tls_config = {
                'enabled': True,
                'server_name': node.sni or node.server,
                'insecure': node.skip_cert_verify or False,
            }

            # Reality 配置
            if hasattr(node, 'extra_config') and node.extra_config.get('reality'):
                reality_config = node.extra_config['reality']
                tls_config['reality'] = {
                    'enabled': True,
                    'public_key': reality_config['public_key'],
                }
                if reality_config.get('short_id'):
                    tls_config['reality']['short_id'] = reality_config['short_id']

                # uTLS 配置
                fingerprint = reality_config.get('fingerprint', 'chrome')
                tls_config['utls'] = {
                    'enabled': True,
                    'fingerprint': fingerprint
                }

            config['tls'] = tls_config

        # 传输配置
        transport_config = self._build_transport_config(node)
        if transport_config:
            config['transport'] = transport_config

        return self._filter_none_values(config)

    def _generate_trojan_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Trojan 配置"""
        config = {
            'type': 'trojan',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'password': node.password,
        }

        # TLS 配置
        tls_config = {
            'enabled': True,
            'server_name': node.sni or node.server,
            'insecure': node.skip_cert_verify or False,
        }
        config['tls'] = tls_config

        return self._filter_none_values(config)

    def _generate_hysteria_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Hysteria 配置"""
        config = {
            'type': 'hysteria',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
        }

        # 认证配置
        if node.auth_str:
            config['auth_str'] = node.auth_str

        # 带宽配置
        if node.up:
            try:
                up_mbps = int(float(node.up.replace('Mbps', '').replace('mbps', '')))
                config['up_mbps'] = up_mbps
            except:
                config['up_mbps'] = 100
        
        if node.down:
            try:
                down_mbps = int(float(node.down.replace('Mbps', '').replace('mbps', '')))
                config['down_mbps'] = down_mbps
            except:
                config['down_mbps'] = 100

        # TLS 配置
        tls_config = {
            'enabled': True,
            'server_name': node.sni or node.server,
            'insecure': node.skip_cert_verify or False,
        }
        config['tls'] = tls_config

        return self._filter_none_values(config)

    def _generate_hysteria2_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 Hysteria2 配置"""
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
                up_mbps = int(float(node.up.replace('Mbps', '').replace('mbps', '')))
                config['up_mbps'] = up_mbps
            except:
                config['up_mbps'] = 100
        
        if node.down:
            try:
                down_mbps = int(float(node.down.replace('Mbps', '').replace('mbps', '')))
                config['down_mbps'] = down_mbps
            except:
                config['down_mbps'] = 100

        # TLS 配置
        tls_config = {
            'enabled': True,
            'server_name': node.sni or node.server,
            'insecure': node.skip_cert_verify or False,
        }
        config['tls'] = tls_config

        # 混淆配置
        if hasattr(node, 'extra_config') and node.extra_config.get('obfs'):
            obfs_config = node.extra_config['obfs']
            config['obfs'] = {
                'type': obfs_config['type'],
            }
            if obfs_config.get('password'):
                config['obfs']['password'] = obfs_config['password']

        return self._filter_none_values(config)

    def _generate_tuic_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 TUIC 配置"""
        config = {
            'type': 'tuic',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'uuid': node.uuid,
            'password': node.password,
        }

        # 版本配置
        version = 5
        if hasattr(node, 'extra_config') and node.extra_config.get('version'):
            try:
                version = int(node.extra_config['version'].replace('v', ''))
            except:
                pass
        config['version'] = version

        # 拥塞控制
        congestion_control = 'cubic'
        if hasattr(node, 'extra_config') and node.extra_config.get('congestion_control'):
            congestion_control = node.extra_config['congestion_control']
        config['congestion_control'] = congestion_control

        # UDP 中继模式 (v5)
        if version >= 5:
            udp_relay_mode = 'native'
            if hasattr(node, 'extra_config') and node.extra_config.get('udp_relay_mode'):
                udp_relay_mode = node.extra_config['udp_relay_mode']
            config['udp_relay_mode'] = udp_relay_mode

        # TLS 配置
        tls_config = {
            'enabled': True,
            'server_name': node.sni or node.server,
            'insecure': node.skip_cert_verify or False,
        }
        config['tls'] = tls_config

        return self._filter_none_values(config)

    def _generate_wireguard_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 WireGuard 配置"""
        if not (hasattr(node, 'extra_config') and node.extra_config.get('wireguard')):
            raise ValueError("缺少WireGuard配置")

        wg_config = node.extra_config['wireguard']
        
        config = {
            'type': 'wireguard',
            'tag': node.name,
            'server': node.server,
            'server_port': int(node.port),
            'private_key': wg_config['private_key'],
            'peer_public_key': wg_config['peer_public_key'],
        }

        # 预共享密钥
        if wg_config.get('preshared_key'):
            config['pre_shared_key'] = wg_config['preshared_key']

        # 本地地址
        if wg_config.get('address'):
            config['local_address'] = wg_config['address']

        # MTU
        config['mtu'] = wg_config.get('mtu', 1420)

        return self._filter_none_values(config)

    def _build_transport_config(self, node: ProxyNode) -> Optional[Dict[str, Any]]:
        """构建传输层配置"""
        if not node.network or node.network == 'tcp':
            return None

        if node.network == 'ws':
            transport_config = {'type': 'ws'}
            if node.path:
                transport_config['path'] = node.path
            if node.host:
                transport_config['headers'] = {'Host': node.host}
            return transport_config

        elif node.network == 'h2':
            transport_config = {'type': 'http'}
            if node.path:
                transport_config['path'] = node.path
            if node.host:
                transport_config['host'] = [node.host] if isinstance(node.host, str) else node.host
            return transport_config

        elif node.network == 'grpc':
            transport_config = {'type': 'grpc'}
            if hasattr(node, 'extra_config') and node.extra_config.get('grpc', {}).get('service_name'):
                transport_config['service_name'] = node.extra_config['grpc']['service_name']
            elif node.path:
                transport_config['service_name'] = node.path
            return transport_config

        return None

    def _build_full_config(self, outbounds: List[Dict[str, Any]], node_tags: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """构建完整的 sing-box 配置"""
        config = {
            'log': {
                'level': options.get('log_level', 'info'),
                'timestamp': True
            },
            'dns': {
                'servers': [
                    {
                        'tag': 'default',
                        'address': 'https://1.1.1.1/dns-query',
                        'strategy': options.get('dns_strategy', 'prefer_ipv4'),
                        'detour': 'proxy'
                    },
                    {
                        'tag': 'local',
                        'address': 'https://223.5.5.5/dns-query',
                        'strategy': options.get('dns_strategy', 'prefer_ipv4'),
                        'detour': 'direct'
                    }
                ],
                'rules': [
                    {
                        'domain_suffix': ['.cn'],
                        'server': 'local'
                    }
                ],
                'strategy': options.get('dns_strategy', 'prefer_ipv4')
            },
            'inbounds': [
                {
                    'type': 'mixed',
                    'tag': 'mixed-in',
                    'listen': '::',
                    'listen_port': 2080,
                    'sniff': True,
                    'domain_strategy': options.get('domain_strategy', 'prefer_ipv4')
                },
                {
                    'type': 'tun',
                    'tag': 'tun-in',
                    'inet4_address': '172.19.0.1/30',
                    'mtu': 9000,
                    'auto_route': True,
                    'strict_route': True,
                    'sniff': True,
                    'endpoint_independent_nat': False,
                    'stack': 'system',
                    'domain_strategy': options.get('domain_strategy', 'prefer_ipv4')
                }
            ],
            'outbounds': []
        }

        # 添加代理选择器
        if len(node_tags) > 1:
            config['outbounds'].append({
                'type': 'selector',
                'tag': 'proxy',
                'outbounds': ['auto'] + node_tags,
                'default': 'auto'
            })

            # 添加自动选择
            config['outbounds'].append({
                'type': 'urltest',
                'tag': 'auto',
                'outbounds': node_tags,
                'url': 'http://www.gstatic.com/generate_204',
                'interval': '10m',
                'tolerance': 50
            })
        else:
            # 单个节点直接作为代理
            config['outbounds'].append({
                'type': 'selector',
                'tag': 'proxy',
                'outbounds': node_tags,
                'default': node_tags[0] if node_tags else 'direct'
            })

        # 添加代理节点
        config['outbounds'].extend(outbounds)

        # 添加直连和阻断
        config['outbounds'].extend([
            {
                'type': 'direct',
                'tag': 'direct'
            },
            {
                'type': 'block',
                'tag': 'block'
            },
            {
                'type': 'dns',
                'tag': 'dns-out'
            }
        ])

        # 路由规则
        config['route'] = {
            'rules': [
                {
                    'protocol': 'dns',
                    'outbound': 'dns-out'
                },
                {
                    'domain_suffix': ['.cn'],
                    'outbound': 'direct'
                },
                {
                    'geoip': ['private', 'cn'],
                    'outbound': 'direct'
                },
                {
                    'domain_suffix': ['googlevideo.com', 'youtube.com', 'youtu.be'],
                    'outbound': 'proxy'
                }
            ],
            'final': 'proxy',
            'auto_detect_interface': True
        }

        # 实验性功能
        experimental_config = {}
        if options.get('enable_statistics', True):
            experimental_config['clash_api'] = {
                'external_controller': '127.0.0.1:9090',
                'external_ui': 'ui'
            }

        if experimental_config:
            config['experimental'] = experimental_config

        return config


# 注册生成器
def register_singbox_generator():
    """注册 sing-box 配置生成器"""
    from ..protocol_parser_interface import protocol_registry
    
    generator = SingBoxConfigGenerator()
    protocol_registry.register_generator(generator)
    
    return generator