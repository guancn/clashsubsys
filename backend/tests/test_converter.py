"""
订阅转换器测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.converter import SubscriptionConverter
from app.models.schemas import ConversionRequest, ProxyNode, ProxyType


class TestSubscriptionConverter:
    """订阅转换器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.converter = SubscriptionConverter()
    
    @pytest.mark.asyncio
    async def test_convert_subscription_success(self):
        """测试订阅转换成功"""
        # 模拟转换请求
        request = ConversionRequest(
            url=["https://example.com/subscription"],
            target="clash",
            emoji=True,
            udp=True
        )
        
        # 模拟节点数据
        mock_nodes = [
            ProxyNode(
                name="Test Node 1",
                type=ProxyType.SS,
                server="example1.com",
                port=443,
                cipher="aes-256-gcm",
                password="password1"
            ),
            ProxyNode(
                name="Test Node 2", 
                type=ProxyType.VMESS,
                server="example2.com",
                port=443,
                uuid="12345678-1234-1234-1234-123456789012"
            )
        ]
        
        # 模拟网络请求和解析
        with patch.object(self.converter, '_fetch_and_parse_subscription', 
                         return_value=mock_nodes):
            result = await self.converter.convert_subscription(request)
        
        assert result.success == True
        assert result.nodes_count == 2
        assert result.config is not None
        assert "proxies:" in result.config
        assert "proxy-groups:" in result.config
        assert "rules:" in result.config
    
    @pytest.mark.asyncio
    async def test_convert_subscription_empty_nodes(self):
        """测试空节点处理"""
        request = ConversionRequest(
            url=["https://example.com/empty"],
            target="clash"
        )
        
        # 模拟返回空节点列表
        with patch.object(self.converter, '_fetch_and_parse_subscription',
                         return_value=[]):
            result = await self.converter.convert_subscription(request)
        
        assert result.success == False
        assert result.nodes_count == 0
        assert "无法解析任何有效节点" in result.message
    
    @pytest.mark.asyncio
    async def test_node_filtering(self):
        """测试节点过滤功能"""
        # 创建测试节点
        nodes = [
            ProxyNode(name="HK Node", type=ProxyType.SS, server="hk.com", port=443),
            ProxyNode(name="US Node", type=ProxyType.SS, server="us.com", port=443), 
            ProxyNode(name="CN Node", type=ProxyType.SS, server="cn.com", port=443),
            ProxyNode(name="Test Node", type=ProxyType.SS, server="test.com", port=443)
        ]
        
        # 测试包含过滤
        request = ConversionRequest(
            url=["https://example.com/test"],
            include="HK|US"
        )
        
        filtered_nodes = self.converter._apply_node_filters(nodes, request)
        assert len(filtered_nodes) == 2
        assert all("HK" in node.name or "US" in node.name for node in filtered_nodes)
        
        # 测试排除过滤
        request = ConversionRequest(
            url=["https://example.com/test"],
            exclude="Test"
        )
        
        filtered_nodes = self.converter._apply_node_filters(nodes, request)
        assert len(filtered_nodes) == 3
        assert all("Test" not in node.name for node in filtered_nodes)
    
    def test_node_rename(self):
        """测试节点重命名"""
        nodes = [
            ProxyNode(name="HK-001", type=ProxyType.SS, server="hk.com", port=443),
            ProxyNode(name="US-002", type=ProxyType.SS, server="us.com", port=443)
        ]
        
        request = ConversionRequest(
            url=["https://example.com/test"],
            rename="HK-,香港-;US-,美国-",
            emoji=True
        )
        
        renamed_nodes = self.converter._apply_node_rename(nodes, request)
        
        # 检查重命名效果（具体实现取决于重命名逻辑）
        assert len(renamed_nodes) == 2
        # 由于添加了 emoji，节点名称应该包含国旗
        assert any("🇭🇰" in node.name for node in renamed_nodes if "香港" in node.name or "HK" in node.name)
        assert any("🇺🇸" in node.name for node in renamed_nodes if "美国" in node.name or "US" in node.name)
    
    @pytest.mark.asyncio
    async def test_convert_node_to_clash(self):
        """测试节点转换为 Clash 格式"""
        request = ConversionRequest(
            url=["test"],
            udp=True,
            tfo=False,
            scv=False
        )
        
        # 测试 SS 节点转换
        ss_node = ProxyNode(
            name="Test SS",
            type=ProxyType.SS,
            server="example.com",
            port=443,
            cipher="aes-256-gcm",
            password="password",
            udp=True
        )
        
        clash_config = self.converter._convert_node_to_clash(ss_node, request)
        
        assert clash_config is not None
        assert clash_config["name"] == "Test SS"
        assert clash_config["type"] == "ss"
        assert clash_config["server"] == "example.com"
        assert clash_config["port"] == 443
        assert clash_config["cipher"] == "aes-256-gcm"
        assert clash_config["password"] == "password"
        assert clash_config["udp"] == True
        
        # 测试 VMess 节点转换
        vmess_node = ProxyNode(
            name="Test VMess",
            type=ProxyType.VMESS,
            server="example.com",
            port=443,
            uuid="12345678-1234-1234-1234-123456789012",
            network="ws",
            path="/path",
            host="example.com",
            tls=True
        )
        
        clash_config = self.converter._convert_node_to_clash(vmess_node, request)
        
        assert clash_config["type"] == "vmess"
        assert clash_config["uuid"] == "12345678-1234-1234-1234-123456789012"
        assert clash_config["network"] == "ws"
        assert "ws-opts" in clash_config
        assert clash_config["ws-opts"]["path"] == "/path"
    
    @pytest.mark.asyncio 
    async def test_remote_config_processing(self):
        """测试远程配置处理"""
        request = ConversionRequest(
            url=["https://example.com/sub"],
            remote_config="https://example.com/config.ini"
        )
        
        # 模拟远程配置
        mock_remote_config = {
            'custom_proxy_group': [
                '🚀 节点选择`select`[]DIRECT[]♻️ 自动选择[]🔗 故障转移`http://www.gstatic.com/generate_204`300'
            ],
            'ruleset': [
                'RULE-SET,https://example.com/rules/direct.list,DIRECT',
                'RULE-SET,https://example.com/rules/proxy.list,🚀 节点选择'
            ]
        }
        
        mock_nodes = [
            ProxyNode(name="Test", type=ProxyType.SS, server="test.com", port=443)
        ]
        
        with patch.object(self.converter, '_fetch_and_parse_subscription',
                         return_value=mock_nodes), \
             patch.object(self.converter.rule_processor, 'fetch_remote_config',
                         return_value=mock_remote_config):
            
            result = await self.converter.convert_subscription(request)
            
            assert result.success == True
            assert "🚀 节点选择" in result.config
    
    @pytest.mark.asyncio
    async def test_conversion_error_handling(self):
        """测试转换错误处理"""
        request = ConversionRequest(
            url=["https://invalid.url/test"]
        )
        
        # 模拟网络错误
        with patch.object(self.converter, '_fetch_and_parse_subscription',
                         side_effect=Exception("Network error")):
            result = await self.converter.convert_subscription(request)
            
            assert result.success == False
            assert "转换失败" in result.message
    
    def test_clash_meta_features(self):
        """测试 Clash Meta 功能特性"""
        features = self.converter.get_clash_meta_features()
        
        assert 'supported_protocols' in features
        assert 'supported_networks' in features
        assert 'proxy_group_types' in features
        
        # 检查支持的协议
        protocols = features['supported_protocols']
        expected_protocols = ['ss', 'ssr', 'vmess', 'vless', 'trojan', 'hysteria', 'hysteria2']
        for protocol in expected_protocols:
            assert protocol in protocols
        
        # 检查代理组类型
        group_types = features['proxy_group_types']
        expected_types = ['select', 'url-test', 'fallback', 'load-balance']
        for group_type in expected_types:
            assert group_type in group_types
    
    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self):
        """测试多订阅合并"""
        request = ConversionRequest(
            url=[
                "https://example1.com/sub",
                "https://example2.com/sub"
            ]
        )
        
        # 模拟不同订阅的节点
        sub1_nodes = [
            ProxyNode(name="Sub1 Node1", type=ProxyType.SS, server="s1.com", port=443),
            ProxyNode(name="Sub1 Node2", type=ProxyType.SS, server="s2.com", port=443)
        ]
        
        sub2_nodes = [
            ProxyNode(name="Sub2 Node1", type=ProxyType.VMESS, server="v1.com", port=443),
            ProxyNode(name="Sub2 Node2", type=ProxyType.TROJAN, server="t1.com", port=443)
        ]
        
        def mock_fetch(url):
            if "example1.com" in url:
                return sub1_nodes
            elif "example2.com" in url:
                return sub2_nodes
            return []
        
        with patch.object(self.converter, '_fetch_and_parse_subscription',
                         side_effect=mock_fetch):
            result = await self.converter.convert_subscription(request)
            
            assert result.success == True
            assert result.nodes_count == 4  # 2 + 2 个节点
            
            # 检查配置中包含所有节点
            config = result.config
            assert "Sub1 Node1" in config
            assert "Sub1 Node2" in config
            assert "Sub2 Node1" in config
            assert "Sub2 Node2" in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])