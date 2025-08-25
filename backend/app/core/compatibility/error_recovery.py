"""
错误恢复机制
提供智能错误处理、自动重试和降级策略
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Callable, Union, Type
from dataclasses import dataclass
from enum import Enum
import functools
from contextlib import asynccontextmanager

from .version_manager import get_version_manager, CompatibilityLevel
from ..performance.cache_manager import get_cache_manager


class RecoveryStrategy(str, Enum):
    """恢复策略"""
    RETRY = "retry"                    # 重试
    FALLBACK = "fallback"             # 回退到备用方案
    DEGRADE = "degrade"               # 降级处理
    IGNORE = "ignore"                 # 忽略错误
    ABORT = "abort"                   # 中止操作


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"                       # 低：不影响核心功能
    MEDIUM = "medium"                 # 中：部分功能受影响
    HIGH = "high"                     # 高：核心功能受影响
    CRITICAL = "critical"             # 严重：系统无法正常工作


@dataclass
class ErrorContext:
    """错误上下文"""
    error: Exception
    operation: str
    attempts: int
    max_attempts: int
    severity: ErrorSeverity
    metadata: Dict[str, Any] = None


@dataclass
class RecoveryRule:
    """恢复规则"""
    error_types: List[Type[Exception]]
    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    fallback_func: Optional[Callable] = None
    condition_func: Optional[Callable] = None  # 判断是否应用此规则的条件


class CircuitBreaker:
    """熔断器"""

    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger("recovery.circuit_breaker")

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """成功回调"""
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.failure_count = 0
            self.logger.info("熔断器已重置为 CLOSED 状态")

    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.warning(f"熔断器已切换为 OPEN 状态，失败次数: {self.failure_count}")


class ErrorRecoveryManager:
    """错误恢复管理器"""

    def __init__(self):
        self.logger = logging.getLogger("recovery.manager")
        self.version_manager = get_version_manager()
        self.cache_manager = get_cache_manager()
        
        # 恢复规则
        self.recovery_rules = self._initialize_recovery_rules()
        
        # 熔断器实例
        self.circuit_breakers = {}
        
        # 错误统计
        self.error_stats = {
            'total_errors': 0,
            'recovered_errors': 0,
            'failed_recoveries': 0,
            'by_type': {},
            'by_operation': {}
        }

    def _initialize_recovery_rules(self) -> List[RecoveryRule]:
        """初始化恢复规则"""
        return [
            # 网络相关错误 - 重试策略
            RecoveryRule(
                error_types=[ConnectionError, TimeoutError, OSError],
                strategy=RecoveryStrategy.RETRY,
                max_retries=3,
                retry_delay=1.0,
                backoff_factor=2.0
            ),
            
            # HTTP 错误 - 根据状态码决定策略
            RecoveryRule(
                error_types=[Exception],  # 会通过 condition_func 进一步过滤
                strategy=RecoveryStrategy.RETRY,
                max_retries=2,
                retry_delay=0.5,
                condition_func=lambda ctx: self._is_retryable_http_error(ctx.error)
            ),
            
            # 解析错误 - 降级策略
            RecoveryRule(
                error_types=[ValueError, KeyError, TypeError],
                strategy=RecoveryStrategy.DEGRADE,
                fallback_func=self._parse_error_fallback
            ),
            
            # 内存不足 - 降级策略
            RecoveryRule(
                error_types=[MemoryError],
                strategy=RecoveryStrategy.DEGRADE,
                fallback_func=self._memory_error_fallback
            ),
            
            # 配置生成错误 - 回退策略
            RecoveryRule(
                error_types=[Exception],
                strategy=RecoveryStrategy.FALLBACK,
                condition_func=lambda ctx: 'generate_config' in ctx.operation,
                fallback_func=self._config_generation_fallback
            ),
            
            # 未知错误 - 记录并忽略
            RecoveryRule(
                error_types=[Exception],
                strategy=RecoveryStrategy.IGNORE,
                condition_func=lambda ctx: ctx.severity == ErrorSeverity.LOW
            )
        ]

    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = CircuitBreaker()
        return self.circuit_breakers[operation]

    async def execute_with_recovery(self,
                                  operation: str,
                                  func: Callable,
                                  *args,
                                  severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                                  **kwargs) -> Any:
        """带恢复机制地执行函数"""
        attempts = 0
        last_error = None
        
        while attempts < 10:  # 最大尝试次数限制
            attempts += 1
            
            try:
                # 检查熔断器
                circuit_breaker = self.get_circuit_breaker(operation)
                if circuit_breaker.state == 'OPEN':
                    if not circuit_breaker._should_attempt_reset():
                        raise Exception(f"Operation '{operation}' is circuit-broken")
                
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 成功时重置熔断器
                circuit_breaker._on_success()
                
                # 更新统计
                if attempts > 1:
                    self.error_stats['recovered_errors'] += 1
                
                return result
                
            except Exception as e:
                last_error = e
                self._update_error_stats(e, operation)
                circuit_breaker._on_failure()
                
                # 创建错误上下文
                error_context = ErrorContext(
                    error=e,
                    operation=operation,
                    attempts=attempts,
                    max_attempts=10,
                    severity=severity,
                    metadata={'args': args, 'kwargs': kwargs}
                )
                
                # 查找适用的恢复规则
                rule = self._find_recovery_rule(error_context)
                if not rule:
                    self.logger.error(f"未找到适用的恢复规则: {operation}, {type(e).__name__}")
                    break
                
                # 应用恢复策略
                recovery_result = await self._apply_recovery_strategy(error_context, rule, func, *args, **kwargs)
                
                if recovery_result.get('success'):
                    return recovery_result.get('result')
                elif recovery_result.get('should_stop'):
                    break
                elif recovery_result.get('should_retry'):
                    continue
                else:
                    break
        
        # 所有恢复尝试都失败了
        self.error_stats['failed_recoveries'] += 1
        self.logger.error(f"恢复失败，操作: {operation}, 最后错误: {last_error}")
        raise last_error

    def _find_recovery_rule(self, context: ErrorContext) -> Optional[RecoveryRule]:
        """查找适用的恢复规则"""
        for rule in self.recovery_rules:
            # 检查错误类型
            if not any(isinstance(context.error, error_type) for error_type in rule.error_types):
                continue
            
            # 检查条件函数
            if rule.condition_func and not rule.condition_func(context):
                continue
            
            return rule
        
        return None

    async def _apply_recovery_strategy(self,
                                     context: ErrorContext,
                                     rule: RecoveryRule,
                                     func: Callable,
                                     *args,
                                     **kwargs) -> Dict[str, Any]:
        """应用恢复策略"""
        if rule.strategy == RecoveryStrategy.RETRY:
            return await self._handle_retry_strategy(context, rule)
        
        elif rule.strategy == RecoveryStrategy.FALLBACK:
            return await self._handle_fallback_strategy(context, rule, func, *args, **kwargs)
        
        elif rule.strategy == RecoveryStrategy.DEGRADE:
            return await self._handle_degrade_strategy(context, rule, func, *args, **kwargs)
        
        elif rule.strategy == RecoveryStrategy.IGNORE:
            return await self._handle_ignore_strategy(context, rule)
        
        elif rule.strategy == RecoveryStrategy.ABORT:
            return await self._handle_abort_strategy(context, rule)
        
        return {'success': False, 'should_stop': True}

    async def _handle_retry_strategy(self, context: ErrorContext, rule: RecoveryRule) -> Dict[str, Any]:
        """处理重试策略"""
        if context.attempts >= rule.max_retries:
            self.logger.warning(f"重试次数已达上限: {context.operation}")
            return {'success': False, 'should_stop': True}
        
        # 计算延迟时间（指数退避）
        delay = rule.retry_delay * (rule.backoff_factor ** (context.attempts - 1))
        
        self.logger.info(f"重试操作 '{context.operation}' (第{context.attempts}次)，延迟 {delay:.2f}s")
        await asyncio.sleep(delay)
        
        return {'success': False, 'should_retry': True}

    async def _handle_fallback_strategy(self,
                                      context: ErrorContext,
                                      rule: RecoveryRule,
                                      func: Callable,
                                      *args,
                                      **kwargs) -> Dict[str, Any]:
        """处理回退策略"""
        if not rule.fallback_func:
            self.logger.error(f"回退策略缺少回退函数: {context.operation}")
            return {'success': False, 'should_stop': True}
        
        try:
            self.logger.info(f"使用回退方案: {context.operation}")
            
            if asyncio.iscoroutinefunction(rule.fallback_func):
                result = await rule.fallback_func(context, *args, **kwargs)
            else:
                result = rule.fallback_func(context, *args, **kwargs)
            
            return {'success': True, 'result': result}
        
        except Exception as e:
            self.logger.error(f"回退方案也失败了: {e}")
            return {'success': False, 'should_stop': True}

    async def _handle_degrade_strategy(self,
                                     context: ErrorContext,
                                     rule: RecoveryRule,
                                     func: Callable,
                                     *args,
                                     **kwargs) -> Dict[str, Any]:
        """处理降级策略"""
        try:
            self.logger.info(f"启用降级模式: {context.operation}")
            
            # 使用降级后的参数重新执行
            degraded_args, degraded_kwargs = self._get_degraded_parameters(context, *args, **kwargs)
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*degraded_args, **degraded_kwargs)
            else:
                result = func(*degraded_args, **degraded_kwargs)
            
            return {'success': True, 'result': result}
        
        except Exception as e:
            self.logger.error(f"降级模式也失败了: {e}")
            if rule.fallback_func:
                return await self._handle_fallback_strategy(context, rule, func, *args, **kwargs)
            return {'success': False, 'should_stop': True}

    async def _handle_ignore_strategy(self, context: ErrorContext, rule: RecoveryRule) -> Dict[str, Any]:
        """处理忽略策略"""
        self.logger.warning(f"忽略错误: {context.operation} - {context.error}")
        return {'success': True, 'result': None}

    async def _handle_abort_strategy(self, context: ErrorContext, rule: RecoveryRule) -> Dict[str, Any]:
        """处理中止策略"""
        self.logger.error(f"中止操作: {context.operation} - {context.error}")
        return {'success': False, 'should_stop': True}

    def _get_degraded_parameters(self, context: ErrorContext, *args, **kwargs):
        """获取降级后的参数"""
        # 根据错误类型和操作类型调整参数
        degraded_kwargs = kwargs.copy()
        
        if isinstance(context.error, MemoryError):
            # 内存不足时减少处理量
            degraded_kwargs['batch_size'] = min(degraded_kwargs.get('batch_size', 50), 10)
            degraded_kwargs['enable_compression'] = False
        
        elif 'timeout' in str(context.error).lower():
            # 超时错误时增加超时时间
            degraded_kwargs['timeout'] = degraded_kwargs.get('timeout', 30) * 2
        
        elif isinstance(context.error, (ValueError, KeyError, TypeError)):
            # 解析错误时启用兼容模式
            degraded_kwargs['strict_mode'] = False
            degraded_kwargs['ignore_errors'] = True
        
        return args, degraded_kwargs

    def _is_retryable_http_error(self, error: Exception) -> bool:
        """判断HTTP错误是否可重试"""
        error_str = str(error).lower()
        
        # 可重试的状态码
        retryable_codes = ['502', '503', '504', '408', '429', '500']
        
        for code in retryable_codes:
            if code in error_str:
                return True
        
        # 网络相关错误
        retryable_keywords = ['timeout', 'connection', 'network', 'dns']
        
        for keyword in retryable_keywords:
            if keyword in error_str:
                return True
        
        return False

    def _parse_error_fallback(self, context: ErrorContext, *args, **kwargs) -> Any:
        """解析错误的回退方案"""
        self.logger.info("使用简化解析器")
        
        # 尝试使用更宽松的解析规则
        if hasattr(context, 'metadata') and context.metadata:
            raw_data = context.metadata.get('raw_data')
            if raw_data:
                # 简单的行分割和基础验证
                lines = raw_data.strip().split('\n')
                valid_lines = [line for line in lines if line.strip() and '://' in line]
                return valid_lines[:10]  # 限制数量
        
        return []

    def _memory_error_fallback(self, context: ErrorContext, *args, **kwargs) -> Any:
        """内存不足的回退方案"""
        self.logger.warning("内存不足，启用精简模式")
        
        # 清理缓存
        self.cache_manager.memory_cache.clear()
        
        # 返回精简结果
        return {'status': 'degraded', 'message': '由于内存限制，返回精简结果'}

    def _config_generation_fallback(self, context: ErrorContext, *args, **kwargs) -> str:
        """配置生成的回退方案"""
        self.logger.info("使用简化配置模板")
        
        # 返回基础的配置模板
        return """# Fallback Configuration
# Generated due to error in primary config generation

proxies: []
proxy-groups:
  - name: "PROXY"
    type: select
    proxies: ["DIRECT"]
rules:
  - MATCH,PROXY
"""

    def _update_error_stats(self, error: Exception, operation: str):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        
        error_type = type(error).__name__
        if error_type not in self.error_stats['by_type']:
            self.error_stats['by_type'][error_type] = 0
        self.error_stats['by_type'][error_type] += 1
        
        if operation not in self.error_stats['by_operation']:
            self.error_stats['by_operation'][operation] = 0
        self.error_stats['by_operation'][operation] += 1

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        total = self.error_stats['total_errors']
        recovered = self.error_stats['recovered_errors']
        
        return {
            **self.error_stats,
            'recovery_rate': recovered / total if total > 0 else 0.0,
            'circuit_breakers': {
                name: {
                    'state': cb.state,
                    'failure_count': cb.failure_count,
                    'last_failure_time': cb.last_failure_time
                }
                for name, cb in self.circuit_breakers.items()
            }
        }

    @asynccontextmanager
    async def error_boundary(self, operation: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """错误边界上下文管理器"""
        try:
            yield
        except Exception as e:
            self.logger.error(f"错误边界捕获异常: {operation} - {e}")
            self.logger.debug(traceback.format_exc())
            
            # 根据严重程度决定是否重新抛出
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                raise
            
            # 低严重程度的错误可以被吸收
            self._update_error_stats(e, operation)

    def reset_circuit_breaker(self, operation: str):
        """手动重置熔断器"""
        if operation in self.circuit_breakers:
            cb = self.circuit_breakers[operation]
            cb.state = 'CLOSED'
            cb.failure_count = 0
            cb.last_failure_time = None
            self.logger.info(f"手动重置熔断器: {operation}")

    def reset_all_circuit_breakers(self):
        """重置所有熔断器"""
        for operation in self.circuit_breakers:
            self.reset_circuit_breaker(operation)


# 全局错误恢复管理器
global_error_recovery = ErrorRecoveryManager()


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """获取全局错误恢复管理器"""
    return global_error_recovery


# 装饰器
def with_error_recovery(operation: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """错误恢复装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            recovery_manager = get_error_recovery_manager()
            return await recovery_manager.execute_with_recovery(
                operation, func, *args, severity=severity, **kwargs
            )
        return wrapper
    return decorator


def circuit_breaker(operation: str, 
                   failure_threshold: int = 5,
                   recovery_timeout: float = 60.0):
    """熔断器装饰器"""
    def decorator(func):
        recovery_manager = get_error_recovery_manager()
        cb = CircuitBreaker(failure_threshold, recovery_timeout)
        recovery_manager.circuit_breakers[operation] = cb
        return cb(func)
    return decorator