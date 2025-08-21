"""
API 路由 - 订阅转换接口
"""

import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, JSONResponse

from ..models.schemas import (
    ConversionRequest, ConversionResponse, HealthResponse,
    TargetFormat, ErrorResponse
)
from ..core.converter import SubscriptionConverter
from ..utils.helpers import validate_url, sanitize_filename

router = APIRouter()
converter = SubscriptionConverter()

# 存储转换结果的内存缓存（生产环境建议使用 Redis）
conversion_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/convert", response_model=ConversionResponse)
async def convert_subscription(request: ConversionRequest):
    """
    转换订阅接口
    
    接受订阅链接和配置参数，返回转换后的配置
    """
    try:
        # 验证输入参数
        if isinstance(request.url, list):
            for url in request.url:
                if not validate_url(url):
                    raise HTTPException(status_code=400, detail=f"无效的 URL: {url}")
        else:
            if not validate_url(request.url):
                raise HTTPException(status_code=400, detail=f"无效的 URL: {request.url}")
        
        # 执行转换
        result = await converter.convert_subscription(request)
        
        if result.success and result.config:
            # 生成配置 ID 并缓存结果
            config_id = hashlib.md5(str(request.url).encode()).hexdigest()[:12]
            
            conversion_cache[config_id] = {
                'config': result.config,
                'timestamp': datetime.now(),
                'nodes_count': result.nodes_count
            }
            
            # 生成下载链接
            result.download_url = f"/api/sub/{config_id}"
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convert", response_model=ConversionResponse)
async def convert_subscription_get(
    url: str = Query(..., description="订阅链接，多个链接用 | 分隔"),
    target: TargetFormat = Query(TargetFormat.CLASH, description="目标格式"),
    remote_config: Optional[str] = Query(None, description="远程配置规则地址"),
    include: Optional[str] = Query(None, description="节点包含过滤规则（正则）"),
    exclude: Optional[str] = Query(None, description="节点排除过滤规则（正则）"),
    rename: Optional[str] = Query(None, description="节点重命名规则"),
    emoji: bool = Query(True, description="是否添加 Emoji"),
    udp: bool = Query(True, description="是否启用 UDP"),
    tfo: bool = Query(False, description="是否启用 TCP Fast Open"),
    scv: bool = Query(False, description="是否跳过证书验证"),
    fdn: bool = Query(False, description="是否过滤非默认端口"),
    sort: bool = Query(False, description="是否按节点名排序")
):
    """
    GET 方式转换订阅接口（兼容 subconverter API）
    
    支持通过 URL 参数传递转换配置
    """
    try:
        # 解析 URL 列表
        url_list = [u.strip() for u in url.split('|') if u.strip()]
        
        # 构建转换请求
        request = ConversionRequest(
            url=url_list,
            target=target,
            remote_config=remote_config,
            include=include,
            exclude=exclude,
            rename=rename,
            emoji=emoji,
            udp=udp,
            tfo=tfo,
            scv=scv,
            fdn=fdn,
            sort=sort
        )
        
        return await convert_subscription(request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sub/{config_id}")
async def download_config(
    config_id: str,
    format: Optional[str] = Query(None, description="输出格式: yaml/json"),
    filename: Optional[str] = Query(None, description="文件名")
):
    """
    下载转换后的配置文件
    
    Args:
        config_id: 配置 ID
        format: 输出格式（yaml 或 json）
        filename: 自定义文件名
    """
    if config_id not in conversion_cache:
        raise HTTPException(status_code=404, detail="配置不存在或已过期")
    
    cached_data = conversion_cache[config_id]
    config_content = cached_data['config']
    
    # 确定响应格式
    if format == 'json':
        import yaml
        try:
            config_dict = yaml.safe_load(config_content)
            return JSONResponse(content=config_dict)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"配置格式转换失败: {str(e)}")
    
    # 默认返回 YAML 格式
    response = PlainTextResponse(
        content=config_content,
        media_type="text/plain; charset=utf-8"
    )
    
    # 设置下载文件名
    if filename:
        safe_filename = sanitize_filename(filename)
    else:
        safe_filename = f"clash_config_{config_id}.yaml"
    
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    
    return response


@router.get("/sub/{config_id}/info")
async def get_config_info(config_id: str):
    """
    获取配置信息
    
    Args:
        config_id: 配置 ID
    """
    if config_id not in conversion_cache:
        raise HTTPException(status_code=404, detail="配置不存在或已过期")
    
    cached_data = conversion_cache[config_id]
    
    return {
        "config_id": config_id,
        "nodes_count": cached_data['nodes_count'],
        "created_at": cached_data['timestamp'].isoformat(),
        "download_url": f"/api/sub/{config_id}"
    }


@router.get("/features")
async def get_supported_features():
    """
    获取支持的功能特性
    """
    return converter.get_clash_meta_features()


@router.get("/protocols")
async def get_supported_protocols():
    """
    获取支持的协议列表
    """
    features = converter.get_clash_meta_features()
    return {
        "protocols": features["supported_protocols"],
        "networks": features["supported_networks"],
        "proxy_groups": features["proxy_group_types"]
    }


@router.post("/validate")
async def validate_subscription_url(urls: list[str]):
    """
    验证订阅链接有效性
    
    Args:
        urls: 要验证的订阅链接列表
    """
    results = []
    
    for url in urls:
        try:
            if not validate_url(url):
                results.append({
                    "url": url,
                    "valid": False,
                    "error": "URL 格式无效"
                })
                continue
            
            # 尝试获取订阅内容（仅获取头部信息）
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(url, follow_redirects=True)
                
                results.append({
                    "url": url,
                    "valid": response.status_code == 200,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": response.headers.get("content-length", "")
                })
                
        except Exception as e:
            results.append({
                "url": url,
                "valid": False,
                "error": str(e)
            })
    
    return {"results": results}


@router.delete("/cache/{config_id}")
async def delete_cached_config(config_id: str):
    """
    删除缓存的配置
    
    Args:
        config_id: 配置 ID
    """
    if config_id in conversion_cache:
        del conversion_cache[config_id]
        return {"message": "配置已删除"}
    else:
        raise HTTPException(status_code=404, detail="配置不存在")


@router.get("/cache/stats")
async def get_cache_stats():
    """
    获取缓存统计信息
    """
    return {
        "cached_configs": len(conversion_cache),
        "total_memory_mb": len(str(conversion_cache)) / (1024 * 1024)
    }


@router.post("/cache/clear")
async def clear_cache():
    """
    清空所有缓存
    """
    global conversion_cache
    conversion_cache.clear()
    return {"message": "缓存已清空"}


# 注意：异常处理器应该在main.py中注册到FastAPI应用上，而不是在路由器上