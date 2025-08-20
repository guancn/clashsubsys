"""
订阅转换器 - 核心转换逻辑
"""

import yaml
import json
import httpx
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .parser import SubscriptionParser
from .rules import RuleProcessor
from ..models.schemas import (
    ConversionRequest, ProxyNode, ProxyGroup, 
    ClashConfig, ConversionResponse, TargetFormat
)

logger = logging.getLogger(__name__)


class SubscriptionConverter:
    """订阅转换器"""
    
    def __init__(self):
        self.parser = SubscriptionParser()
        self.rule_processor = RuleProcessor()
    
    async def convert_subscription(self, request: ConversionRequest) -> ConversionResponse:
        """
        转换订阅
        
        Args:
            request: 转换请求
            
        Returns:
            转换响应
        """
        try:
            # 1. 获取并解析订阅内容
            all_nodes = []
            for url in request.url:
                nodes = await self._fetch_and_parse_subscription(url)
                all_nodes.extend(nodes)
            
            if not all_nodes:
                return ConversionResponse(
                    success=False,
                    message="无法解析任何有效节点",
                    nodes_count=0
                )
            
            logger.info(f"Parsed {len(all_nodes)} nodes from subscriptions")
            
            # 2. 应用节点过滤
            filtered_nodes = self._apply_node_filters(all_nodes, request)
            
            if not filtered_nodes:
                return ConversionResponse(
                    success=False,
                    message="节点过滤后没有剩余节点",
                    nodes_count=0
                )
            
            logger.info(f"After filtering: {len(filtered_nodes)} nodes remaining")
            
            # 3. 应用节点重命名
            renamed_nodes = self._apply_node_rename(filtered_nodes, request)
            
            # 4. 获取远程规则配置
            remote_config = None
            if request.remote_config:
                remote_config = await self.rule_processor.fetch_remote_config(str(request.remote_config))
            
            # 5. 根据目标格式生成配置
            if request.target == TargetFormat.CLASH:
                config = await self._generate_clash_config(
                    renamed_nodes, request, remote_config
                )
            else:
                # 其他格式暂时不支持，返回 Clash 格式
                config = await self._generate_clash_config(
                    renamed_nodes, request, remote_config
                )
            
            return ConversionResponse(
                success=True,
                message="转换成功",
                config=config,
                nodes_count=len(renamed_nodes)
            )
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return ConversionResponse(
                success=False,
                message=f"转换失败: {str(e)}",
                nodes_count=0
            )
    
    async def _fetch_and_parse_subscription(self, url: str) -> List[ProxyNode]:
        """获取并解析订阅"""
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                headers={'User-Agent': 'clash-meta/1.15.0'},
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.text
                nodes = self.parser.parse_subscription(content)
                
                logger.info(f"Fetched subscription from {url}, got {len(nodes)} nodes")
                return nodes
                
        except Exception as e:
            logger.error(f"Failed to fetch subscription from {url}: {e}")
            return []
    
    def _apply_node_filters(self, nodes: List[ProxyNode], request: ConversionRequest) -> List[ProxyNode]:
        """应用节点过滤"""
        filtered_nodes = nodes[:]
        
        # 提取节点名称用于过滤
        node_names = [node.name for node in nodes]
        
        # 应用过滤规则
        filtered_names = self.rule_processor.apply_node_filters(
            node_names, 
            request.include, 
            request.exclude
        )
        
        # 根据过滤后的名称筛选节点
        filtered_nodes = [node for node in nodes if node.name in filtered_names]
        
        return filtered_nodes
    
    def _apply_node_rename(self, nodes: List[ProxyNode], request: ConversionRequest) -> List[ProxyNode]:
        """应用节点重命名"""
        node_names = [node.name for node in nodes]
        
        # 应用重命名规则
        rename_rules = []
        if request.rename:
            rename_rules = [request.rename]
        
        rename_map = self.rule_processor.apply_node_rename(node_names, rename_rules)
        
        # 应用重命名
        for node in nodes:
            new_name = rename_map.get(node.name, node.name)
            
            # 添加 Emoji（如果启用）
            if request.emoji:
                new_name = self.rule_processor.add_emoji_flags(new_name)
            
            node.name = new_name
        
        return nodes
    
    async def _generate_clash_config(self, 
                                   nodes: List[ProxyNode], 
                                   request: ConversionRequest,
                                   remote_config: Optional[Dict[str, Any]] = None) -> str:
        """生成 Clash 配置"""
        try:
            # 转换节点为 Clash 格式
            clash_proxies = []
            node_names = []
            
            for node in nodes:
                clash_proxy = self._convert_node_to_clash(node, request)
                if clash_proxy:
                    clash_proxies.append(clash_proxy)
                    node_names.append(node.name)
            
            # 生成代理组
            custom_groups = remote_config.get('custom_proxy_group', []) if remote_config else None
            proxy_groups = self.rule_processor.generate_proxy_groups(node_names, custom_groups)
            
            # 生成规则
            custom_rulesets = remote_config.get('ruleset', []) if remote_config else None
            rules = self.rule_processor.generate_rules(custom_rulesets, request.custom_rules)
            
            # 构建完整配置
            clash_config = {
                'port': 7890,
                'socks-port': 7891,
                'allow-lan': False,
                'mode': 'rule',
                'log-level': 'info',
                'external-controller': '127.0.0.1:9090',
                'dns': {
                    'enable': True,
                    'listen': '0.0.0.0:53',
                    'default-nameserver': ['223.5.5.5', '119.29.29.29'],
                    'enhanced-mode': 'fake-ip',
                    'fake-ip-range': '198.18.0.1/16',
                    'fake-ip-filter': [
                        '*.lan',
                        '*.localdomain',
                        '*.example',
                        '*.invalid',
                        '*.localhost',
                        '*.test',
                        '*.local',
                        '*.home.arpa'
                    ],
                    'nameserver': ['https://doh.pub/dns-query', 'https://dns.alidns.com/dns-query']
                },
                'proxies': clash_proxies,
                'proxy-groups': proxy_groups,
                'rules': rules
            }
            
            # 添加模板配置
            if remote_config and 'template' in remote_config:
                template = remote_config['template']
                
                # 应用模板中的全局配置
                for key, value in template.items():
                    if key not in clash_config and key not in ['clash_rule_base']:
                        try:
                            # 尝试解析为适当的类型
                            if value.lower() == 'true':
                                clash_config[key] = True
                            elif value.lower() == 'false':
                                clash_config[key] = False
                            elif value.isdigit():
                                clash_config[key] = int(value)
                            else:
                                clash_config[key] = value
                        except:
                            clash_config[key] = value
            
            return yaml.dump(clash_config, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
        except Exception as e:
            logger.error(f"Failed to generate Clash config: {e}")
            raise
    
    def _convert_node_to_clash(self, node: ProxyNode, request: ConversionRequest) -> Optional[Dict[str, Any]]:
        """将节点转换为 Clash 格式"""
        try:
            base_config = {
                'name': node.name,
                'type': node.type,
                'server': node.server,
                'port': node.port,
            }
            
            # 根据协议类型添加特定配置
            if node.type == 'ss':
                base_config.update({
                    'cipher': node.cipher,
                    'password': node.password,
                    'udp': request.udp and node.udp,
                })
            
            elif node.type == 'ssr':
                base_config.update({
                    'cipher': node.cipher,
                    'password': node.password,
                    'protocol': node.protocol,
                    'protocol-param': node.protocol_param,
                    'obfs': node.obfs,
                    'obfs-param': node.obfs_param,
                    'udp': request.udp and node.udp,
                })
            
            elif node.type == 'vmess':
                base_config.update({
                    'uuid': node.uuid,
                    'alterId': node.alterId or 0,
                    'cipher': node.cipher or 'auto',
                    'udp': request.udp and node.udp,
                })
                
                # 传输层配置
                if node.network and node.network != 'tcp':
                    base_config['network'] = node.network
                    
                    if node.network == 'ws':
                        ws_opts = {}
                        if node.path:
                            ws_opts['path'] = node.path
                        if node.host:
                            ws_opts['headers'] = {'Host': node.host}
                        if ws_opts:
                            base_config['ws-opts'] = ws_opts
                    
                    elif node.network == 'h2':
                        h2_opts = {}
                        if node.path:
                            h2_opts['path'] = node.path
                        if node.host:
                            h2_opts['host'] = [node.host]
                        if h2_opts:
                            base_config['h2-opts'] = h2_opts
                    
                    elif node.network == 'grpc':
                        if node.path:
                            base_config['grpc-opts'] = {
                                'grpc-service-name': node.path
                            }
                
                # TLS 配置
                if node.tls:
                    base_config['tls'] = True
                    tls_opts = {}
                    
                    if node.sni:
                        tls_opts['sni'] = node.sni
                    
                    if request.scv or node.skip_cert_verify:
                        tls_opts['skip-cert-verify'] = True
                    
                    if tls_opts:
                        base_config['tls-opts'] = tls_opts
            
            elif node.type == 'vless':
                base_config.update({
                    'uuid': node.uuid,
                    'udp': request.udp and node.udp,
                })
                
                # 传输层和 TLS 配置（类似 vmess）
                if node.network and node.network != 'tcp':
                    base_config['network'] = node.network
                    # ... (类似 vmess 的传输层配置逻辑)
                
                if node.tls:
                    base_config['tls'] = True
                    # ... (类似 vmess 的 TLS 配置逻辑)
            
            elif node.type == 'trojan':
                base_config.update({
                    'password': node.password,
                    'udp': request.udp and node.udp,
                })
                
                if node.sni:
                    base_config['sni'] = node.sni
                
                if request.scv or node.skip_cert_verify:
                    base_config['skip-cert-verify'] = True
            
            elif node.type in ['hysteria', 'hysteria2']:
                base_config.update({
                    'udp': True,  # Hysteria 基于 UDP
                })
                
                if node.auth_str:
                    base_config['auth-str'] = node.auth_str
                
                if node.up:
                    base_config['up'] = node.up
                
                if node.down:
                    base_config['down'] = node.down
                
                if node.sni:
                    base_config['sni'] = node.sni
                
                if request.scv or node.skip_cert_verify:
                    base_config['skip-cert-verify'] = True
            
            elif node.type == 'tuic':
                base_config.update({
                    'uuid': node.uuid,
                    'password': node.password,
                    'udp': True,  # TUIC 基于 QUIC/UDP
                })
                
                if node.sni:
                    base_config['sni'] = node.sni
                
                if request.scv or node.skip_cert_verify:
                    base_config['skip-cert-verify'] = True
            
            # 通用配置
            if request.tfo:
                base_config['tfo'] = True
            
            return base_config
            
        except Exception as e:
            logger.error(f"Failed to convert node {node.name} to Clash format: {e}")
            return None
    
    def generate_subscription_url(self, config_id: str, base_url: str) -> str:
        """生成订阅链接"""
        return f"{base_url}/sub/{config_id}"
    
    def get_clash_meta_features(self) -> Dict[str, Any]:
        """获取 Clash Meta 特性支持信息"""
        return {
            'supported_protocols': [
                'ss', 'ssr', 'vmess', 'vless', 'trojan', 
                'hysteria', 'hysteria2', 'tuic', 'wireguard'
            ],
            'supported_networks': [
                'tcp', 'udp', 'ws', 'h2', 'grpc', 'quic'
            ],
            'supported_features': [
                'tls', 'xtls', 'reality', 'mux', 'cdn'
            ],
            'proxy_group_types': [
                'select', 'url-test', 'fallback', 'load-balance', 'relay'
            ]
        }