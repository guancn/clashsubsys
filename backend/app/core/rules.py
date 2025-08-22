"""
规则处理器 - 处理远程配置和自定义规则
"""

import re
import httpx
import logging
from typing import List, Dict, Any, Optional, Tuple
from configparser import ConfigParser
from io import StringIO

from ..models.schemas import ProxyGroup, Rule

logger = logging.getLogger(__name__)


class RuleProcessor:
    """规则处理器"""
    
    def __init__(self):
        self.default_groups = [
            {
                "name": "🚀 节点选择",
                "type": "select",
                "proxies": ["♻️ 自动选择", "🔗 故障转移", "🔄 负载均衡", "DIRECT"]
            },
            {
                "name": "♻️ 自动选择",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": []
            },
            {
                "name": "🔗 故障转移",
                "type": "fallback",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": []
            },
            {
                "name": "🔄 负载均衡",
                "type": "load-balance",
                "strategy": "consistent-hashing",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": []
            },
            {
                "name": "🐟 漏网之鱼",
                "type": "select",
                "proxies": ["🚀 节点选择", "DIRECT", "REJECT"]
            },
            {
                "name": "📲 电报消息",
                "type": "select",
                "proxies": ["🚀 节点选择", "♻️ 自动选择", "DIRECT"]
            },
            {
                "name": "🎯 全球直连",
                "type": "select",
                "proxies": ["DIRECT", "🚀 节点选择"]
            },
            {
                "name": "🛑 广告拦截",
                "type": "select",
                "proxies": ["REJECT", "DIRECT"]
            },
            {
                "name": "🍃 应用净化",
                "type": "select",
                "proxies": ["REJECT", "DIRECT"]
            }
        ]
        
        self.default_rules = [
            # 管理界面直连
            "DOMAIN,clash.razord.top,DIRECT",
            "DOMAIN,yacd.haishan.me,DIRECT",
            
            # 局域网直连
            "IP-CIDR,192.168.0.0/16,DIRECT",
            "IP-CIDR,10.0.0.0/8,DIRECT", 
            "IP-CIDR,172.16.0.0/12,DIRECT",
            "IP-CIDR,127.0.0.0/8,DIRECT",
            "IP-CIDR,100.64.0.0/10,DIRECT",
            "IP-CIDR,224.0.0.0/4,DIRECT",
            "IP-CIDR6,fe80::/10,DIRECT",
            
            # Apple 服务直连
            "DOMAIN-SUFFIX,apple.com,🎯 全球直连",
            "DOMAIN-SUFFIX,icloud.com,🎯 全球直连",
            "DOMAIN-SUFFIX,apple-cloudkit.com,🎯 全球直连",
            "DOMAIN-SUFFIX,crashlytics.com,🎯 全球直连",
            
            # 常见直连服务
            "DOMAIN-SUFFIX,qq.com,🎯 全球直连",
            "DOMAIN-SUFFIX,taobao.com,🎯 全球直连",
            "DOMAIN-SUFFIX,tmall.com,🎯 全球直连",
            "DOMAIN-SUFFIX,alipay.com,🎯 全球直连",
            "DOMAIN-SUFFIX,baidu.com,🎯 全球直连",
            "DOMAIN-SUFFIX,163.com,🎯 全球直连",
            "DOMAIN-SUFFIX,126.com,🎯 全球直连",
            "DOMAIN-SUFFIX,weibo.com,🎯 全球直连",
            "DOMAIN-SUFFIX,sina.com.cn,🎯 全球直连",
            "DOMAIN-SUFFIX,douban.com,🎯 全球直连",
            "DOMAIN-SUFFIX,zhihu.com,🎯 全球直连",
            "DOMAIN-SUFFIX,bilibili.com,🎯 全球直连",
            
            # Telegram
            "DOMAIN-SUFFIX,t.me,📲 电报消息",
            "DOMAIN-SUFFIX,tdesktop.com,📲 电报消息", 
            "DOMAIN-SUFFIX,telegra.ph,📲 电报消息",
            "DOMAIN-SUFFIX,telegram.org,📲 电报消息",
            "IP-CIDR,91.108.4.0/22,📲 电报消息",
            "IP-CIDR,91.108.8.0/22,📲 电报消息",
            "IP-CIDR,91.108.12.0/22,📲 电报消息",
            "IP-CIDR,91.108.16.0/22,📲 电报消息",
            "IP-CIDR,91.108.56.0/22,📲 电报消息",
            "IP-CIDR,149.154.160.0/20,📲 电报消息",
            
            # 常见代理服务
            "DOMAIN-SUFFIX,google.com,🚀 节点选择",
            "DOMAIN-SUFFIX,youtube.com,🚀 节点选择",
            "DOMAIN-SUFFIX,facebook.com,🚀 节点选择",
            "DOMAIN-SUFFIX,twitter.com,🚀 节点选择",
            "DOMAIN-SUFFIX,instagram.com,🚀 节点选择",
            "DOMAIN-SUFFIX,github.com,🚀 节点选择",
            "DOMAIN-SUFFIX,netflix.com,🚀 节点选择",
            "DOMAIN-SUFFIX,openai.com,🚀 节点选择",
            "DOMAIN-SUFFIX,chatgpt.com,🚀 节点选择",
            
            # 地理位置规则
            "GEOIP,LAN,DIRECT",
            "GEOIP,CN,🎯 全球直连",
            
            # 最终匹配
            "MATCH,🐟 漏网之鱼"
        ]
    
    async def fetch_remote_config(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取远程配置文件
        
        Args:
            url: 远程配置文件 URL
            
        Returns:
            解析后的配置字典
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.text
                
                # 尝试解析 INI 格式
                if self._is_ini_format(content):
                    return self._parse_ini_config(content)
                
                # 尝试解析其他格式（如 YAML）
                # 这里可以扩展支持更多格式
                logger.warning(f"Unsupported config format from {url}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch remote config from {url}: {e}")
            return None
    
    def _is_ini_format(self, content: str) -> bool:
        """检查内容是否为 INI 格式或自定义格式"""
        # 检查是否包含自定义代理组或规则集配置
        return ('custom_proxy_group' in content or 
                'ruleset' in content or 
                'enable_rule_generator' in content or
                ('[' in content and ']' in content and '=' in content))
    
    def _parse_ini_config(self, content: str) -> Dict[str, Any]:
        """
        解析配置文件（支持INI格式和自定义格式）
        
        Args:
            content: 配置内容
            
        Returns:
            解析后的配置字典
        """
        try:
            result = {
                'custom_proxy_group': [],
                'ruleset': [],
                'rename': [],
                'template': {},
            }
            
            # 首先尝试按行解析自定义格式
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 跳过注释和空行
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                # 解析 ruleset 行
                if line.startswith('ruleset='):
                    ruleset_config = line[8:]  # 移除 "ruleset=" 前缀
                    result['ruleset'].append(ruleset_config)
                
                # 解析 custom_proxy_group 行
                elif line.startswith('custom_proxy_group='):
                    group_config = line[19:]  # 移除 "custom_proxy_group=" 前缀
                    result['custom_proxy_group'].append(group_config)
                
                # 解析其他配置项（作为模板配置）
                elif '=' in line and not line.startswith('['):
                    key, value = line.split('=', 1)
                    result['template'][key.strip()] = value.strip()
            
            # 如果自定义格式解析失败，尝试标准INI格式
            if not result['ruleset'] and not result['custom_proxy_group']:
                try:
                    config = ConfigParser()
                    config.read_string(content)
                    
                    # 解析 custom_proxy_group 部分
                    if config.has_section('custom_proxy_group'):
                        for key, value in config.items('custom_proxy_group'):
                            result['custom_proxy_group'].append(value)
                    
                    # 解析 ruleset 部分
                    if config.has_section('ruleset'):
                        for key, value in config.items('ruleset'):
                            result['ruleset'].append(value)
                    
                    # 解析 template 部分
                    if config.has_section('template'):
                        for key, value in config.items('template'):
                            result['template'][key] = value
                    
                    # 解析节点重命名规则
                    if config.has_section('rename_node'):
                        for key, value in config.items('rename_node'):
                            result['rename'].append(f"{key},{value}")
                
                except Exception as ini_error:
                    logger.warning(f"Standard INI parsing also failed: {ini_error}")
            
            logger.info(f"Parsed remote config: {len(result['ruleset'])} rulesets, {len(result['custom_proxy_group'])} proxy groups")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse config: {e}")
            return {}
    
    def generate_proxy_groups(self, 
                            nodes: List[str], 
                            custom_groups: Optional[List[str]] = None,
                            node_filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        生成代理组配置
        
        Args:
            nodes: 节点名称列表
            custom_groups: 自定义代理组配置
            node_filters: 节点过滤规则
            
        Returns:
            代理组配置列表
        """
        try:
            groups = []
            
            # 处理自定义代理组
            if custom_groups:
                for group_config in custom_groups:
                    group = self._parse_custom_group(group_config, nodes, node_filters)
                    if group:
                        groups.append(group)
            else:
                # 使用默认代理组
                for default_group in self.default_groups:
                    group = dict(default_group)
                    
                    # 为需要节点的组添加节点
                    if group['name'] in ['♻️ 自动选择', '🔗 故障转移', '🔄 负载均衡']:
                        group['proxies'] = nodes[:]  # 复制节点列表
                    elif group['name'] == '🚀 节点选择':
                        # 节点选择组包含其他策略组和所有节点
                        strategy_groups = ["♻️ 自动选择", "🔗 故障转移", "🔄 负载均衡", "DIRECT"]
                        group['proxies'] = strategy_groups + nodes
                    
                    groups.append(group)
            
            return groups
            
        except Exception as e:
            logger.error(f"Failed to generate proxy groups: {e}")
            return self.default_groups
    
    def _parse_custom_group(self, 
                          group_config: str, 
                          nodes: List[str],
                          node_filters: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        解析自定义代理组配置
        
        格式: Group_Name`select`[]Group_1[]Group_2[].*HK.*`http://www.gstatic.com/generate_204`300
        """
        try:
            parts = group_config.split('`')
            if len(parts) < 3:
                return None
            
            name = parts[0]
            group_type = parts[1]
            
            # 解析代理列表部分
            proxies_part = parts[2]
            url = parts[3] if len(parts) > 3 else "http://www.gstatic.com/generate_204"
            
            # 解析第4部分，格式可能是 "300,,50" 
            if len(parts) > 4:
                interval_tolerance_part = parts[4]
                # 按逗号分割，可能有多个逗号
                interval_parts = interval_tolerance_part.split(',')
                
                # 第一个是interval
                interval = int(interval_parts[0]) if interval_parts[0].isdigit() else 300
                
                # 最后一个非空部分是tolerance
                tolerance = 50
                for part in reversed(interval_parts):
                    if part.strip() and part.strip().isdigit():
                        tolerance = int(part.strip())
                        break
            else:
                interval = 300
                tolerance = 50
            
            # 解析代理
            proxies = []
            
            # 检查是否为地区匹配格式（以点开头和结尾）
            if proxies_part.startswith('.') and proxies_part.endswith('.'):
                # 地区匹配格式，如 .香港|HK.
                pattern_str = proxies_part[1:-1]  # 移除首尾的点
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    filtered_nodes = [node for node in nodes if pattern.search(node)]
                    proxies.extend(filtered_nodes)
                    logger.info(f"Regional group {name} matched {len(filtered_nodes)} nodes with pattern: {pattern_str}")
                except re.error as e:
                    logger.warning(f"Invalid regex pattern {proxies_part}: {e}")
                    # 如果正则失败，尝试简单的字符串匹配
                    keywords = pattern_str.split('|')
                    for node in nodes:
                        if any(keyword in node for keyword in keywords):
                            proxies.append(node)
            else:
                # 按 [] 分割的传统格式
                proxy_items = re.findall(r'\[(.*?)\]', proxies_part)
                
                for item in proxy_items:
                    if item == 'DIRECT' or item == 'REJECT':
                        proxies.append(item)
                    elif item.startswith('[]'):
                        # 引用其他组
                        proxies.append(item[2:])
                    else:
                        # 节点过滤规则
                        if '.*' in item or item.startswith('^') or item.endswith('$'):
                            # 正则表达式过滤
                            try:
                                pattern = re.compile(item, re.IGNORECASE)
                                filtered_nodes = [node for node in nodes if pattern.search(node)]
                                proxies.extend(filtered_nodes)
                            except re.error as e:
                                logger.warning(f"Invalid regex pattern {item}: {e}")
                        else:
                            # 直接添加
                            if item in nodes:
                                proxies.append(item)
            
            # 如果没有找到节点，添加所有节点
            if not proxies and group_type in ['url-test', 'fallback', 'load-balance']:
                proxies = nodes[:]
            
            group = {
                'name': name,
                'type': group_type,
                'proxies': proxies
            }
            
            # 添加测试相关配置
            if group_type in ['url-test', 'fallback', 'load-balance']:
                group['url'] = url
                group['interval'] = interval
                
                if group_type == 'url-test':
                    group['tolerance'] = tolerance
                elif group_type == 'load-balance':
                    group['strategy'] = 'consistent-hashing'
            
            return group
            
        except Exception as e:
            logger.error(f"Failed to parse custom group: {group_config}, error: {e}")
            return None
    
    def generate_rules(self, 
                      custom_rulesets: Optional[List[str]] = None,
                      custom_rules: Optional[List[str]] = None) -> tuple[List[str], Dict[str, Any]]:
        """
        生成规则列表和rule-providers配置
        
        Args:
            custom_rulesets: 自定义规则集配置
            custom_rules: 自定义规则列表
            
        Returns:
            (规则列表, rule-providers配置字典)
        """
        try:
            rules = []
            rule_providers = {}
            
            # 处理自定义规则集
            if custom_rulesets:
                for ruleset_config in custom_rulesets:
                    parsed_rule = self._parse_custom_ruleset(ruleset_config)
                    if parsed_rule:
                        if parsed_rule.get('rule') == 'MATCH':
                            # 处理FINAL规则
                            rules.append(f"MATCH,{parsed_rule['policy']}")
                        elif parsed_rule.get('url'):
                            # 处理RULE-SET规则
                            rule_name = parsed_rule['name']
                            rule_url = parsed_rule['url']
                            policy = parsed_rule['policy']
                            
                            # 添加到rule-providers
                            rule_providers[rule_name] = {
                                "type": "http",
                                "behavior": "domain" if "domain" in rule_name.lower() else "ipcidr" if "ip" in rule_name.lower() else "classical",
                                "url": rule_url,
                                "path": f"./{rule_name}.yaml",
                                "interval": 86400
                            }
                            
                            # 添加规则
                            rules.append(f"RULE-SET,{rule_name},{policy}")
            
            # 添加自定义规则
            if custom_rules:
                rules.extend(custom_rules)
            
            # 如果没有自定义规则，使用默认规则
            if not rules:
                rules = self.default_rules[:]
            
            logger.info(f"Generated {len(rules)} rules and {len(rule_providers)} rule providers")
            return rules, rule_providers
            
        except Exception as e:
            logger.error(f"Failed to generate rules: {e}")
            return self.default_rules, {}
    
    def _parse_custom_ruleset(self, ruleset_config: str) -> Optional[Dict[str, str]]:
        """
        解析自定义规则集配置
        
        格式: 策略组,https://raw.githubusercontent.com/...,规则名称
        返回: {"policy": "策略组", "url": "规则URL", "name": "规则名称"}
        """
        try:
            # 解析格式：策略组,URL
            parts = ruleset_config.split(',', 1)
            if len(parts) == 2:
                policy = parts[0].strip()
                url = parts[1].strip()
                
                # 处理特殊规则
                if url == "[]FINAL":
                    return {"policy": policy, "rule": "MATCH", "name": "FINAL"}
                
                # 从URL生成规则名称
                if url.startswith('http'):
                    rule_name = url.split('/')[-1].replace('.list', '').replace('.txt', '').replace('.yaml', '')
                    return {
                        "policy": policy,
                        "url": url,
                        "name": rule_name,
                        "rule": f"RULE-SET,{rule_name}"
                    }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse custom ruleset: {ruleset_config}, error: {e}")
            return None
    
    def apply_node_filters(self, 
                          nodes: List[str],
                          include_pattern: Optional[str] = None,
                          exclude_pattern: Optional[str] = None) -> List[str]:
        """
        应用节点过滤规则
        
        Args:
            nodes: 原始节点列表
            include_pattern: 包含规则（正则表达式）
            exclude_pattern: 排除规则（正则表达式）
            
        Returns:
            过滤后的节点列表
        """
        try:
            filtered_nodes = nodes[:]
            
            # 应用包含规则
            if include_pattern:
                pattern = re.compile(include_pattern, re.IGNORECASE)
                filtered_nodes = [node for node in filtered_nodes if pattern.search(node)]
            
            # 应用排除规则
            if exclude_pattern:
                pattern = re.compile(exclude_pattern, re.IGNORECASE)
                filtered_nodes = [node for node in filtered_nodes if not pattern.search(node)]
            
            return filtered_nodes
            
        except Exception as e:
            logger.error(f"Failed to apply node filters: {e}")
            return nodes
    
    def apply_node_rename(self, 
                         nodes: List[str], 
                         rename_rules: Optional[List[str]] = None) -> Dict[str, str]:
        """
        应用节点重命名规则
        
        Args:
            nodes: 节点名称列表
            rename_rules: 重命名规则列表，格式: "old_pattern,new_pattern"
            
        Returns:
            重命名映射字典 {old_name: new_name}
        """
        try:
            rename_map = {}
            
            if not rename_rules:
                return {node: node for node in nodes}
            
            for node in nodes:
                new_name = node
                
                for rule in rename_rules:
                    try:
                        parts = rule.split(',', 1)
                        if len(parts) == 2:
                            pattern, replacement = parts
                            new_name = re.sub(pattern, replacement, new_name, flags=re.IGNORECASE)
                    except Exception as e:
                        logger.warning(f"Failed to apply rename rule {rule}: {e}")
                        continue
                
                rename_map[node] = new_name
            
            return rename_map
            
        except Exception as e:
            logger.error(f"Failed to apply node rename: {e}")
            return {node: node for node in nodes}
    
    def add_emoji_flags(self, node_name: str) -> str:
        """
        为节点名称添加国旗 Emoji
        
        Args:
            node_name: 原始节点名称
            
        Returns:
            添加 Emoji 后的节点名称
        """
        flag_map = {
            # 中国地区
            r'港|hk|hong.?kong': '🇭🇰',
            r'台|tw|taiwan': '🇹🇼',
            r'澳门|macao': '🇲🇴',
            r'中国|china|cn': '🇨🇳',
            
            # 亚洲
            r'日本|jp|japan': '🇯🇵',
            r'韩国|kr|korea': '🇰🇷',
            r'新加坡|sg|singapore': '🇸🇬',
            r'马来西亚|my|malaysia': '🇲🇾',
            r'泰国|th|thailand': '🇹🇭',
            r'印度|in|india': '🇮🇳',
            r'菲律宾|ph|philippines': '🇵🇭',
            r'印尼|id|indonesia': '🇮🇩',
            r'越南|vn|vietnam': '🇻🇳',
            
            # 欧洲
            r'英国|uk|britain|united.?kingdom': '🇬🇧',
            r'法国|fr|france': '🇫🇷',
            r'德国|de|germany': '🇩🇪',
            r'荷兰|nl|netherlands': '🇳🇱',
            r'意大利|it|italy': '🇮🇹',
            r'西班牙|es|spain': '🇪🇸',
            r'俄罗斯|ru|russia': '🇷🇺',
            r'瑞士|ch|switzerland': '🇨🇭',
            r'瑞典|se|sweden': '🇸🇪',
            r'挪威|no|norway': '🇳🇴',
            r'芬兰|fi|finland': '🇫🇮',
            r'丹麦|dk|denmark': '🇩🇰',
            r'波兰|pl|poland': '🇵🇱',
            r'土耳其|tr|turkey': '🇹🇷',
            
            # 美洲
            r'美国|us|united.?states|america': '🇺🇸',
            r'加拿大|ca|canada': '🇨🇦',
            r'墨西哥|mx|mexico': '🇲🇽',
            r'巴西|br|brazil': '🇧🇷',
            r'阿根廷|ar|argentina': '🇦🇷',
            
            # 大洋洲
            r'澳大利亚|au|australia': '🇦🇺',
            r'新西兰|nz|new.?zealand': '🇳🇿',
            
            # 非洲
            r'南非|za|south.?africa': '🇿🇦',
            r'埃及|eg|egypt': '🇪🇬',
            
            # 中东
            r'以色列|il|israel': '🇮🇱',
            r'阿联酋|ae|uae': '🇦🇪',
        }
        
        for pattern, flag in flag_map.items():
            if re.search(pattern, node_name, re.IGNORECASE):
                # 如果节点名称中还没有这个国旗，则添加
                if flag not in node_name:
                    return f"{flag} {node_name}"
                return node_name
        
        return node_name