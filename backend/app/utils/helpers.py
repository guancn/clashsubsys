"""
工具函数
"""

import re
import os
import logging
from typing import Optional, Union
from urllib.parse import urlparse
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """
    验证 URL 格式
    
    Args:
        url: 要验证的 URL
        
    Returns:
        是否为有效 URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的安全文件名
    """
    # 移除不安全字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除开头和结尾的空格和点
    sanitized = sanitized.strip(' .')
    
    # 如果文件名为空或只包含不安全字符，使用默认名称
    if not sanitized:
        sanitized = 'config'
    
    # 限制文件名长度
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized


def format_bytes(bytes_value: int) -> str:
    """
    格式化字节数为可读格式
    
    Args:
        bytes_value: 字节数
        
    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def is_valid_regex(pattern: str) -> bool:
    """
    验证正则表达式是否有效
    
    Args:
        pattern: 正则表达式模式
        
    Returns:
        是否为有效正则表达式
    """
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    从 URL 中提取域名
    
    Args:
        url: URL 地址
        
    Returns:
        域名或 None
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def mask_sensitive_info(text: str, mask_char: str = '*') -> str:
    """
    遮蔽敏感信息
    
    Args:
        text: 原始文本
        mask_char: 遮蔽字符
        
    Returns:
        遮蔽后的文本
    """
    if len(text) <= 4:
        return mask_char * len(text)
    
    # 保留前2位和后2位，中间用遮蔽字符替换
    return text[:2] + mask_char * (len(text) - 4) + text[-2:]


def ensure_dir_exists(path: Union[str, Path]) -> Path:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path 对象
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小（字节）
    """
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0


def is_port_available(port: int) -> bool:
    """
    检查端口是否可用
    
    Args:
        port: 端口号
        
    Returns:
        端口是否可用
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result != 0
    except Exception:
        return False


def generate_random_string(length: int = 8) -> str:
    """
    生成随机字符串
    
    Args:
        length: 字符串长度
        
    Returns:
        随机字符串
    """
    import random
    import string
    
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def parse_data_size(size_str: str) -> int:
    """
    解析数据大小字符串为字节数
    
    Args:
        size_str: 大小字符串，如 "1GB", "500MB"
        
    Returns:
        字节数
    """
    size_str = size_str.upper().strip()
    
    # 单位映射
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5
    }
    
    # 提取数字和单位
    match = re.match(r'(\d+(?:\.\d+)?)\s*([A-Z]{1,2})?', size_str)
    if not match:
        return 0
    
    number, unit = match.groups()
    number = float(number)
    unit = unit or 'B'
    
    if unit in units:
        return int(number * units[unit])
    else:
        return 0


def format_duration(seconds: int) -> str:
    """
    格式化时间长度
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}天{hours}小时"


def is_valid_port(port: Union[str, int]) -> bool:
    """
    验证端口号是否有效
    
    Args:
        port: 端口号
        
    Returns:
        是否为有效端口
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


def get_client_ip(request) -> str:
    """
    获取客户端 IP 地址
    
    Args:
        request: FastAPI Request 对象
        
    Returns:
        客户端 IP 地址
    """
    # 检查代理头
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    return request.client.host if request.client else '0.0.0.0'


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径（可选）
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 基础配置
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format
    )
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)