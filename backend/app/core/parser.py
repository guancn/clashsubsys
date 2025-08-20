"""
订阅解析器 - 解析各种代理协议的订阅链接
支持 SS、SSR、V2Ray、Trojan、Hysteria 等协议
"""

import re
import json
import base64
import urllib.parse
from typing import List, Dict, Any, Optional
import yaml
import logging

from ..models.schemas import ProxyNode, ProxyType

logger = logging.getLogger(__name__)


class SubscriptionParser:
    """订阅解析器"""
    
    def __init__(self):
        self.supported_protocols = {
            'ss': self._parse_ss,
            'ssr': self._parse_ssr,
            'vmess': self._parse_vmess,
            'vless': self._parse_vless,
            'trojan': self._parse_trojan,
            'hysteria': self._parse_hysteria,
            'hysteria2': self._parse_hysteria2,
            'tuic': self._parse_tuic,
            'wireguard': self._parse_wireguard,
        }
    
    def parse_subscription(self, content: str) -> List[ProxyNode]:
        """
        解析订阅内容
        
        Args:
            content: 订阅内容（base64编码或原始格式）
            
        Returns:
            解析后的代理节点列表
        """
        try:
            # 尝试 base64 解码
            try:
                decoded_content = base64.b64decode(content).decode('utf-8')
            except Exception:
                decoded_content = content
            
            # 检查是否为 Clash 配置格式
            if self._is_clash_config(decoded_content):
                return self._parse_clash_config(decoded_content)
            
            # 按行分割并解析每个节点
            lines = decoded_content.strip().split('\n')
            nodes = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    node = self._parse_node_line(line)
                    if node:
                        nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse node line: {line}, error: {e}")
                    continue
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to parse subscription: {e}")
            return []
    
    def _is_clash_config(self, content: str) -> bool:
        """检查内容是否为 Clash 配置格式"""
        try:
            data = yaml.safe_load(content)
            return isinstance(data, dict) and ('proxies' in data or 'Proxy' in data)
        except:
            return False
    
    def _parse_clash_config(self, content: str) -> List[ProxyNode]:
        """解析 Clash 配置格式"""
        try:
            data = yaml.safe_load(content)
            proxies = data.get('proxies', data.get('Proxy', []))
            
            nodes = []
            for proxy in proxies:
                try:
                    node = self._parse_clash_proxy(proxy)
                    if node:
                        nodes.append(node)
                except Exception as e:
                    logger.warning(f"Failed to parse clash proxy: {proxy}, error: {e}")
                    continue
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to parse clash config: {e}")
            return []
    
    def _parse_clash_proxy(self, proxy: Dict[str, Any]) -> Optional[ProxyNode]:
        """解析单个 Clash 代理配置"""
        try:
            proxy_type = proxy.get('type', '').lower()
            
            # 基础字段
            node_data = {
                'name': proxy.get('name', ''),
                'type': proxy_type,
                'server': proxy.get('server', ''),
                'port': proxy.get('port', 443),
            }
            
            # 根据协议类型添加特定字段
            if proxy_type == 'ss':
                node_data.update({
                    'cipher': proxy.get('cipher'),
                    'password': proxy.get('password'),
                    'udp': proxy.get('udp', True),
                })
            elif proxy_type == 'ssr':
                node_data.update({
                    'cipher': proxy.get('cipher'),
                    'password': proxy.get('password'),
                    'protocol': proxy.get('protocol'),
                    'protocol_param': proxy.get('protocol-param'),
                    'obfs': proxy.get('obfs'),
                    'obfs_param': proxy.get('obfs-param'),
                })
            elif proxy_type == 'vmess':
                node_data.update({
                    'uuid': proxy.get('uuid'),
                    'alterId': proxy.get('alterId', 0),
                    'cipher': proxy.get('cipher', 'auto'),
                    'network': proxy.get('network', 'tcp'),
                    'tls': proxy.get('tls', False),
                })
                
                # WebSocket 配置
                if node_data['network'] == 'ws':
                    ws_opts = proxy.get('ws-opts', {})
                    node_data.update({
                        'path': ws_opts.get('path'),
                        'host': ws_opts.get('headers', {}).get('Host'),
                    })
                
                # HTTP/2 配置
                elif node_data['network'] == 'h2':
                    h2_opts = proxy.get('h2-opts', {})
                    node_data.update({
                        'path': h2_opts.get('path'),
                        'host': h2_opts.get('host'),
                    })
                
                # gRPC 配置
                elif node_data['network'] == 'grpc':
                    grpc_opts = proxy.get('grpc-opts', {})
                    node_data.update({
                        'path': grpc_opts.get('grpc-service-name'),
                    })
                
                # TLS 配置
                if node_data['tls']:
                    tls_opts = proxy.get('tls-opts', {})
                    node_data['sni'] = tls_opts.get('sni') or tls_opts.get('servername')
                    node_data['skip_cert_verify'] = tls_opts.get('skip-cert-verify', False)
            
            elif proxy_type == 'vless':
                node_data.update({
                    'uuid': proxy.get('uuid'),
                    'network': proxy.get('network', 'tcp'),
                    'tls': proxy.get('tls', False),
                })
                
                # 处理传输协议配置（类似 vmess）
                self._handle_transport_config(node_data, proxy)
            
            elif proxy_type == 'trojan':
                node_data.update({
                    'password': proxy.get('password'),
                    'sni': proxy.get('sni'),
                    'skip_cert_verify': proxy.get('skip-cert-verify', False),
                })
            
            elif proxy_type in ['hysteria', 'hysteria2']:
                node_data.update({
                    'auth_str': proxy.get('auth_str') or proxy.get('auth-str'),
                    'up': proxy.get('up'),
                    'down': proxy.get('down'),
                    'sni': proxy.get('sni'),
                    'skip_cert_verify': proxy.get('skip-cert-verify', False),
                })
            
            return ProxyNode(**node_data)
            
        except Exception as e:
            logger.error(f"Failed to parse clash proxy: {e}")
            return None
    
    def _handle_transport_config(self, node_data: Dict[str, Any], proxy: Dict[str, Any]):
        """处理传输协议配置"""
        network = node_data.get('network', 'tcp')
        
        if network == 'ws':
            ws_opts = proxy.get('ws-opts', {})
            node_data.update({
                'path': ws_opts.get('path'),
                'host': ws_opts.get('headers', {}).get('Host'),
            })
        elif network == 'h2':
            h2_opts = proxy.get('h2-opts', {})
            node_data.update({
                'path': h2_opts.get('path'),
                'host': h2_opts.get('host'),
            })
        elif network == 'grpc':
            grpc_opts = proxy.get('grpc-opts', {})
            node_data.update({
                'path': grpc_opts.get('grpc-service-name'),
            })
        
        # TLS 配置
        if node_data.get('tls'):
            tls_opts = proxy.get('tls-opts', {})
            node_data['sni'] = tls_opts.get('sni') or tls_opts.get('servername')
            node_data['skip_cert_verify'] = tls_opts.get('skip-cert-verify', False)
    
    def _parse_node_line(self, line: str) -> Optional[ProxyNode]:
        """解析单行节点信息"""
        # 提取协议
        if '://' not in line:
            return None
            
        protocol = line.split('://')[0].lower()
        
        if protocol in self.supported_protocols:
            return self.supported_protocols[protocol](line)
        else:
            logger.warning(f"Unsupported protocol: {protocol}")
            return None
    
    def _parse_ss(self, url: str) -> Optional[ProxyNode]:
        """解析 Shadowsocks 节点"""
        try:
            # ss://base64(method:password)@server:port#name
            # 或 ss://base64(method:password@server:port)#name
            
            parsed = urllib.parse.urlparse(url)
            
            # 解码主体部分
            encoded_part = parsed.netloc
            if '@' not in encoded_part:
                # 格式1: ss://base64(method:password@server:port)
                decoded = base64.b64decode(encoded_part).decode('utf-8')
                if '@' in decoded:
                    auth_part, server_part = decoded.rsplit('@', 1)
                    method, password = auth_part.split(':', 1)
                    server, port = server_part.split(':', 1)
                else:
                    return None
            else:
                # 格式2: ss://base64(method:password)@server:port
                auth_encoded, server_part = encoded_part.split('@', 1)
                auth_decoded = base64.b64decode(auth_encoded).decode('utf-8')
                method, password = auth_decoded.split(':', 1)
                server, port = server_part.split(':', 1)
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.SS,
                server=server,
                port=int(port),
                cipher=method,
                password=password,
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse SS node: {e}")
            return None
    
    def _parse_ssr(self, url: str) -> Optional[ProxyNode]:
        """解析 ShadowsocksR 节点"""
        try:
            # ssr://base64(server:port:protocol:method:obfs:password_base64/?params)
            
            encoded_part = url[6:]  # 移除 "ssr://"
            decoded = base64.b64decode(encoded_part).decode('utf-8')
            
            parts = decoded.split('/')
            main_part = parts[0]
            params_part = parts[1] if len(parts) > 1 else ""
            
            # 解析主要部分
            server, port, protocol, method, obfs, password_encoded = main_part.split(':')
            password = base64.b64decode(password_encoded).decode('utf-8')
            
            # 解析参数
            params = {}
            if params_part.startswith('?'):
                param_str = params_part[1:]  # 移除 '?'
                for param in param_str.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = base64.b64decode(value).decode('utf-8')
            
            name = params.get('remarks', f"{server}:{port}")
            
            return ProxyNode(
                name=name,
                type=ProxyType.SSR,
                server=server,
                port=int(port),
                cipher=method,
                password=password,
                protocol=protocol,
                obfs=obfs,
                protocol_param=params.get('protoparam'),
                obfs_param=params.get('obfsparam'),
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse SSR node: {e}")
            return None
    
    def _parse_vmess(self, url: str) -> Optional[ProxyNode]:
        """解析 VMess 节点"""
        try:
            # vmess://base64(json_config)
            
            encoded_part = url[8:]  # 移除 "vmess://"
            decoded = base64.b64decode(encoded_part).decode('utf-8')
            config = json.loads(decoded)
            
            return ProxyNode(
                name=config.get('ps', config.get('add', '') + ':' + str(config.get('port', ''))),
                type=ProxyType.VMESS,
                server=config.get('add', ''),
                port=int(config.get('port', 443)),
                uuid=config.get('id', ''),
                alterId=int(config.get('aid', 0)),
                cipher=config.get('scy', 'auto'),
                network=config.get('net', 'tcp'),
                tls=config.get('tls') == 'tls',
                host=config.get('host'),
                path=config.get('path'),
                sni=config.get('sni'),
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse VMess node: {e}")
            return None
    
    def _parse_vless(self, url: str) -> Optional[ProxyNode]:
        """解析 VLESS 节点"""
        try:
            # vless://uuid@server:port?params#name
            
            parsed = urllib.parse.urlparse(url)
            uuid = parsed.username
            server = parsed.hostname
            port = parsed.port or 443
            
            # 解析查询参数
            params = urllib.parse.parse_qs(parsed.query)
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.VLESS,
                server=server,
                port=port,
                uuid=uuid,
                network=params.get('type', ['tcp'])[0],
                tls=params.get('security', ['none'])[0] in ['tls', 'xtls'],
                host=params.get('host', [None])[0],
                path=params.get('path', [None])[0],
                sni=params.get('sni', [None])[0],
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse VLESS node: {e}")
            return None
    
    def _parse_trojan(self, url: str) -> Optional[ProxyNode]:
        """解析 Trojan 节点"""
        try:
            # trojan://password@server:port?params#name
            
            parsed = urllib.parse.urlparse(url)
            password = parsed.username
            server = parsed.hostname
            port = parsed.port or 443
            
            # 解析查询参数
            params = urllib.parse.parse_qs(parsed.query)
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.TROJAN,
                server=server,
                port=port,
                password=password,
                sni=params.get('sni', [server])[0],
                skip_cert_verify=params.get('allowInsecure', ['false'])[0].lower() == 'true',
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Trojan node: {e}")
            return None
    
    def _parse_hysteria(self, url: str) -> Optional[ProxyNode]:
        """解析 Hysteria 节点"""
        try:
            # hysteria://server:port?params#name
            
            parsed = urllib.parse.urlparse(url)
            server = parsed.hostname
            port = parsed.port or 443
            
            # 解析查询参数
            params = urllib.parse.parse_qs(parsed.query)
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.HYSTERIA,
                server=server,
                port=port,
                auth_str=params.get('auth', [None])[0],
                up=params.get('up', [None])[0],
                down=params.get('down', [None])[0],
                sni=params.get('peer', [server])[0],
                skip_cert_verify=params.get('insecure', ['false'])[0].lower() == 'true',
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Hysteria node: {e}")
            return None
    
    def _parse_hysteria2(self, url: str) -> Optional[ProxyNode]:
        """解析 Hysteria2 节点"""
        # Hysteria2 解析逻辑类似 Hysteria，但协议有所不同
        try:
            node = self._parse_hysteria(url)
            if node:
                node.type = ProxyType.HYSTERIA2
            return node
        except Exception as e:
            logger.error(f"Failed to parse Hysteria2 node: {e}")
            return None
    
    def _parse_tuic(self, url: str) -> Optional[ProxyNode]:
        """解析 TUIC 节点"""
        try:
            # tuic://uuid:password@server:port?params#name
            
            parsed = urllib.parse.urlparse(url)
            uuid = parsed.username
            password = parsed.password
            server = parsed.hostname
            port = parsed.port or 443
            
            # 解析查询参数
            params = urllib.parse.parse_qs(parsed.query)
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.TUIC,
                server=server,
                port=port,
                uuid=uuid,
                password=password,
                sni=params.get('sni', [server])[0],
                skip_cert_verify=params.get('allowInsecure', ['false'])[0].lower() == 'true',
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse TUIC node: {e}")
            return None
    
    def _parse_wireguard(self, url: str) -> Optional[ProxyNode]:
        """解析 WireGuard 节点 (简单实现)"""
        try:
            # 由于 WireGuard 配置较复杂，这里只做基础解析
            parsed = urllib.parse.urlparse(url)
            server = parsed.hostname
            port = parsed.port or 51820
            
            name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"
            
            return ProxyNode(
                name=name,
                type=ProxyType.WIREGUARD,
                server=server,
                port=port,
                udp=True
            )
            
        except Exception as e:
            logger.error(f"Failed to parse WireGuard node: {e}")
            return None