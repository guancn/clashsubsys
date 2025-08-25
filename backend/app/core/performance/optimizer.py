"""
性能优化器
专为弱性能VPS环境设计的性能优化策略
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
import threading
from functools import wraps

from .cache_manager import CacheManager, get_cache_manager


@dataclass
class SystemResources:
    """系统资源状态"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: int
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


@dataclass
class PerformanceMetrics:
    """性能指标"""
    processing_time: float
    memory_peak_mb: float
    cpu_peak_percent: float
    cache_hit_rate: float
    nodes_processed: int
    errors_count: int


class ResourceMonitor:
    """系统资源监控器"""

    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.monitoring = False
        self.metrics_history = []
        self.logger = logging.getLogger("performance.monitor")

    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False

    def get_current_resources(self) -> SystemResources:
        """获取当前系统资源状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()

            return SystemResources(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_mb=memory.available / (1024 * 1024),
                disk_io_read_mb=getattr(disk_io, 'read_bytes', 0) / (1024 * 1024),
                disk_io_write_mb=getattr(disk_io, 'write_bytes', 0) / (1024 * 1024),
                network_sent_mb=getattr(network_io, 'bytes_sent', 0) / (1024 * 1024),
                network_recv_mb=getattr(network_io, 'bytes_recv', 0) / (1024 * 1024)
            )
        except Exception as e:
            self.logger.warning(f"获取系统资源状态失败: {e}")
            return SystemResources(0, 0, 0, 0, 0, 0, 0)

    def is_system_under_load(self, 
                           cpu_threshold: float = 80.0,
                           memory_threshold: float = 85.0) -> bool:
        """检查系统是否处于高负载状态"""
        resources = self.get_current_resources()
        return (resources.cpu_percent > cpu_threshold or 
                resources.memory_percent > memory_threshold)

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                resources = self.get_current_resources()
                timestamp = time.time()
                
                self.metrics_history.append((timestamp, resources))
                
                # 保留最近5分钟的数据
                cutoff_time = timestamp - 300
                self.metrics_history = [
                    (t, r) for t, r in self.metrics_history if t > cutoff_time
                ]
                
                time.sleep(self.sampling_interval)
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(self.sampling_interval)


class AdaptiveThrottler:
    """自适应限流器"""

    def __init__(self, 
                 initial_rate: float = 10.0,
                 min_rate: float = 1.0,
                 max_rate: float = 50.0):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.last_request_time = 0
        self.success_count = 0
        self.error_count = 0
        self.adjustment_window = 10  # 调整窗口大小
        self.logger = logging.getLogger("performance.throttler")

    async def acquire(self) -> bool:
        """获取请求许可"""
        now = time.time()
        time_since_last = now - self.last_request_time
        required_interval = 1.0 / self.current_rate

        if time_since_last < required_interval:
            sleep_time = required_interval - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()
        return True

    def report_success(self):
        """报告成功"""
        self.success_count += 1
        self._adjust_rate()

    def report_error(self):
        """报告错误"""
        self.error_count += 1
        self._adjust_rate()

    def _adjust_rate(self):
        """调整速率"""
        total_requests = self.success_count + self.error_count
        
        if total_requests >= self.adjustment_window:
            error_rate = self.error_count / total_requests
            
            if error_rate > 0.1:  # 错误率超过10%，降低速率
                self.current_rate = max(self.min_rate, self.current_rate * 0.8)
            elif error_rate < 0.05:  # 错误率低于5%，提高速率
                self.current_rate = min(self.max_rate, self.current_rate * 1.2)
            
            # 重置计数器
            self.success_count = 0
            self.error_count = 0
            
            self.logger.debug(f"调整请求速率: {self.current_rate:.2f} req/s")


class BatchProcessor:
    """批处理器"""

    def __init__(self, 
                 batch_size: int = 50,
                 max_wait_time: float = 2.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.batch_queue = []
        self.batch_lock = asyncio.Lock()
        self.logger = logging.getLogger("performance.batch")

    async def add_to_batch(self, item: Any, processor: Callable) -> Any:
        """添加项到批处理队列"""
        async with self.batch_lock:
            batch_id = len(self.batch_queue)
            future = asyncio.get_event_loop().create_future()
            
            self.batch_queue.append({
                'item': item,
                'processor': processor,
                'future': future,
                'added_at': time.time()
            })
            
            # 检查是否需要处理批次
            if len(self.batch_queue) >= self.batch_size:
                asyncio.create_task(self._process_batch())
            else:
                # 设置超时处理
                asyncio.create_task(self._timeout_handler())
            
            return await future

    async def _process_batch(self):
        """处理当前批次"""
        async with self.batch_lock:
            if not self.batch_queue:
                return
            
            current_batch = self.batch_queue[:]
            self.batch_queue.clear()
        
        self.logger.debug(f"处理批次，大小: {len(current_batch)}")
        
        # 并行处理批次中的项
        tasks = []
        for batch_item in current_batch:
            task = asyncio.create_task(
                self._process_single_item(batch_item)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_item(self, batch_item: Dict[str, Any]):
        """处理单个项"""
        try:
            result = await batch_item['processor'](batch_item['item'])
            batch_item['future'].set_result(result)
        except Exception as e:
            batch_item['future'].set_exception(e)

    async def _timeout_handler(self):
        """超时处理器"""
        await asyncio.sleep(self.max_wait_time)
        
        async with self.batch_lock:
            if self.batch_queue:
                # 检查最早的项是否超时
                oldest_time = min(item['added_at'] for item in self.batch_queue)
                if time.time() - oldest_time >= self.max_wait_time:
                    await self._process_batch()


class PerformanceOptimizer:
    """性能优化器主类"""

    def __init__(self):
        self.cache_manager = get_cache_manager()
        self.resource_monitor = ResourceMonitor()
        self.throttler = AdaptiveThrottler()
        self.batch_processor = BatchProcessor()
        self.logger = logging.getLogger("performance.optimizer")
        
        # 性能配置
        self.config = {
            'enable_caching': True,
            'enable_compression': True,
            'enable_batching': True,
            'enable_throttling': True,
            'max_concurrent_requests': 10,
            'memory_limit_mb': 128,
            'processing_timeout': 30.0,
        }

    def configure(self, **kwargs):
        """配置优化器"""
        self.config.update(kwargs)
        self.logger.info(f"更新性能配置: {kwargs}")

    async def optimize_subscription_fetch(self, urls: List[str]) -> List[str]:
        """优化订阅获取"""
        if not self.config['enable_batching']:
            # 顺序处理
            return await self._fetch_subscriptions_sequential(urls)
        
        # 批处理
        return await self._fetch_subscriptions_batch(urls)

    async def optimize_node_parsing(self, subscriptions: List[str]) -> List[Any]:
        """优化节点解析"""
        # 检查系统负载
        if self.resource_monitor.is_system_under_load():
            self.logger.warning("系统负载较高，启用保守模式")
            return await self._parse_nodes_conservative(subscriptions)
        
        # 正常模式
        return await self._parse_nodes_optimized(subscriptions)

    async def optimize_config_generation(self, nodes: List[Any], format_type: str) -> str:
        """优化配置生成"""
        cache_key = f"config_{format_type}_{hash(str(nodes))}"
        
        # 检查缓存
        if self.config['enable_caching']:
            cached_config = self.cache_manager.get('generated_config', cache_key)
            if cached_config:
                self.logger.debug("使用缓存的配置")
                return cached_config
        
        # 生成新配置
        config = await self._generate_config(nodes, format_type)
        
        # 缓存结果
        if self.config['enable_caching']:
            self.cache_manager.set('generated_config', cache_key, config)
        
        return config

    async def _fetch_subscriptions_sequential(self, urls: List[str]) -> List[str]:
        """顺序获取订阅"""
        results = []
        for url in urls:
            try:
                if self.config['enable_throttling']:
                    await self.throttler.acquire()
                
                # 这里调用实际的获取逻辑
                result = await self._fetch_single_subscription(url)
                results.append(result)
                
                if self.config['enable_throttling']:
                    self.throttler.report_success()
                    
            except Exception as e:
                self.logger.error(f"获取订阅失败 {url}: {e}")
                if self.config['enable_throttling']:
                    self.throttler.report_error()
                results.append("")
        
        return results

    async def _fetch_subscriptions_batch(self, urls: List[str]) -> List[str]:
        """批量获取订阅"""
        semaphore = asyncio.Semaphore(self.config['max_concurrent_requests'])
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                return await self.batch_processor.add_to_batch(
                    url, self._fetch_single_subscription
                )
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_single_subscription(self, url: str) -> str:
        """获取单个订阅"""
        import httpx
        
        # 检查缓存
        if self.config['enable_caching']:
            cache_key = f"sub_{hash(url)}"
            cached = self.cache_manager.get('subscription', cache_key)
            if cached:
                return cached
        
        # 实际获取
        try:
            timeout = httpx.Timeout(self.config['processing_timeout'])
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.text
                
                # 缓存结果
                if self.config['enable_caching']:
                    self.cache_manager.set('subscription', cache_key, content)
                
                return content
        except Exception as e:
            self.logger.error(f"获取订阅失败: {e}")
            return ""

    async def _parse_nodes_conservative(self, subscriptions: List[str]) -> List[Any]:
        """保守模式解析节点"""
        # 降低并发数，增加延迟
        results = []
        for subscription in subscriptions:
            try:
                await asyncio.sleep(0.1)  # 添加延迟
                nodes = await self._parse_single_subscription(subscription)
                results.extend(nodes)
            except Exception as e:
                self.logger.error(f"解析失败: {e}")
        
        return results

    async def _parse_nodes_optimized(self, subscriptions: List[str]) -> List[Any]:
        """优化模式解析节点"""
        tasks = []
        semaphore = asyncio.Semaphore(self.config['max_concurrent_requests'])
        
        async def parse_with_semaphore(subscription):
            async with semaphore:
                return await self._parse_single_subscription(subscription)
        
        for subscription in subscriptions:
            task = asyncio.create_task(parse_with_semaphore(subscription))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 展平结果
        all_nodes = []
        for result in results:
            if isinstance(result, list):
                all_nodes.extend(result)
            elif not isinstance(result, Exception):
                all_nodes.append(result)
        
        return all_nodes

    async def _parse_single_subscription(self, content: str) -> List[Any]:
        """解析单个订阅"""
        # 检查缓存
        if self.config['enable_caching']:
            cache_key = f"nodes_{hash(content)}"
            cached = self.cache_manager.get('parsed_nodes', cache_key)
            if cached:
                return cached
        
        # 实际解析（这里需要调用实际的解析器）
        from ..parser import SubscriptionParser
        
        parser = SubscriptionParser()
        nodes = parser.parse_subscription(content)
        
        # 缓存结果
        if self.config['enable_caching']:
            self.cache_manager.set('parsed_nodes', cache_key, nodes)
        
        return nodes

    async def _generate_config(self, nodes: List[Any], format_type: str) -> str:
        """生成配置"""
        # 这里需要调用实际的配置生成器
        from ..converter import SubscriptionConverter
        
        converter = SubscriptionConverter()
        # 根据format_type生成相应配置
        # 这里需要适配实际的接口
        
        return "# Generated config placeholder"

    @asynccontextmanager
    async def performance_context(self):
        """性能监控上下文"""
        start_time = time.time()
        start_resources = self.resource_monitor.get_current_resources()
        
        self.resource_monitor.start_monitoring()
        
        try:
            yield
        finally:
            self.resource_monitor.stop_monitoring()
            
            end_time = time.time()
            end_resources = self.resource_monitor.get_current_resources()
            
            # 计算性能指标
            duration = end_time - start_time
            memory_delta = end_resources.memory_percent - start_resources.memory_percent
            cpu_avg = (start_resources.cpu_percent + end_resources.cpu_percent) / 2
            
            self.logger.info(
                f"性能统计 - 耗时: {duration:.2f}s, "
                f"内存变化: {memory_delta:.1f}%, "
                f"平均CPU: {cpu_avg:.1f}%"
            )

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        cache_stats = self.cache_manager.get_stats()
        system_resources = self.resource_monitor.get_current_resources()
        
        return {
            'cache': cache_stats,
            'system': {
                'cpu_percent': system_resources.cpu_percent,
                'memory_percent': system_resources.memory_percent,
                'memory_available_mb': system_resources.memory_available_mb,
            },
            'throttler': {
                'current_rate': self.throttler.current_rate,
                'success_count': self.throttler.success_count,
                'error_count': self.throttler.error_count,
            },
            'config': self.config
        }


# 全局优化器实例
global_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器"""
    return global_optimizer


# 性能装饰器
def optimize_performance(enable_caching: bool = True, 
                        enable_throttling: bool = True):
    """性能优化装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_performance_optimizer()
            
            async with optimizer.performance_context():
                if enable_throttling:
                    await optimizer.throttler.acquire()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if enable_throttling:
                        optimizer.throttler.report_success()
                    
                    return result
                except Exception as e:
                    if enable_throttling:
                        optimizer.throttler.report_error()
                    raise
        
        return wrapper
    return decorator