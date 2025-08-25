"""
新协议支持的测试用例
验证 Hysteria2、TUIC v5、VLESS Reality、WireGuard 协议的解析和配置生成
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.protocol_parser_interface import protocol_registry, ParseResult, ConfigGenerationResult
from core.parsers.hysteria2_parser import register_hysteria2_support
from core.parsers.tuic_parser import register_tuic_support
from core.parsers.vless_reality_parser import register_vless_reality_support
from core.parsers.wireguard_parser import register_wireguard_support
from core.generators.singbox_generator import register_singbox_generator
from models.schemas import ProxyNode, ProxyType


class TestProtocolParserRegistry:
    """协议解析器注册表测试"""

    def setup_method(self):
        """测试前的设置"""
        # 注册所有解析器
        register_hysteria2_support()
        register_tuic_support()
        register_vless_reality_support()
        register_wireguard_support()
        register_singbox_generator()

    def test_parser_registration(self):
        """测试解析器注册"""
        supported_protocols = protocol_registry.get_supported_protocols()
        
        assert "hysteria2" in supported_protocols
        assert "tuic" in supported_protocols
        assert "vless-reality" in supported_protocols
        assert "wireguard" in supported_protocols

    def test_generator_registration(self):
        """测试生成器注册"""
        supported_formats = protocol_registry.get_supported_formats()
        
        assert "hysteria2" in supported_formats
        assert "tuic" in supported_formats
        assert "vless-reality" in supported_formats
        assert "wireguard" in supported_formats
        assert "sing-box" in supported_formats

    def test_health_check(self):
        """测试健康检查"""
        health = protocol_registry.health_check()
        
        assert health['parsers_count'] > 0
        assert health['generators_count'] > 0
        assert len(health['supported_schemes']) > 0
        assert len(health['supported_formats']) > 0


class TestHysteria2Parser:
    """Hysteria2 解析器测试"""

    def setup_method(self):
        register_hysteria2_support()
        self.parser = protocol_registry.get_parser("hysteria2://example.com")

    def test_parse_hysteria2_url_basic(self):
        """测试基础 Hysteria2 URL 解析"""
        url = "hysteria2://password@example.com:443?up=100&down=200&sni=example.com#TestNode"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.name == "TestNode"
        assert result.node.type == ProxyType.HYSTERIA2
        assert result.node.server == "example.com"
        assert result.node.port == 443
        assert result.node.auth_str == "password"
        assert result.node.up == "100"
        assert result.node.down == "200"
        assert result.node.sni == "example.com"
        assert result.node.udp == True

    def test_parse_hysteria2_url_with_obfs(self):
        """测试带混淆的 Hysteria2 URL 解析"""
        url = "hysteria2://auth123@server.com:443?obfs=salamander&obfs-password=secret#Node"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.auth_str == "auth123"
        assert hasattr(result.node, 'extra_config')
        assert 'obfs' in result.node.extra_config
        assert result.node.extra_config['obfs']['type'] == 'salamander'
        assert result.node.extra_config['obfs']['password'] == 'secret'

    def test_parse_hysteria2_clash_config(self):
        """测试 Clash 格式 Hysteria2 配置解析"""
        config = {
            'name': 'Hysteria2-Test',
            'type': 'hysteria2',
            'server': 'example.com',
            'port': 443,
            'auth': 'password123',
            'up': '100 Mbps',
            'down': '200 Mbps',
            'sni': 'example.com',
            'skip-cert-verify': False
        }
        
        result = self.parser.parse_clash_config(config)
        
        assert result.success
        assert result.node.name == 'Hysteria2-Test'
        assert result.node.auth_str == 'password123'
        assert result.node.up == '100 Mbps'

    def test_invalid_hysteria2_url(self):
        """测试无效的 Hysteria2 URL"""
        url = "invalid://example.com"
        
        result = self.parser.parse_url(url)
        
        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_hysteria2_config_generation(self):
        """测试 Hysteria2 配置生成"""
        node = ProxyNode(
            name="Test-Hysteria2",
            type=ProxyType.HYSTERIA2,
            server="example.com",
            port=443,
            auth_str="password123",
            up="100",
            down="200",
            sni="example.com",
            udp=True
        )
        
        generator = protocol_registry.get_generator("hysteria2")
        result = generator.generate_proxy_config(
            node, 
            ConfigFormat.CLASH_META,
            options={'udp': True}
        )
        
        assert result.success
        assert result.config['type'] == 'hysteria2'
        assert result.config['auth'] == 'password123'


class TestTuicParser:
    """TUIC 解析器测试"""

    def setup_method(self):
        register_tuic_support()
        self.parser = protocol_registry.get_parser("tuic://example.com")

    def test_parse_tuic_v5_url(self):
        """测试 TUIC v5 URL 解析"""
        url = "tuic://550e8400-e29b-41d4-a716-446655440000:password@example.com:443?sni=example.com&congestion_control=bbr#TUIC-Test"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert result.node.password == "password"
        assert result.node.sni == "example.com"
        assert hasattr(result.node, 'extra_config')
        assert result.node.extra_config['congestion_control'] == 'bbr'
        assert result.node.extra_config['version'] == 'v5'

    def test_parse_tuic_v4_clash_config(self):
        """测试 TUIC v4 Clash 配置解析"""
        config = {
            'name': 'TUIC-v4',
            'type': 'tuic',
            'server': 'example.com',
            'port': 443,
            'token': 'test-token',
            'version': 4,
            'congestion-control': 'cubic'
        }
        
        result = self.parser.parse_clash_config(config)
        
        assert result.success
        assert result.node.uuid == 'test-token'
        assert result.node.extra_config['version'] == 'v4'

    def test_tuic_version_detection(self):
        """测试 TUIC 版本检测"""
        v5_url = "tuic5://uuid:pass@host:443"
        v4_url = "tuic://uuid:pass@host:443?version=4"
        
        assert self.parser.detect_version(v5_url).value == 'v5'
        assert self.parser.detect_version(v4_url).value == 'v4'

    def test_invalid_uuid_format(self):
        """测试无效的 UUID 格式"""
        url = "tuic://invalid-uuid:password@example.com:443"
        
        result = self.parser.parse_url(url)
        
        assert not result.success
        assert "无效的UUID格式" in result.error


class TestVlessRealityParser:
    """VLESS Reality 解析器测试"""

    def setup_method(self):
        register_vless_reality_support()
        self.parser = protocol_registry.get_parser("vless://example.com")

    def test_parse_vless_reality_url(self):
        """测试 VLESS Reality URL 解析"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=tcp&security=reality&pbk=publickey123&fp=chrome&sni=example.com&sid=shortid#VLESS-Reality"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert result.node.tls == True
        assert result.node.network == "tcp"
        assert hasattr(result.node, 'extra_config')
        assert 'reality' in result.node.extra_config
        
        reality_config = result.node.extra_config['reality']
        assert reality_config['public_key'] == 'publickey123'
        assert reality_config['fingerprint'] == 'chrome'
        assert reality_config['short_id'] == 'shortid'

    def test_parse_vless_reality_websocket(self):
        """测试 VLESS Reality WebSocket 传输"""
        url = "vless://uuid@host:443?type=ws&path=/ws&host=example.com&security=reality&pbk=key123#Test"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.network == "ws"
        assert result.node.path == "/ws"
        assert result.node.host == "example.com"
        assert 'websocket' in result.node.extra_config

    def test_parse_vless_reality_clash_config(self):
        """测试 Clash 格式 VLESS Reality 配置"""
        config = {
            'name': 'VLESS-Reality',
            'type': 'vless',
            'server': 'example.com',
            'port': 443,
            'uuid': '550e8400-e29b-41d4-a716-446655440000',
            'network': 'tcp',
            'reality-opts': {
                'public-key': 'publickey123',
                'short-id': 'sid123'
            },
            'servername': 'example.com',
            'client-fingerprint': 'chrome'
        }
        
        result = self.parser.parse_clash_config(config)
        
        assert result.success
        assert 'reality' in result.node.extra_config
        assert result.node.extra_config['reality']['public_key'] == 'publickey123'

    def test_missing_reality_config(self):
        """测试缺少 Reality 配置的情况"""
        url = "vless://uuid@host:443?type=tcp&security=tls#Test"  # 不是 Reality
        
        result = self.parser.parse_url(url)
        
        assert not result.success
        assert "不是Reality协议配置" in result.error


class TestWireGuardParser:
    """WireGuard 解析器测试"""

    def setup_method(self):
        register_wireguard_support()
        self.parser = protocol_registry.get_parser("wg://example.com")

    def test_parse_wireguard_url(self):
        """测试 WireGuard URL 解析"""
        url = "wg://privatekey123@example.com:51820/?publickey=pubkey123&allowed_ips=0.0.0.0/0&dns=1.1.1.1#WG-Test"
        
        result = self.parser.parse_url(url)
        
        assert result.success
        assert result.node.name == "WG-Test"
        assert result.node.server == "example.com"
        assert result.node.port == 51820
        assert result.node.udp == True
        
        wg_config = result.node.extra_config['wireguard']
        assert wg_config['private_key'] == 'privatekey123'
        assert wg_config['peer_public_key'] == 'pubkey123'
        assert '0.0.0.0/0' in wg_config['allowed_ips']
        assert '1.1.1.1' in wg_config['dns']

    def test_parse_wireguard_config_file(self):
        """测试 WireGuard 配置文件格式解析"""
        config_text = """
[Interface]
PrivateKey = privatekey123
Address = 10.0.0.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = pubkey123
Endpoint = example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        
        result = self.parser.parse_wg_config(config_text)
        
        assert result.success
        assert result.node.server == "example.com"
        assert result.node.port == 51820
        
        wg_config = result.node.extra_config['wireguard']
        assert wg_config['private_key'] == 'privatekey123'
        assert wg_config['peer_public_key'] == 'pubkey123'
        assert wg_config['persistent_keepalive'] == 25

    def test_invalid_wireguard_key(self):
        """测试无效的 WireGuard 密钥"""
        # WireGuard 密钥应该是 44 字符的 Base64
        url = "wg://invalidkey@example.com:51820/?publickey=alsoinvalid#Test"
        
        result = self.parser.parse_url(url)
        
        assert not result.success
        assert "无效的私钥格式" in result.error


class TestSingBoxGenerator:
    """sing-box 配置生成器测试"""

    def setup_method(self):
        register_singbox_generator()
        self.generator = protocol_registry.get_generator("sing-box")

    def test_generate_hysteria2_singbox_config(self):
        """测试生成 Hysteria2 的 sing-box 配置"""
        node = ProxyNode(
            name="Hysteria2-Test",
            type=ProxyType.HYSTERIA2,
            server="example.com",
            port=443,
            auth_str="password123",
            up="100",
            down="200",
            udp=True
        )
        
        result = self.generator.generate_proxy_config(
            node,
            ConfigFormat.SING_BOX
        )
        
        assert result.success
        config = result.config
        assert config['type'] == 'hysteria2'
        assert config['tag'] == 'Hysteria2-Test'
        assert config['auth'] == 'password123'
        assert config['up_mbps'] == 100
        assert config['down_mbps'] == 200

    def test_generate_full_singbox_config(self):
        """测试生成完整的 sing-box 配置"""
        nodes = [
            ProxyNode(
                name="Node1",
                type=ProxyType.HYSTERIA2,
                server="server1.com",
                port=443,
                auth_str="pass1",
                udp=True
            ),
            ProxyNode(
                name="Node2",
                type=ProxyType.TUIC,
                server="server2.com",
                port=443,
                uuid="550e8400-e29b-41d4-a716-446655440000",
                password="pass2",
                udp=True
            )
        ]
        
        result = self.generator.generate_full_config(nodes)
        
        assert result.success
        config = result.config
        assert 'outbounds' in config
        assert 'inbounds' in config
        assert 'route' in config
        assert len(config['outbounds']) > len(nodes)  # 包含选择器和直连


class TestPerformanceOptimization:
    """性能优化测试"""

    def setup_method(self):
        from ..core.performance.cache_manager import get_cache_manager
        from ..core.performance.optimizer import get_performance_optimizer
        
        self.cache_manager = get_cache_manager()
        self.optimizer = get_performance_optimizer()

    def test_cache_functionality(self):
        """测试缓存功能"""
        # 设置缓存
        self.cache_manager.set('test', 'key1', {'data': 'test'})
        
        # 获取缓存
        cached_data = self.cache_manager.get('test', 'key1')
        assert cached_data == {'data': 'test'}
        
        # 缓存统计
        stats = self.cache_manager.get_stats()
        assert stats['size'] > 0

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """测试性能监控"""
        async with self.optimizer.performance_context():
            # 模拟一些处理
            await asyncio.sleep(0.1)
        
        stats = self.optimizer.get_optimization_stats()
        assert 'cache' in stats
        assert 'system' in stats

    def test_batch_processing(self):
        """测试批处理功能"""
        processor = self.optimizer.batch_processor
        assert processor.batch_size > 0
        assert processor.max_wait_time > 0


class TestCompatibilityAndRecovery:
    """兼容性和恢复机制测试"""

    def setup_method(self):
        from ..core.compatibility.version_manager import get_version_manager
        from ..core.compatibility.error_recovery import get_error_recovery_manager
        
        self.version_manager = get_version_manager()
        self.recovery_manager = get_error_recovery_manager()

    def test_version_compatibility_check(self):
        """测试版本兼容性检查"""
        rule = self.version_manager.check_compatibility('tuic', '4', '5')
        
        assert rule.compatibility_level in [
            CompatibilityLevel.FULL,
            CompatibilityLevel.PARTIAL,
            CompatibilityLevel.DEGRADED
        ]

    def test_config_migration(self):
        """测试配置迁移"""
        clash_config = {
            'name': 'test',
            'server': 'example.com',
            'port': 443,
            'skip-cert-verify': True
        }
        
        migrated, warnings = self.version_manager.migrate_config(
            clash_config, 'clash', 'singbox'
        )
        
        # 应该有一些字段被映射
        assert len(migrated) > 0

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试错误恢复机制"""
        # 模拟一个会失败的函数
        async def failing_function():
            raise ConnectionError("模拟网络错误")
        
        # 使用错误恢复执行
        try:
            result = await self.recovery_manager.execute_with_recovery(
                'test_operation',
                failing_function,
                severity=ErrorSeverity.LOW
            )
        except Exception as e:
            # 预期会有异常，因为我们的函数总是失败
            pass
        
        # 检查错误统计
        stats = self.recovery_manager.get_error_stats()
        assert stats['total_errors'] > 0

    def test_circuit_breaker(self):
        """测试熔断器"""
        circuit_breaker = self.recovery_manager.get_circuit_breaker('test_operation')
        
        # 初始状态应该是 CLOSED
        assert circuit_breaker.state == 'CLOSED'
        
        # 模拟连续失败
        for _ in range(6):  # 超过默认阈值 5
            circuit_breaker._on_failure()
        
        # 应该变为 OPEN 状态
        assert circuit_breaker.state == 'OPEN'


class TestIntegration:
    """集成测试"""

    def setup_method(self):
        # 注册所有组件
        register_hysteria2_support()
        register_tuic_support()
        register_vless_reality_support()
        register_wireguard_support()
        register_singbox_generator()

    @pytest.mark.asyncio
    async def test_full_conversion_pipeline(self):
        """测试完整的转换流水线"""
        # 模拟订阅内容
        subscription_urls = [
            "hysteria2://pass@host1.com:443?up=100&down=200#Hysteria2-1",
            "tuic://uuid:pass@host2.com:443?version=5#TUIC-1",
            "vless://uuid@host3.com:443?security=reality&pbk=key123#VLESS-1"
        ]
        
        # 解析节点
        nodes = []
        for url in subscription_urls:
            parser = protocol_registry.get_parser(url)
            if parser:
                result = parser.parse_url(url)
                if result.success:
                    nodes.append(result.node)
        
        assert len(nodes) == 3
        
        # 生成 sing-box 配置
        generator = protocol_registry.get_generator("sing-box")
        config_result = generator.generate_full_config(nodes)
        
        assert config_result.success
        assert 'outbounds' in config_result.config

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试无效URL的处理
        invalid_url = "invalid://malformed-url"
        parser = protocol_registry.get_parser(invalid_url)
        
        # 应该返回 None 或处理错误
        assert parser is None

    def test_performance_with_large_dataset(self):
        """测试大数据集性能"""
        # 创建大量节点
        large_nodes = []
        for i in range(100):
            node = ProxyNode(
                name=f"Node-{i}",
                type=ProxyType.HYSTERIA2,
                server=f"server{i}.com",
                port=443,
                auth_str=f"pass{i}",
                udp=True
            )
            large_nodes.append(node)
        
        # 生成配置
        generator = protocol_registry.get_generator("sing-box")
        start_time = time.time()
        
        result = generator.generate_full_config(large_nodes)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert result.success
        assert processing_time < 5.0  # 应该在5秒内完成
        print(f"处理100个节点耗时: {processing_time:.3f}秒")


# 性能基准测试
class TestPerformanceBenchmarks:
    """性能基准测试"""

    def setup_method(self):
        register_hysteria2_support()
        register_tuic_support()
        register_vless_reality_support()
        register_wireguard_support()
        register_singbox_generator()

    def test_parsing_performance(self):
        """测试解析性能"""
        import time
        
        urls = [
            "hysteria2://pass@host.com:443?up=100&down=200#Test",
            "tuic://uuid:pass@host.com:443?version=5#Test",
            "vless://uuid@host.com:443?security=reality&pbk=key#Test"
        ] * 100  # 重复100次
        
        start_time = time.time()
        
        for url in urls:
            parser = protocol_registry.get_parser(url)
            if parser:
                result = parser.parse_url(url)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(urls)
        
        print(f"平均解析时间: {avg_time*1000:.3f}ms")
        assert avg_time < 0.01  # 每个URL解析应在10ms内完成

    def test_generation_performance(self):
        """测试配置生成性能"""
        import time
        
        # 创建测试节点
        nodes = []
        for i in range(50):
            node = ProxyNode(
                name=f"Node-{i}",
                type=ProxyType.HYSTERIA2,
                server=f"server{i}.com",
                port=443,
                auth_str=f"pass{i}",
                udp=True
            )
            nodes.append(node)
        
        generator = protocol_registry.get_generator("sing-box")
        
        start_time = time.time()
        result = generator.generate_full_config(nodes)
        end_time = time.time()
        
        generation_time = end_time - start_time
        
        print(f"生成50个节点配置耗时: {generation_time:.3f}秒")
        assert result.success
        assert generation_time < 2.0  # 应在2秒内完成


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])