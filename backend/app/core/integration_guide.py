"""
新协议支持集成指南
提供完整的集成说明和部署建议
"""

from typing import Dict, Any, List
from pathlib import Path


class IntegrationGuide:
    """集成指南生成器"""

    def __init__(self):
        self.components = {
            "protocol_parsers": {
                "hysteria2": "Hysteria2Parser",
                "tuic": "TuicParser", 
                "vless_reality": "VlessRealityParser",
                "wireguard": "WireGuardParser"
            },
            "config_generators": {
                "singbox": "SingBoxConfigGenerator"
            },
            "performance_modules": {
                "cache_manager": "CacheManager",
                "optimizer": "PerformanceOptimizer"
            },
            "compatibility_modules": {
                "version_manager": "VersionManager",
                "error_recovery": "ErrorRecoveryManager"
            }
        }

    def generate_integration_guide(self) -> str:
        """生成集成指南"""
        guide = f"""
# 订阅转换系统新协议支持集成指南

## 概述

本指南提供了将新协议支持（Hysteria2、TUIC v5、VLESS Reality、WireGuard）集成到现有订阅转换系统的详细说明。

## 支持的协议

### 1. Hysteria2
- **描述**: 基于 QUIC 的高性能代理协议
- **特性**: 支持 BBR 拥塞控制、Salamander 混淆、自适应带宽
- **解析器**: `Hysteria2Parser`
- **支持格式**: URL、Clash、sing-box

### 2. TUIC v5
- **描述**: 新一代 QUIC 代理协议
- **特性**: UUID+密码认证、UDP 中继模式、减少 RTT
- **解析器**: `TuicParser`
- **版本支持**: v4、v5（自动检测和迁移）

### 3. VLESS Reality
- **描述**: 具有强伪装能力的协议
- **特性**: Reality TLS、多种传输方式、流量控制
- **解析器**: `VlessRealityParser`
- **传输支持**: TCP、WebSocket、HTTP/2、gRPC

### 4. WireGuard
- **描述**: 现代 VPN 协议
- **特性**: 高性能、简单配置、强加密
- **解析器**: `WireGuardParser`
- **配置支持**: URL、标准配置文件格式

### 5. sing-box 配置格式
- **描述**: 新兴的统一配置格式
- **生成器**: `SingBoxConfigGenerator`
- **支持协议**: 所有上述协议

## 集成步骤

### 第一步：安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 新增依赖（如果需要）
pip install packaging psutil
```

### 第二步：注册协议支持

在应用启动时注册所有协议解析器：

```python
from app.core.parsers.hysteria2_parser import register_hysteria2_support
from app.core.parsers.tuic_parser import register_tuic_support
from app.core.parsers.vless_reality_parser import register_vless_reality_support
from app.core.parsers.wireguard_parser import register_wireguard_support
from app.core.generators.singbox_generator import register_singbox_generator

def initialize_new_protocols():
    \"\"\"初始化新协议支持\"\"\"
    register_hysteria2_support()
    register_tuic_support()
    register_vless_reality_support()
    register_wireguard_support()
    register_singbox_generator()
```

### 第三步：更新解析逻辑

修改现有的解析器以支持新协议：

```python
from app.core.protocol_parser_interface import protocol_registry

class EnhancedSubscriptionParser:
    def __init__(self):
        self.registry = protocol_registry
    
    def parse_subscription(self, content: str) -> List[ProxyNode]:
        nodes = []
        lines = content.strip().split('\\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line.startswith(('hysteria2://', 'tuic://', 'vless://', 'wg://')):
                continue
            
            # 使用注册表查找解析器
            parser = self.registry.get_parser(line)
            if parser:
                result = parser.parse_url(line)
                if result.success:
                    nodes.append(result.node)
        
        return nodes
```

### 第四步：集成配置生成

添加 sing-box 配置格式支持：

```python
from app.core.generators.singbox_generator import SingBoxConfigGenerator

class EnhancedConverter:
    def __init__(self):
        self.singbox_generator = SingBoxConfigGenerator()
    
    async def convert_to_singbox(self, nodes: List[ProxyNode]) -> str:
        result = self.singbox_generator.generate_full_config(nodes)
        if result.success:
            return json.dumps(result.config, indent=2)
        else:
            raise ValueError(f"配置生成失败: {{result.error}}")
```

### 第五步：启用性能优化

集成缓存和性能优化：

```python
from app.core.performance.cache_manager import get_cache_manager
from app.core.performance.optimizer import get_performance_optimizer

# 在转换过程中使用优化器
optimizer = get_performance_optimizer()

async def optimized_conversion(urls: List[str]):
    async with optimizer.performance_context():
        # 优化的订阅获取
        subscriptions = await optimizer.optimize_subscription_fetch(urls)
        
        # 优化的节点解析
        nodes = await optimizer.optimize_node_parsing(subscriptions)
        
        # 优化的配置生成
        config = await optimizer.optimize_config_generation(nodes, 'sing-box')
        
        return config
```

### 第六步：添加错误恢复

集成智能错误恢复机制：

```python
from app.core.compatibility.error_recovery import with_error_recovery, ErrorSeverity

class RobustConverter:
    @with_error_recovery("subscription_conversion", ErrorSeverity.HIGH)
    async def convert_subscription(self, request):
        # 转换逻辑
        pass
    
    @with_error_recovery("node_parsing", ErrorSeverity.MEDIUM)  
    async def parse_nodes(self, content):
        # 解析逻辑
        pass
```

## 配置示例

### Hysteria2 配置示例

```yaml
# Clash 格式
- name: "Hysteria2-Example"
  type: hysteria2
  server: example.com
  port: 443
  auth: password123
  up: "100 Mbps"
  down: "200 Mbps"
  sni: example.com
  skip-cert-verify: false
  obfs:
    type: salamander
    password: secret123
```

```json
// sing-box 格式
{{
  "type": "hysteria2",
  "tag": "Hysteria2-Example",
  "server": "example.com",
  "server_port": 443,
  "auth": "password123",
  "up_mbps": 100,
  "down_mbps": 200,
  "tls": {{
    "enabled": true,
    "server_name": "example.com"
  }},
  "obfs": {{
    "type": "salamander",
    "password": "secret123"
  }}
}}
```

### TUIC v5 配置示例

```yaml
# Clash 格式
- name: "TUIC-v5-Example"
  type: tuic
  server: example.com
  port: 443
  uuid: "550e8400-e29b-41d4-a716-446655440000"
  password: "password123"
  version: 5
  congestion-control: "bbr"
  udp-relay-mode: "native"
  reduce-rtt: true
```

### VLESS Reality 配置示例

```yaml
# Clash Meta 格式
- name: "VLESS-Reality-Example"
  type: vless
  server: example.com
  port: 443
  uuid: "550e8400-e29b-41d4-a716-446655440000"
  network: tcp
  reality-opts:
    public-key: "publickey123"
    short-id: "shortid123"
  servername: example.com
  client-fingerprint: chrome
```

### WireGuard 配置示例

```json
// sing-box 格式（WireGuard 主要在 sing-box 中支持）
{{
  "type": "wireguard",
  "tag": "WireGuard-Example",
  "server": "example.com",
  "server_port": 51820,
  "private_key": "privatekey123",
  "peer_public_key": "publickey123",
  "local_address": ["10.0.0.2/32"],
  "mtu": 1420
}}
```

## API 集成

### 添加新的 API 端点

```python
from fastapi import APIRouter, HTTPException
from app.models.schemas import ConversionRequest, ConversionResponse

router = APIRouter()

@router.post("/convert/singbox", response_model=ConversionResponse)
async def convert_to_singbox(request: ConversionRequest):
    try:
        # 使用增强的转换器
        converter = EnhancedConverter()
        nodes = await converter.parse_subscriptions(request.url)
        
        if not nodes:
            raise HTTPException(status_code=400, detail="无法解析任何有效节点")
        
        config = await converter.convert_to_singbox(nodes)
        
        return ConversionResponse(
            success=True,
            message="转换成功",
            config=config,
            nodes_count=len(nodes)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 性能优化配置

### 推荐的生产环境配置

```python
# 在应用启动时配置性能优化器
optimizer = get_performance_optimizer()
optimizer.configure(
    enable_caching=True,
    enable_compression=True,
    enable_batching=True,
    enable_throttling=True,
    max_concurrent_requests=10,  # 根据 VPS 性能调整
    memory_limit_mb=128,         # 根据可用内存调整
    processing_timeout=30.0
)

# 配置缓存管理器
cache_manager = get_cache_manager()
# 缓存会自动使用合理的默认设置
```

## 监控和日志

### 添加监控端点

```python
@router.get("/health/protocols")
async def protocol_health():
    registry_health = protocol_registry.health_check()
    cache_stats = get_cache_manager().get_stats()
    optimizer_stats = get_performance_optimizer().get_optimization_stats()
    
    return {{
        "registry": registry_health,
        "cache": cache_stats,
        "optimizer": optimizer_stats,
        "supported_protocols": protocol_registry.get_supported_protocols(),
        "supported_formats": protocol_registry.get_supported_formats()
    }}
```

### 配置日志记录

```python
import logging

# 为新组件配置日志
logging.getLogger("parser").setLevel(logging.INFO)
logging.getLogger("generator").setLevel(logging.INFO) 
logging.getLogger("performance").setLevel(logging.INFO)
logging.getLogger("compatibility").setLevel(logging.WARNING)
logging.getLogger("recovery").setLevel(logging.WARNING)
```

## 测试和验证

### 运行测试套件

```bash
# 运行单元测试
python -m pytest app/tests/test_new_protocols.py -v

# 运行完整验证
python app/tests/validation_runner.py

# 运行性能基准测试
python -m pytest app/tests/test_new_protocols.py::TestPerformanceBenchmarks -v
```

### 验证新协议支持

```python
# 验证脚本示例
async def verify_protocol_support():
    test_urls = [
        "hysteria2://pass@host.com:443?up=100&down=200#Test",
        "tuic://uuid:pass@host.com:443?version=5#Test",
        "vless://uuid@host.com:443?security=reality&pbk=key#Test",
        "wg://private:public@host.com:51820#Test"
    ]
    
    for url in test_urls:
        parser = protocol_registry.get_parser(url)
        if parser:
            result = parser.parse_url(url)
            print(f"{{url[:20]}}... : {{'✓' if result.success else '✗'}}")
        else:
            print(f"{{url[:20]}}... : ✗ (无解析器)")
```

## 部署考虑

### 弱性能 VPS 优化

1. **内存限制**：设置较小的缓存大小（64-128MB）
2. **并发控制**：限制同时处理的请求数（5-10个）
3. **超时设置**：适当增加超时时间以适应网络延迟
4. **批处理**：启用批处理以提高效率
5. **压缩**：启用配置压缩以节省内存

### 容器化部署

```dockerfile
# 在 Dockerfile 中添加新依赖
RUN pip install packaging psutil

# 确保缓存目录权限
RUN mkdir -p /app/cache && chown app:app /app/cache
```

### 环境变量配置

```bash
# 性能优化配置
ENABLE_PROTOCOL_CACHING=true
MAX_CONCURRENT_REQUESTS=8
MEMORY_LIMIT_MB=128
PROCESSING_TIMEOUT=30

# 新协议特性开关
ENABLE_HYSTERIA2=true
ENABLE_TUIC_V5=true  
ENABLE_VLESS_REALITY=true
ENABLE_WIREGUARD=true
ENABLE_SINGBOX_FORMAT=true
```

## 故障排除

### 常见问题和解决方案

1. **解析器未找到**
   - 检查协议是否正确注册
   - 验证 URL 格式是否正确

2. **配置生成失败**
   - 检查节点必需字段是否完整
   - 验证协议特定配置是否正确

3. **性能问题**
   - 调整并发限制
   - 检查缓存配置
   - 监控内存使用

4. **兼容性问题**
   - 使用版本管理器检查兼容性
   - 启用降级模式
   - 查看迁移警告

### 日志分析

```bash
# 查看协议解析日志
grep "parser" /var/log/app.log

# 查看性能统计
grep "performance" /var/log/app.log

# 查看错误恢复
grep "recovery" /var/log/app.log
```

## 升级和维护

### 版本升级

1. 备份现有配置
2. 更新代码
3. 运行迁移脚本（如需要）
4. 重新注册协议支持
5. 验证功能正常

### 定期维护

1. 清理缓存（自动进行）
2. 检查错误统计
3. 更新协议版本信息
4. 性能调优

## 扩展指南

### 添加新协议支持

1. 创建解析器类继承 `BaseProtocolParser`
2. 创建配置生成器继承 `BaseConfigGenerator`
3. 实现必需的接口方法
4. 注册到协议注册表
5. 添加测试用例
6. 更新文档

### 自定义配置格式

1. 创建生成器继承 `BaseConfigGenerator`
2. 实现格式特定的生成逻辑
3. 注册到注册表
4. 添加API端点支持

---

## 总结

本集成指南提供了完整的新协议支持集成方案，包括：

- 4个新协议解析器的集成
- sing-box配置格式支持
- 性能优化和缓存系统
- 智能错误恢复机制
- 版本兼容性管理
- 完整的测试和验证方案

通过遵循本指南，您可以成功地将新协议支持集成到现有的订阅转换系统中，并确保在弱性能VPS环境下的稳定运行。

更多技术细节请参考各模块的源代码和测试用例。
"""
        
        return guide

    def generate_deployment_script(self) -> str:
        """生成部署脚本"""
        script = '''#!/bin/bash

# 新协议支持部署脚本

echo "开始部署新协议支持..."

# 检查Python版本
python3 --version
if [ $? -ne 0 ]; then
    echo "错误: 未找到Python 3"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
pip3 install packaging psutil

# 创建缓存目录
echo "创建缓存目录..."
mkdir -p /app/cache
chmod 755 /app/cache

# 运行验证测试
echo "运行验证测试..."
cd /app
python3 -m app.tests.validation_runner

if [ $? -eq 0 ]; then
    echo "✓ 新协议支持部署成功"
else
    echo "✗ 验证失败，请检查日志"
    exit 1
fi

# 重启服务
echo "重启服务..."
systemctl restart subscription-converter

echo "部署完成！"
'''
        return script

    def generate_performance_tuning_guide(self) -> str:
        """生成性能调优指南"""
        guide = '''
# 弱性能VPS环境性能调优指南

## 系统配置

### 内存优化
- 限制缓存大小: 64-128MB
- 启用压缩: 减少内存占用
- 定期清理: 自动垃圾回收

### CPU优化  
- 限制并发: 5-10个请求
- 批处理: 提高处理效率
- 异步处理: 非阻塞I/O

### 网络优化
- 连接复用: 减少连接开销
- 超时设置: 适应网络延迟
- 重试机制: 智能错误恢复

## 监控指标

### 关键指标
- 内存使用率: <85%
- CPU使用率: <80%  
- 响应时间: <5秒
- 错误率: <5%

### 监控命令
```bash
# 内存使用
free -h

# CPU负载
top -p $(pgrep -f subscription-converter)

# 应用统计
curl http://localhost:8000/health/protocols
```

## 性能调优参数

```python
# 生产环境推荐配置
OPTIMIZER_CONFIG = {
    'enable_caching': True,
    'enable_compression': True,
    'enable_batching': True,
    'max_concurrent_requests': 8,  # 根据CPU核心数调整
    'memory_limit_mb': 128,        # 根据可用内存调整
    'processing_timeout': 30.0,
    'cache_ttl': 300,              # 5分钟缓存
    'batch_size': 20,              # 批处理大小
}
```

## 故障处理

### 内存不足
1. 减少缓存大小
2. 启用压缩
3. 限制并发数
4. 重启服务

### CPU过载
1. 降低并发限制
2. 增加处理延迟
3. 启用批处理
4. 优化算法

### 网络超时
1. 增加超时时间
2. 启用重试机制
3. 检查网络连接
4. 使用CDN加速
'''
        return guide


def main():
    """生成集成指南和相关文档"""
    guide_generator = IntegrationGuide()
    
    # 生成集成指南
    integration_guide = guide_generator.generate_integration_guide()
    Path("integration_guide.md").write_text(integration_guide, encoding='utf-8')
    
    # 生成部署脚本
    deployment_script = guide_generator.generate_deployment_script()
    Path("deploy_new_protocols.sh").write_text(deployment_script)
    
    # 生成性能调优指南
    tuning_guide = guide_generator.generate_performance_tuning_guide()
    Path("performance_tuning_guide.md").write_text(tuning_guide, encoding='utf-8')
    
    print("集成指南生成完成:")
    print("- integration_guide.md")
    print("- deploy_new_protocols.sh") 
    print("- performance_tuning_guide.md")


if __name__ == "__main__":
    main()