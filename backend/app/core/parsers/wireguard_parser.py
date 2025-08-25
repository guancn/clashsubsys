"""
WireGuard 协议解析器
支持现代 VPN 协议 WireGuard 的配置解析和生成
"""

import re
import base64
import urllib.parse
from typing import List, Dict, Any, Optional
import ipaddress

from ..protocol_parser_interface import (
    BaseProtocolParser, BaseConfigGenerator, ParseResult, ConfigGenerationResult,
    ProtocolVersion, ConfigFormat, performance_monitor, cache_result
)
from ...models.schemas import ProxyNode, ProxyType


class WireGuardParser(BaseProtocolParser):
    """WireGuard 协议解析器"""

    def __init__(self):
        super().__init__(
            protocol_name="wireguard",
            supported_versions=[ProtocolVersion.V1]
        )

    @property
    def protocol_schemes(self) -> List[str]:
        return ['wg', 'wireguard']

    def detect_version(self, url: str) -> ProtocolVersion:
        return ProtocolVersion.V1

    @performance_monitor
    def parse_url(self, url: str) -> ParseResult:
        """
        解析 WireGuard URL
        
        支持格式：
        wg://privatekey@endpoint:port/?publickey=xxx&allowed_ips=0.0.0.0/0&dns=1.1.1.1#name
        wireguard://privatekey@endpoint:port/?publickey=xxx&allowed_ips=0.0.0.0/0#name
        """
        try:
            if not self.can_parse(url):
                return ParseResult(error=f"不支持的协议格式: {url}")

            scheme, username, password, hostname, port, path, query, fragment = self._extract_basic_info(url)
            
            if not hostname:
                return ParseResult(error="缺少服务器地址")

            port = port or 51820  # WireGuard 默认端口
            params = self._parse_query_params(query)
            
            # 节点名称
            name = urllib.parse.unquote(fragment) if fragment else f"{hostname}:{port}"

            # 构建节点
            node = ProxyNode(
                name=name,
                type=ProxyType.WIREGUARD,
                server=hostname,
                port=port,
                udp=True  # WireGuard 基于 UDP
            )

            # WireGuard 特有配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            wg_config = {}

            # 私钥 (从用户名部分获取或查询参数)
            private_key = username or params.get('private_key', params.get('privatekey'))
            if private_key:
                # 验证私钥格式（Base64, 44字符）
                if self._validate_wg_key(private_key):
                    wg_config['private_key'] = private_key
                else:
                    return ParseResult(error=f"无效的私钥格式: {private_key}")

            # 公钥 (必需)
            public_key = params.get('public_key', params.get('publickey', params.get('peer_public_key')))
            if not public_key:
                return ParseResult(error="缺少对等方公钥")
            
            if self._validate_wg_key(public_key):
                wg_config['peer_public_key'] = public_key
            else:
                return ParseResult(error=f"无效的公钥格式: {public_key}")

            # 预共享密钥 (可选)
            preshared_key = params.get('preshared_key', params.get('presharedkey', params.get('psk')))
            if preshared_key and self._validate_wg_key(preshared_key):
                wg_config['preshared_key'] = preshared_key

            # 允许的IP范围
            allowed_ips = params.get('allowed_ips', params.get('allowedips', '0.0.0.0/0'))
            wg_config['allowed_ips'] = self._parse_ip_ranges(allowed_ips)

            # 本地地址
            address = params.get('address', params.get('addr'))
            if address:
                wg_config['address'] = self._parse_ip_ranges(address)

            # DNS 服务器
            dns = params.get('dns')
            if dns:
                wg_config['dns'] = dns.split(',')

            # MTU
            mtu = params.get('mtu')
            if mtu:
                try:
                    wg_config['mtu'] = int(mtu)
                except ValueError:
                    pass  # 忽略无效的MTU值

            # Keep-alive 间隔
            keepalive = params.get('keepalive', params.get('persistent_keepalive'))
            if keepalive:
                try:
                    wg_config['persistent_keepalive'] = int(keepalive)
                except ValueError:
                    pass

            # 存储配置
            node.extra_config['wireguard'] = wg_config

            # 验证节点
            warnings = self.validate_node(node)
            if not private_key:
                warnings.append("缺少私钥")
            if not public_key:
                warnings.append("缺少对等方公钥")

            result = ParseResult(success=True, node=node, warnings=warnings)
            return result

        except Exception as e:
            self.logger.error(f"解析 WireGuard URL 失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def parse_clash_config(self, config: Dict[str, Any]) -> ParseResult:
        """解析 Clash 格式的 WireGuard 配置"""
        try:
            if config.get('type') != 'wireguard':
                return ParseResult(error="配置类型不是 wireguard")

            name = config.get('name', '')
            server = config.get('server', '')
            port = self._safe_int(config.get('port'), 51820)

            if not server:
                return ParseResult(error="缺少服务器地址")

            node = ProxyNode(
                name=name,
                type=ProxyType.WIREGUARD,
                server=server,
                port=port,
                udp=True
            )

            # WireGuard 配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            wg_config = {}

            # 密钥配置
            if config.get('private-key'):
                wg_config['private_key'] = config['private-key']
            if config.get('public-key'):
                wg_config['peer_public_key'] = config['public-key']
            if config.get('preshared-key'):
                wg_config['preshared_key'] = config['preshared-key']

            # 网络配置
            if config.get('allowed-ips'):
                allowed_ips = config['allowed-ips']
                if isinstance(allowed_ips, list):
                    wg_config['allowed_ips'] = allowed_ips
                else:
                    wg_config['allowed_ips'] = [allowed_ips]

            if config.get('address'):
                address = config['address']
                if isinstance(address, list):
                    wg_config['address'] = address
                else:
                    wg_config['address'] = [address]

            # DNS 配置
            if config.get('dns'):
                dns = config['dns']
                if isinstance(dns, list):
                    wg_config['dns'] = dns
                else:
                    wg_config['dns'] = [dns]

            # 其他配置
            if config.get('mtu'):
                wg_config['mtu'] = self._safe_int(config['mtu'])
            if config.get('keepalive'):
                wg_config['persistent_keepalive'] = self._safe_int(config['keepalive'])

            node.extra_config['wireguard'] = wg_config

            # 验证节点
            warnings = self.validate_node(node)

            return ParseResult(success=True, node=node, warnings=warnings)

        except Exception as e:
            self.logger.error(f"解析 Clash WireGuard 配置失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def parse_wg_config(self, config_text: str) -> ParseResult:
        """解析标准 WireGuard 配置文件格式"""
        try:
            config = self._parse_ini_format(config_text)
            
            interface = config.get('Interface', {})
            peer = config.get('Peer', {})
            
            if not peer:
                return ParseResult(error="缺少 [Peer] 配置段")

            # 提取服务器信息
            endpoint = peer.get('Endpoint', '')
            if not endpoint:
                return ParseResult(error="缺少 Endpoint 配置")

            if ':' in endpoint:
                server, port_str = endpoint.rsplit(':', 1)
                try:
                    port = int(port_str)
                except ValueError:
                    port = 51820
            else:
                server = endpoint
                port = 51820

            # 生成节点名称
            name = f"WireGuard-{server}:{port}"

            node = ProxyNode(
                name=name,
                type=ProxyType.WIREGUARD,
                server=server,
                port=port,
                udp=True
            )

            # WireGuard 配置
            if not hasattr(node, 'extra_config'):
                node.extra_config = {}

            wg_config = {}

            # Interface 配置
            if interface.get('PrivateKey'):
                wg_config['private_key'] = interface['PrivateKey']
            if interface.get('Address'):
                wg_config['address'] = self._parse_ip_ranges(interface['Address'])
            if interface.get('DNS'):
                wg_config['dns'] = interface['DNS'].split(',')
            if interface.get('MTU'):
                wg_config['mtu'] = self._safe_int(interface['MTU'])

            # Peer 配置
            if peer.get('PublicKey'):
                wg_config['peer_public_key'] = peer['PublicKey']
            if peer.get('PresharedKey'):
                wg_config['preshared_key'] = peer['PresharedKey']
            if peer.get('AllowedIPs'):
                wg_config['allowed_ips'] = self._parse_ip_ranges(peer['AllowedIPs'])
            if peer.get('PersistentKeepalive'):
                wg_config['persistent_keepalive'] = self._safe_int(peer['PersistentKeepalive'])

            node.extra_config['wireguard'] = wg_config

            # 验证节点
            warnings = self.validate_node(node)

            return ParseResult(success=True, node=node, warnings=warnings)

        except Exception as e:
            self.logger.error(f"解析 WireGuard 配置文件失败: {e}")
            return ParseResult(error=f"解析失败: {str(e)}")

    def _validate_wg_key(self, key: str) -> bool:
        """验证 WireGuard 密钥格式"""
        if not key:
            return False
        try:
            # WireGuard 密钥是 32 字节的 Base64 编码，长度应该是 44 字符（包含填充）
            decoded = base64.b64decode(key + '==')  # 添加填充以防止错误
            return len(decoded) == 32
        except:
            return False

    def _parse_ip_ranges(self, ip_string: str) -> List[str]:
        """解析IP地址范围"""
        if not ip_string:
            return []
        
        ranges = []
        for ip_range in ip_string.split(','):
            ip_range = ip_range.strip()
            if ip_range:
                try:
                    # 验证IP地址格式
                    ipaddress.ip_network(ip_range, strict=False)
                    ranges.append(ip_range)
                except ValueError:
                    self.logger.warning(f"无效的IP地址范围: {ip_range}")
        
        return ranges

    def _parse_ini_format(self, config_text: str) -> Dict[str, Dict[str, str]]:
        """解析INI格式的配置文件"""
        config = {}
        current_section = None
        
        for line in config_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 段标题
            section_match = re.match(r'\[(\w+)\]', line)
            if section_match:
                current_section = section_match.group(1)
                config[current_section] = {}
                continue
            
            # 键值对
            if current_section and '=' in line:
                key, value = line.split('=', 1)
                config[current_section][key.strip()] = value.strip()
        
        return config


class WireGuardConfigGenerator(BaseConfigGenerator):
    """WireGuard 配置生成器"""

    def __init__(self):
        super().__init__(
            format_name="wireguard",
            supported_formats=[ConfigFormat.SING_BOX]  # WireGuard 主要在 sing-box 中支持
        )

    def supports_protocol(self, protocol_name: str) -> bool:
        return protocol_name.lower() in ['wireguard', 'wg']

    def get_default_options(self, format_type: ConfigFormat) -> Dict[str, Any]:
        """获取默认配置选项"""
        defaults = {
            ConfigFormat.SING_BOX: {
                'type': 'wireguard',
                'mtu': 1420,
                'gso': False,
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

            # 检查WireGuard配置
            if not (hasattr(node, 'extra_config') and node.extra_config.get('wireguard')):
                return ConfigGenerationResult(error="缺少WireGuard配置")

            wg_config = node.extra_config['wireguard']
            if not wg_config.get('private_key'):
                return ConfigGenerationResult(error="缺少私钥")
            if not wg_config.get('peer_public_key'):
                return ConfigGenerationResult(error="缺少对等方公钥")

            # 合并选项
            default_options = self.get_default_options(format_type)
            merged_options = self._merge_options(default_options, options)

            # 根据格式生成配置
            if format_type == ConfigFormat.SING_BOX:
                config = self._generate_sing_box_config(node, merged_options)
            else:
                return ConfigGenerationResult(error=f"不支持的配置格式: {format_type}")

            warnings = []
            if not wg_config.get('address'):
                warnings.append("缺少本地IP地址配置")

            return ConfigGenerationResult(success=True, config=config, warnings=warnings)

        except Exception as e:
            self.logger.error(f"生成 WireGuard 配置失败: {e}")
            return ConfigGenerationResult(error=f"配置生成失败: {str(e)}")

    def _generate_sing_box_config(self, node: ProxyNode, options: Dict[str, Any]) -> Dict[str, Any]:
        """生成 sing-box 格式配置"""
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
        config['mtu'] = wg_config.get('mtu', options.get('mtu', 1420))

        # GSO
        config['gso'] = options.get('gso', False)

        # Reserved 字段（用于优化）
        if wg_config.get('reserved'):
            config['reserved'] = wg_config['reserved']

        # Workers（并发数）
        if wg_config.get('workers'):
            config['workers'] = wg_config['workers']

        return self._filter_none_values(config)

    def generate_wg_config(self, node: ProxyNode) -> str:
        """生成标准 WireGuard 配置文件格式"""
        if not (hasattr(node, 'extra_config') and node.extra_config.get('wireguard')):
            raise ValueError("缺少WireGuard配置")

        wg_config = node.extra_config['wireguard']
        
        config_lines = ["[Interface]"]
        
        # Interface 配置
        if wg_config.get('private_key'):
            config_lines.append(f"PrivateKey = {wg_config['private_key']}")
        
        if wg_config.get('address'):
            addresses = wg_config['address']
            if isinstance(addresses, list):
                config_lines.append(f"Address = {', '.join(addresses)}")
            else:
                config_lines.append(f"Address = {addresses}")
        
        if wg_config.get('dns'):
            dns_servers = wg_config['dns']
            if isinstance(dns_servers, list):
                config_lines.append(f"DNS = {', '.join(dns_servers)}")
            else:
                config_lines.append(f"DNS = {dns_servers}")
        
        if wg_config.get('mtu'):
            config_lines.append(f"MTU = {wg_config['mtu']}")
        
        # Peer 配置
        config_lines.extend(["", "[Peer]"])
        
        if wg_config.get('peer_public_key'):
            config_lines.append(f"PublicKey = {wg_config['peer_public_key']}")
        
        if wg_config.get('preshared_key'):
            config_lines.append(f"PresharedKey = {wg_config['preshared_key']}")
        
        # Endpoint
        config_lines.append(f"Endpoint = {node.server}:{node.port}")
        
        if wg_config.get('allowed_ips'):
            allowed_ips = wg_config['allowed_ips']
            if isinstance(allowed_ips, list):
                config_lines.append(f"AllowedIPs = {', '.join(allowed_ips)}")
            else:
                config_lines.append(f"AllowedIPs = {allowed_ips}")
        
        if wg_config.get('persistent_keepalive'):
            config_lines.append(f"PersistentKeepalive = {wg_config['persistent_keepalive']}")
        
        return '\n'.join(config_lines)


# 注册解析器和生成器
def register_wireguard_support():
    """注册 WireGuard 支持"""
    from ..protocol_parser_interface import protocol_registry
    
    parser = WireGuardParser()
    generator = WireGuardConfigGenerator()
    
    protocol_registry.register_parser(parser)
    protocol_registry.register_generator(generator)
    
    return parser, generator