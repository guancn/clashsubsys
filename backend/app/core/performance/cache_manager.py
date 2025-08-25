"""
缓存管理器
提供高效的缓存策略，优化弱性能VPS环境下的订阅转换性能
"""

import time
import hashlib
import json
import asyncio
import logging
from typing import Any, Optional, Dict, List, Callable, TypeVar, Generic
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from functools import wraps

T = TypeVar('T')


class CacheStrategy(str, Enum):
    """缓存策略"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    TTL = "ttl"           # 时间过期
    ADAPTIVE = "adaptive"  # 自适应策略


@dataclass
class CacheItem(Generic[T]):
    """缓存项"""
    value: T
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None
    size: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        """更新访问时间和计数"""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheStats:
    """缓存统计"""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.memory_usage = 0
        self.start_time = time.time()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def uptime(self) -> float:
        return time.time() - self.start_time

    def reset(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.start_time = time.time()


class MemoryCache:
    """内存缓存实现"""

    def __init__(self, 
                 max_size: int = 1000,
                 max_memory_mb: int = 128,
                 default_ttl: float = 300,
                 strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.max_memory = max_memory_mb * 1024 * 1024  # 转换为字节
        self.default_ttl = default_ttl
        self.strategy = strategy
        
        self._cache: Dict[str, CacheItem] = {}
        self._lock = threading.RLock()
        self.stats = CacheStats()
        self.logger = logging.getLogger("cache.memory")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                return None

            item = self._cache[key]
            
            # 检查是否过期
            if item.is_expired():
                del self._cache[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                return None

            # 更新访问信息
            item.touch()
            self.stats.hits += 1
            
            return item.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存项"""
        with self._lock:
            # 计算项大小
            size = self._estimate_size(value)
            
            # 检查单项大小是否超限
            if size > self.max_memory * 0.1:  # 单项不超过总内存的10%
                self.logger.warning(f"缓存项太大，跳过: {key} ({size} bytes)")
                return False

            now = time.time()
            item = CacheItem(
                value=value,
                created_at=now,
                last_accessed=now,
                ttl=ttl or self.default_ttl,
                size=size
            )

            # 清理过期项
            self._cleanup_expired()

            # 检查是否需要腾出空间
            self._ensure_capacity(size)

            # 添加新项
            self._cache[key] = item
            self.stats.memory_usage += size

            return True

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                item = self._cache.pop(key)
                self.stats.memory_usage -= item.size
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self.stats.memory_usage = 0

    def keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """获取缓存项数量"""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                'size': len(self._cache),
                'memory_usage_mb': self.stats.memory_usage / (1024 * 1024),
                'hit_rate': self.stats.hit_rate,
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'evictions': self.stats.evictions,
                'uptime': self.stats.uptime,
            }

    def _cleanup_expired(self):
        """清理过期项"""
        now = time.time()
        expired_keys = []
        
        for key, item in self._cache.items():
            if item.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            item = self._cache.pop(key)
            self.stats.memory_usage -= item.size
            self.stats.evictions += 1

    def _ensure_capacity(self, new_item_size: int):
        """确保有足够容量"""
        # 检查数量限制
        while len(self._cache) >= self.max_size:
            self._evict_one()

        # 检查内存限制
        while self.stats.memory_usage + new_item_size > self.max_memory:
            if not self._evict_one():
                break  # 无法进一步释放空间

    def _evict_one(self) -> bool:
        """根据策略淘汰一个项"""
        if not self._cache:
            return False

        if self.strategy == CacheStrategy.LRU:
            # 最近最少使用
            key_to_evict = min(self._cache.keys(), 
                             key=lambda k: self._cache[k].last_accessed)
        elif self.strategy == CacheStrategy.LFU:
            # 最少使用频率
            key_to_evict = min(self._cache.keys(), 
                             key=lambda k: self._cache[k].access_count)
        elif self.strategy == CacheStrategy.TTL:
            # 最早创建的
            key_to_evict = min(self._cache.keys(), 
                             key=lambda k: self._cache[k].created_at)
        else:  # ADAPTIVE
            # 综合考虑访问时间、频率和大小
            def adaptive_score(key):
                item = self._cache[key]
                age = time.time() - item.last_accessed
                frequency = item.access_count
                size_factor = item.size / 1024  # KB
                return age * size_factor / (frequency + 1)
            
            key_to_evict = max(self._cache.keys(), key=adaptive_score)

        # 执行淘汰
        item = self._cache.pop(key_to_evict)
        self.stats.memory_usage -= item.size
        self.stats.evictions += 1
        
        return True

    def _estimate_size(self, value: Any) -> int:
        """估算值的内存大小"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, bool):
                return 1
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(item) for item in value) + 64
            elif isinstance(value, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) 
                          for k, v in value.items()) + 64
            else:
                # 对于复杂对象，使用JSON序列化估算
                return len(json.dumps(value, default=str, ensure_ascii=False).encode('utf-8'))
        except:
            return 1024  # 默认值


class CacheManager:
    """缓存管理器"""

    def __init__(self, 
                 memory_cache_size: int = 1000,
                 memory_cache_mb: int = 128,
                 enable_compression: bool = True):
        self.memory_cache = MemoryCache(
            max_size=memory_cache_size,
            max_memory_mb=memory_cache_mb,
            strategy=CacheStrategy.ADAPTIVE
        )
        self.enable_compression = enable_compression
        self.logger = logging.getLogger("cache.manager")
        
        # 不同类型数据的缓存配置
        self.cache_configs = {
            'subscription': {'ttl': 300, 'strategy': CacheStrategy.LRU},
            'parsed_nodes': {'ttl': 600, 'strategy': CacheStrategy.LFU},
            'generated_config': {'ttl': 180, 'strategy': CacheStrategy.LRU},
            'remote_config': {'ttl': 1800, 'strategy': CacheStrategy.TTL},
        }

    def get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 创建一个包含所有参数的字符串
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        # 使用SHA256生成固定长度的键
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:32]

    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_key = f"{cache_type}:{key}"
        return self.memory_cache.get(cache_key)

    def set(self, cache_type: str, key: str, value: Any) -> bool:
        """设置缓存"""
        cache_key = f"{cache_type}:{key}"
        config = self.cache_configs.get(cache_type, {})
        ttl = config.get('ttl', 300)
        
        # 压缩大型数据
        if self.enable_compression and self._should_compress(value):
            value = self._compress_value(value)
        
        return self.memory_cache.set(cache_key, value, ttl)

    def delete(self, cache_type: str, key: str) -> bool:
        """删除缓存"""
        cache_key = f"{cache_type}:{key}"
        return self.memory_cache.delete(cache_key)

    def clear_type(self, cache_type: str):
        """清空指定类型的缓存"""
        prefix = f"{cache_type}:"
        keys_to_delete = [key for key in self.memory_cache.keys() 
                         if key.startswith(prefix)]
        
        for key in keys_to_delete:
            self.memory_cache.delete(key)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.memory_cache.get_stats()
        
        # 按类型统计
        type_stats = {}
        for key in self.memory_cache.keys():
            cache_type = key.split(':', 1)[0]
            if cache_type not in type_stats:
                type_stats[cache_type] = 0
            type_stats[cache_type] += 1
        
        stats['types'] = type_stats
        return stats

    def _should_compress(self, value: Any) -> bool:
        """判断是否应该压缩"""
        try:
            size = len(json.dumps(value, default=str).encode('utf-8'))
            return size > 1024  # 大于1KB的数据进行压缩
        except:
            return False

    def _compress_value(self, value: Any) -> Dict[str, Any]:
        """压缩值"""
        import gzip
        import base64
        
        try:
            json_str = json.dumps(value, default=str, ensure_ascii=False)
            compressed = gzip.compress(json_str.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('ascii')
            
            return {
                '_compressed': True,
                '_data': encoded
            }
        except Exception as e:
            self.logger.warning(f"压缩失败: {e}")
            return value

    def _decompress_value(self, value: Dict[str, Any]) -> Any:
        """解压缩值"""
        import gzip
        import base64
        
        if not isinstance(value, dict) or not value.get('_compressed'):
            return value
        
        try:
            encoded = value['_data']
            compressed = base64.b64decode(encoded.encode('ascii'))
            json_str = gzip.decompress(compressed).decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            self.logger.error(f"解压缩失败: {e}")
            return None


# 缓存装饰器
def cached(cache_type: str, ttl: int = 300, key_func: Optional[Callable] = None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取缓存管理器实例
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if not cache_manager:
                # 创建默认缓存管理器
                cache_manager = CacheManager()
                wrapper._cache_manager = cache_manager
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager.get_cache_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_type, cache_key)
            if cached_result is not None:
                # 处理解压缩
                if isinstance(cached_result, dict) and cached_result.get('_compressed'):
                    cached_result = cache_manager._decompress_value(cached_result)
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache_manager.set(cache_type, cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# 异步缓存装饰器
def async_cached(cache_type: str, ttl: int = 300, key_func: Optional[Callable] = None):
    """异步缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取缓存管理器实例
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if not cache_manager:
                cache_manager = CacheManager()
                wrapper._cache_manager = cache_manager
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager.get_cache_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_type, cache_key)
            if cached_result is not None:
                if isinstance(cached_result, dict) and cached_result.get('_compressed'):
                    cached_result = cache_manager._decompress_value(cached_result)
                return cached_result
            
            # 执行异步函数
            result = await func(*args, **kwargs)
            
            # 存入缓存
            cache_manager.set(cache_type, cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# 全局缓存管理器实例
global_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    return global_cache_manager


# 缓存清理任务
class CacheCleanupTask:
    """缓存清理任务"""
    
    def __init__(self, cache_manager: CacheManager, interval: int = 300):
        self.cache_manager = cache_manager
        self.interval = interval
        self.running = False
        self.logger = logging.getLogger("cache.cleanup")

    async def start(self):
        """启动清理任务"""
        self.running = True
        while self.running:
            try:
                await asyncio.sleep(self.interval)
                self._cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"缓存清理任务错误: {e}")

    def stop(self):
        """停止清理任务"""
        self.running = False

    def _cleanup(self):
        """执行清理操作"""
        # 清理过期项
        self.cache_manager.memory_cache._cleanup_expired()
        
        # 记录统计信息
        stats = self.cache_manager.get_stats()
        self.logger.info(f"缓存清理完成 - 大小: {stats['size']}, "
                        f"内存使用: {stats['memory_usage_mb']:.2f}MB, "
                        f"命中率: {stats['hit_rate']:.2%}")