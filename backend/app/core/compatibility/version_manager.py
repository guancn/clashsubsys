"""
版本管理器
处理协议版本兼容性和向后兼容性问题
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass
from packaging import version as pkg_version

from ..protocol_parser_interface import ProtocolVersion
from ...models.schemas import ProxyNode, ProxyType


class CompatibilityLevel(str, Enum):
    """兼容性级别"""
    FULL = "full"           # 完全兼容
    PARTIAL = "partial"     # 部分兼容，有功能缺失
    DEGRADED = "degraded"   # 降级兼容，功能受限
    INCOMPATIBLE = "incompatible"  # 不兼容


@dataclass
class VersionInfo:
    """版本信息"""
    protocol: str
    version: str
    features: List[str]
    deprecated_features: List[str] = None
    removed_features: List[str] = None
    migration_notes: str = ""


@dataclass
class CompatibilityRule:
    """兼容性规则"""
    source_version: str
    target_version: str
    compatibility_level: CompatibilityLevel
    field_mappings: Dict[str, str] = None
    transformation_func: Optional[Callable] = None
    warnings: List[str] = None


class VersionManager:
    """版本管理器"""

    def __init__(self):
        self.logger = logging.getLogger("compatibility.version")
        
        # 协议版本信息
        self.protocol_versions = self._initialize_protocol_versions()
        
        # 兼容性规则
        self.compatibility_rules = self._initialize_compatibility_rules()
        
        # 字段映射规则
        self.field_mappings = self._initialize_field_mappings()

    def _initialize_protocol_versions(self) -> Dict[str, Dict[str, VersionInfo]]:
        """初始化协议版本信息"""
        return {
            "hysteria": {
                "1": VersionInfo(
                    protocol="hysteria",
                    version="1",
                    features=["auth", "obfs", "fast_open", "lazy_start"],
                    deprecated_features=["lazy_start"],
                    migration_notes="Hysteria v1 已被 v2 取代，建议升级"
                ),
                "2": VersionInfo(
                    protocol="hysteria",
                    version="2",
                    features=["auth", "obfs", "brutal", "salamander"],
                    removed_features=["lazy_start", "fast_open"],
                    migration_notes="Hysteria v2 使用新的认证和混淆机制"
                )
            },
            "tuic": {
                "4": VersionInfo(
                    protocol="tuic",
                    version="4",
                    features=["token", "congestion_control", "disable_sni"],
                    deprecated_features=["token"],
                    migration_notes="TUIC v4 使用 token 认证"
                ),
                "5": VersionInfo(
                    protocol="tuic",
                    version="5",
                    features=["uuid", "password", "congestion_control", "udp_relay_mode", "reduce_rtt"],
                    removed_features=["token", "disable_sni"],
                    migration_notes="TUIC v5 改用 UUID+Password 认证模式"
                )
            },
            "vless": {
                "1": VersionInfo(
                    protocol="vless",
                    version="1",
                    features=["uuid", "flow", "encryption", "transport", "tls", "xtls", "reality"],
                    migration_notes="VLESS 是 VMess 的轻量级版本"
                )
            },
            "wireguard": {
                "1": VersionInfo(
                    protocol="wireguard",
                    version="1",
                    features=["private_key", "public_key", "preshared_key", "allowed_ips", "endpoint"],
                    migration_notes="WireGuard 是现代 VPN 协议"
                )
            }
        }

    def _initialize_compatibility_rules(self) -> Dict[str, List[CompatibilityRule]]:
        """初始化兼容性规则"""
        return {
            "hysteria": [
                CompatibilityRule(
                    source_version="1",
                    target_version="2",
                    compatibility_level=CompatibilityLevel.PARTIAL,
                    field_mappings={
                        "auth_str": "auth",
                        "obfs": "obfs",
                        "up": "up_mbps",
                        "down": "down_mbps"
                    },
                    warnings=["fast_open 和 lazy_start 功能在 v2 中不支持"]
                ),
                CompatibilityRule(
                    source_version="2",
                    target_version="1",
                    compatibility_level=CompatibilityLevel.DEGRADED,
                    field_mappings={
                        "auth": "auth_str",
                        "up_mbps": "up",
                        "down_mbps": "down"
                    },
                    warnings=["brutal 和 salamander 混淆在 v1 中不支持"]
                )
            ],
            "tuic": [
                CompatibilityRule(
                    source_version="4",
                    target_version="5",
                    compatibility_level=CompatibilityLevel.PARTIAL,
                    field_mappings={
                        "token": "uuid",  # token 映射到 uuid
                        "disable_sni": None,  # 移除该字段
                    },
                    warnings=["需要同时设置 password 字段", "disable_sni 功能已移除"]
                ),
                CompatibilityRule(
                    source_version="5",
                    target_version="4",
                    compatibility_level=CompatibilityLevel.DEGRADED,
                    field_mappings={
                        "uuid": "token",
                        "password": None,  # v4 不支持独立密码
                        "udp_relay_mode": None,
                        "reduce_rtt": None
                    },
                    warnings=["password、udp_relay_mode、reduce_rtt 功能在 v4 中不支持"]
                )
            ]
        }

    def _initialize_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """初始化字段映射"""
        return {
            "clash_to_singbox": {
                "server": "server",
                "port": "server_port",
                "cipher": "method",
                "uuid": "uuid",
                "alterId": "alter_id",
                "skip-cert-verify": "tls.insecure",
                "sni": "tls.server_name",
                "network": "transport.type",
                "ws-opts.path": "transport.path",
                "ws-opts.headers.Host": "transport.headers.Host",
                "h2-opts.path": "transport.path",
                "h2-opts.host": "transport.host",
                "grpc-opts.grpc-service-name": "transport.service_name"
            },
            "singbox_to_clash": {
                "server": "server",
                "server_port": "port",
                "method": "cipher",
                "uuid": "uuid",
                "alter_id": "alterId",
                "tls.insecure": "skip-cert-verify",
                "tls.server_name": "sni",
                "transport.type": "network",
                "transport.path": "ws-opts.path",
                "transport.headers.Host": "ws-opts.headers.Host",
                "transport.host": "h2-opts.host",
                "transport.service_name": "grpc-opts.grpc-service-name"
            }
        }

    def get_protocol_version(self, protocol: str, version: str) -> Optional[VersionInfo]:
        """获取协议版本信息"""
        protocol_versions = self.protocol_versions.get(protocol.lower(), {})
        return protocol_versions.get(version)

    def check_compatibility(self, 
                          protocol: str,
                          source_version: str, 
                          target_version: str) -> CompatibilityRule:
        """检查版本兼容性"""
        protocol_rules = self.compatibility_rules.get(protocol.lower(), [])
        
        for rule in protocol_rules:
            if rule.source_version == source_version and rule.target_version == target_version:
                return rule
        
        # 如果没有找到明确的规则，进行版本比较
        try:
            source_ver = pkg_version.parse(source_version)
            target_ver = pkg_version.parse(target_version)
            
            if source_ver == target_ver:
                return CompatibilityRule(
                    source_version=source_version,
                    target_version=target_version,
                    compatibility_level=CompatibilityLevel.FULL
                )
            elif source_ver < target_ver:
                # 从低版本到高版本，通常是部分兼容
                return CompatibilityRule(
                    source_version=source_version,
                    target_version=target_version,
                    compatibility_level=CompatibilityLevel.PARTIAL,
                    warnings=[f"从 v{source_version} 升级到 v{target_version} 可能有功能变更"]
                )
            else:
                # 从高版本到低版本，通常是降级兼容
                return CompatibilityRule(
                    source_version=source_version,
                    target_version=target_version,
                    compatibility_level=CompatibilityLevel.DEGRADED,
                    warnings=[f"从 v{source_version} 降级到 v{target_version} 会丢失部分功能"]
                )
        except:
            # 无法解析版本号，标记为不兼容
            return CompatibilityRule(
                source_version=source_version,
                target_version=target_version,
                compatibility_level=CompatibilityLevel.INCOMPATIBLE,
                warnings=[f"无法确定 v{source_version} 和 v{target_version} 的兼容性"]
            )

    def migrate_config(self, 
                      config: Dict[str, Any], 
                      source_format: str, 
                      target_format: str) -> tuple[Dict[str, Any], List[str]]:
        """迁移配置格式"""
        mapping_key = f"{source_format}_to_{target_format}"
        field_mapping = self.field_mappings.get(mapping_key, {})
        
        if not field_mapping:
            self.logger.warning(f"未找到 {source_format} 到 {target_format} 的映射规则")
            return config, [f"未找到格式映射规则: {source_format} -> {target_format}"]
        
        migrated_config = {}
        warnings = []
        
        for source_field, target_field in field_mapping.items():
            if target_field is None:
                # 字段已被移除
                if source_field in config:
                    warnings.append(f"字段 '{source_field}' 在目标格式中不支持，已忽略")
                continue
            
            # 处理嵌套字段
            source_value = self._get_nested_value(config, source_field)
            if source_value is not None:
                self._set_nested_value(migrated_config, target_field, source_value)
        
        # 复制未映射的字段
        for key, value in config.items():
            if key not in field_mapping and key not in migrated_config:
                migrated_config[key] = value
        
        return migrated_config, warnings

    def migrate_node_version(self, 
                           node: ProxyNode,
                           target_version: str) -> tuple[ProxyNode, List[str]]:
        """迁移节点版本"""
        if not hasattr(node, 'extra_config') or not node.extra_config:
            return node, []
        
        current_version = node.extra_config.get('version', '1')
        protocol = node.type.lower() if hasattr(node.type, 'lower') else str(node.type).lower()
        
        # 检查兼容性
        compatibility = self.check_compatibility(protocol, current_version, target_version)
        
        if compatibility.compatibility_level == CompatibilityLevel.INCOMPATIBLE:
            return node, [f"无法将 {protocol} v{current_version} 迁移到 v{target_version}"]
        
        # 应用字段映射
        warnings = compatibility.warnings or []
        migrated_node = self._apply_node_migration(node, compatibility)
        
        # 更新版本信息
        if hasattr(migrated_node, 'extra_config'):
            migrated_node.extra_config['version'] = target_version
        
        return migrated_node, warnings

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字段值"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """设置嵌套字段值"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value

    def _apply_node_migration(self, node: ProxyNode, rule: CompatibilityRule) -> ProxyNode:
        """应用节点迁移规则"""
        if not rule.field_mappings:
            return node
        
        # 创建节点副本
        migrated_node = ProxyNode(**node.dict())
        
        # 应用字段映射
        for source_field, target_field in rule.field_mappings.items():
            if target_field is None:
                # 移除字段
                if hasattr(migrated_node, source_field):
                    delattr(migrated_node, source_field)
                continue
            
            # 映射字段
            if hasattr(node, source_field):
                source_value = getattr(node, source_field)
                if hasattr(migrated_node, target_field):
                    setattr(migrated_node, target_field, source_value)
        
        # 应用转换函数
        if rule.transformation_func:
            try:
                migrated_node = rule.transformation_func(migrated_node)
            except Exception as e:
                self.logger.error(f"应用转换函数失败: {e}")
        
        return migrated_node

    def get_supported_versions(self, protocol: str) -> List[str]:
        """获取协议支持的版本列表"""
        protocol_versions = self.protocol_versions.get(protocol.lower(), {})
        return sorted(protocol_versions.keys(), key=lambda x: pkg_version.parse(x) if x.replace('.', '').isdigit() else x)

    def get_latest_version(self, protocol: str) -> Optional[str]:
        """获取协议的最新版本"""
        versions = self.get_supported_versions(protocol)
        if not versions:
            return None
        
        try:
            # 尝试按版本号排序
            sorted_versions = sorted(versions, key=pkg_version.parse, reverse=True)
            return sorted_versions[0]
        except:
            # 如果无法解析版本号，返回最后一个
            return versions[-1]

    def recommend_migration_path(self, 
                                protocol: str,
                                current_version: str,
                                target_version: str) -> List[str]:
        """推荐迁移路径"""
        if current_version == target_version:
            return [current_version]
        
        try:
            current_ver = pkg_version.parse(current_version)
            target_ver = pkg_version.parse(target_version)
            
            # 获取所有支持的版本
            all_versions = self.get_supported_versions(protocol)
            
            if current_ver < target_ver:
                # 升级路径：逐步升级
                path = [current_version]
                for ver_str in all_versions:
                    try:
                        ver = pkg_version.parse(ver_str)
                        if current_ver < ver <= target_ver:
                            path.append(ver_str)
                    except:
                        continue
                return path
            else:
                # 降级路径：直接降级
                return [current_version, target_version]
        except:
            # 无法解析版本号，直接迁移
            return [current_version, target_version]

    def validate_config_compatibility(self, 
                                    config: Dict[str, Any],
                                    format_type: str,
                                    protocol: str,
                                    version: str) -> List[str]:
        """验证配置兼容性"""
        warnings = []
        
        # 获取协议版本信息
        version_info = self.get_protocol_version(protocol, version)
        if not version_info:
            warnings.append(f"未知的协议版本: {protocol} v{version}")
            return warnings
        
        # 检查必需字段
        required_fields = self._get_required_fields(protocol, version, format_type)
        for field in required_fields:
            if not self._get_nested_value(config, field):
                warnings.append(f"缺少必需字段: {field}")
        
        # 检查已弃用字段
        if version_info.deprecated_features:
            for field in version_info.deprecated_features:
                if self._get_nested_value(config, field):
                    warnings.append(f"字段 '{field}' 已弃用，建议移除")
        
        # 检查已移除字段
        if version_info.removed_features:
            for field in version_info.removed_features:
                if self._get_nested_value(config, field):
                    warnings.append(f"字段 '{field}' 在此版本中不再支持")
        
        return warnings

    def _get_required_fields(self, protocol: str, version: str, format_type: str) -> List[str]:
        """获取必需字段列表"""
        # 基础必需字段
        base_fields = ["name", "server", "port"]
        
        # 协议特定字段
        protocol_fields = {
            "hysteria": ["auth", "up_mbps", "down_mbps"],
            "hysteria2": ["auth", "up_mbps", "down_mbps"],
            "tuic": ["uuid", "password"] if version == "5" else ["token"],
            "vless": ["uuid"],
            "vmess": ["uuid"],
            "trojan": ["password"],
            "ss": ["method", "password"],
            "ssr": ["method", "password", "protocol", "obfs"],
            "wireguard": ["private_key", "peer_public_key"]
        }
        
        fields = base_fields + protocol_fields.get(protocol, [])
        
        # 根据格式调整字段名
        if format_type == "sing-box":
            # sing-box 使用不同的字段名
            field_mapping = self.field_mappings.get("clash_to_singbox", {})
            fields = [field_mapping.get(field, field) for field in fields]
        
        return fields


# 全局版本管理器实例
global_version_manager = VersionManager()


def get_version_manager() -> VersionManager:
    """获取全局版本管理器"""
    return global_version_manager