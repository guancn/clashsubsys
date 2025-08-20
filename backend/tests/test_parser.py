"""
订阅解析器测试
"""

import pytest
import base64
import json
from app.core.parser import SubscriptionParser
from app.models.schemas import ProxyType


class TestSubscriptionParser:
    """订阅解析器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.parser = SubscriptionParser()
    
    def test_ss_url_parsing(self):
        """测试 Shadowsocks URL 解析"""
        # 标准 SS URL
        ss_url = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example.com:443#Test%20Node"
        nodes = self.parser.parse_subscription(ss_url)
        
        assert len(nodes) == 1
        node = nodes[0]
        assert node.type == ProxyType.SS
        assert node.name == "Test Node"
        assert node.server == "example.com"
        assert node.port == 443
        assert node.cipher == "aes-256-gcm"
        assert node.password == "password"
    
    def test_ssr_url_parsing(self):
        """测试 ShadowsocksR URL 解析"""
        # 模拟 SSR URL (base64 encoded)
        ssr_content = "example.com:443:origin:aes-256-cfb:plain:cGFzc3dvcmQ/?obfsparam=&protoparam=&remarks=VGVzdCBOb2Rl"
        ssr_encoded = base64.b64encode(ssr_content.encode()).decode()
        ssr_url = f"ssr://{ssr_encoded}"
        
        nodes = self.parser.parse_subscription(ssr_url)
        
        assert len(nodes) == 1
        node = nodes[0]
        assert node.type == ProxyType.SSR
        assert node.server == "example.com"
        assert node.port == 443
        assert node.protocol == "origin"
        assert node.cipher == "aes-256-cfb"
        assert node.obfs == "plain"
    
    def test_vmess_url_parsing(self):
        """测试 VMess URL 解析"""
        # VMess 配置
        vmess_config = {
            "v": "2",
            "ps": "Test VMess",
            "add": "example.com",
            "port": "443",
            "id": "12345678-1234-1234-1234-123456789012",
            "aid": "0",
            "net": "ws",
            "type": "none",
            "host": "example.com",
            "path": "/path",
            "tls": "tls"
        }
        
        vmess_encoded = base64.b64encode(json.dumps(vmess_config).encode()).decode()
        vmess_url = f"vmess://{vmess_encoded}"
        
        nodes = self.parser.parse_subscription(vmess_url)
        
        assert len(nodes) == 1
        node = nodes[0]
        assert node.type == ProxyType.VMESS
        assert node.name == "Test VMess"
        assert node.server == "example.com"
        assert node.port == 443
        assert node.uuid == "12345678-1234-1234-1234-123456789012"
        assert node.network == "ws"
        assert node.tls == True
        assert node.host == "example.com"
        assert node.path == "/path"
    
    def test_trojan_url_parsing(self):
        """测试 Trojan URL 解析"""
        trojan_url = "trojan://password@example.com:443?sni=example.com#Test%20Trojan"
        nodes = self.parser.parse_subscription(trojan_url)
        
        assert len(nodes) == 1
        node = nodes[0]
        assert node.type == ProxyType.TROJAN
        assert node.name == "Test Trojan"
        assert node.server == "example.com"
        assert node.port == 443
        assert node.password == "password"
        assert node.sni == "example.com"
    
    def test_base64_subscription(self):
        """测试 Base64 编码的订阅内容"""
        # 创建测试订阅内容
        content = """ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example1.com:443#Node1
ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example2.com:443#Node2"""
        
        encoded_content = base64.b64encode(content.encode()).decode()
        nodes = self.parser.parse_subscription(encoded_content)
        
        assert len(nodes) == 2
        assert nodes[0].name == "Node1"
        assert nodes[1].name == "Node2"
    
    def test_clash_config_parsing(self):
        """测试 Clash 配置解析"""
        clash_config = """
proxies:
  - name: "Test SS"
    type: ss
    server: example.com
    port: 443
    cipher: aes-256-gcm
    password: password
    udp: true
  - name: "Test VMess"
    type: vmess
    server: example.com
    port: 443
    uuid: 12345678-1234-1234-1234-123456789012
    alterId: 0
    cipher: auto
    network: ws
    ws-opts:
      path: /path
      headers:
        Host: example.com
    tls: true
"""
        
        nodes = self.parser.parse_subscription(clash_config)
        
        assert len(nodes) == 2
        
        # 检查 SS 节点
        ss_node = nodes[0]
        assert ss_node.type == ProxyType.SS
        assert ss_node.name == "Test SS"
        assert ss_node.cipher == "aes-256-gcm"
        assert ss_node.udp == True
        
        # 检查 VMess 节点
        vmess_node = nodes[1]
        assert vmess_node.type == ProxyType.VMESS
        assert vmess_node.name == "Test VMess"
        assert vmess_node.network == "ws"
        assert vmess_node.tls == True
        assert vmess_node.path == "/path"
        assert vmess_node.host == "example.com"
    
    def test_invalid_url_handling(self):
        """测试无效 URL 处理"""
        invalid_urls = [
            "invalid://test",
            "ss://invalid-base64",
            "http://example.com",
            "",
            "not-a-url"
        ]
        
        for invalid_url in invalid_urls:
            nodes = self.parser.parse_subscription(invalid_url)
            # 无效 URL 应该返回空列表或被忽略
            assert isinstance(nodes, list)
    
    def test_empty_subscription(self):
        """测试空订阅处理"""
        empty_contents = ["", "\n", "   ", base64.b64encode(b"").decode()]
        
        for content in empty_contents:
            nodes = self.parser.parse_subscription(content)
            assert len(nodes) == 0
    
    def test_mixed_protocol_subscription(self):
        """测试混合协议订阅"""
        mixed_content = """ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example.com:443#SS-Node
trojan://password@example.com:443#Trojan-Node"""
        
        nodes = self.parser.parse_subscription(mixed_content)
        
        assert len(nodes) == 2
        assert any(node.type == ProxyType.SS for node in nodes)
        assert any(node.type == ProxyType.TROJAN for node in nodes)
    
    def test_node_name_encoding(self):
        """测试节点名称编码处理"""
        # 测试中文节点名
        ss_url = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example.com:443#%E6%B5%8B%E8%AF%95%E8%8A%82%E7%82%B9"
        nodes = self.parser.parse_subscription(ss_url)
        
        assert len(nodes) == 1
        assert nodes[0].name == "测试节点"
    
    def test_large_subscription(self):
        """测试大型订阅解析性能"""
        # 生成大量节点
        large_content = []
        for i in range(100):
            url = f"ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example{i}.com:443#Node{i}"
            large_content.append(url)
        
        content = "\n".join(large_content)
        nodes = self.parser.parse_subscription(content)
        
        assert len(nodes) == 100
        # 验证节点名称正确
        for i, node in enumerate(nodes):
            assert node.name == f"Node{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])