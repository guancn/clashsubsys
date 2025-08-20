"""
FastAPI 应用主入口
提供 Clash 订阅转换服务的 REST API
"""

import os
import yaml
import logging
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .api.converter import router as converter_router
from .models.schemas import HealthResponse, ErrorResponse
from .utils.helpers import setup_logging, get_client_ip

# 配置日志
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/app.log"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 Clash 订阅转换服务启动")
    
    # 确保必要目录存在
    os.makedirs("logs", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    yield
    
    # 关闭时执行
    logger.info("🛑 Clash 订阅转换服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Clash 订阅转换服务",
    description="""
    一个强大的 Clash 代理订阅转换服务
    
    ## 功能特性
    
    * **多协议支持**: SS、SSR、V2Ray、Trojan、Hysteria 等
    * **灵活配置**: 支持远程规则和自定义规则
    * **节点管理**: 节点过滤、重命名、排序
    * **现代化 API**: RESTful API 设计
    * **高性能**: 基于 FastAPI 和异步处理
    
    ## 使用方法
    
    ### 基础转换
    ```
    POST /api/convert
    {
        "url": ["订阅链接1", "订阅链接2"],
        "target": "clash",
        "emoji": true
    }
    ```
    
    ### URL 参数转换
    ```
    GET /api/convert?url=订阅链接&target=clash&emoji=true
    ```
    
    ### 下载配置
    ```
    GET /api/sub/{config_id}
    ```
    """,
    version="1.0.0",
    contact={
        "name": "开发者",
        "email": "dev@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 加载配置
config_path = Path("config.yaml")
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
else:
    config = {}

# CORS 中间件配置
cors_config = config.get('cors', {})
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.get('allow_origins', ["*"]),
    allow_credentials=True,
    allow_methods=cors_config.get('allow_methods', ["GET", "POST", "PUT", "DELETE"]),
    allow_headers=cors_config.get('allow_headers', ["*"]),
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    client_ip = get_client_ip(request)
    
    logger.info(f"📨 {request.method} {request.url.path} - {client_ip}")
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"📤 {response.status_code} - {process_time:.3f}s")
    
    return response

# 路由注册
app.include_router(converter_router, prefix="/api", tags=["订阅转换"])

# 根路径
@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向到文档"""
    return JSONResponse({
        "name": "Clash 订阅转换服务",
        "version": "1.0.0",
        "description": "一个强大的 Clash 代理订阅转换服务",
        "docs": "/docs",
        "health": "/health",
        "api": "/api"
    })

# 健康检查
@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """
    健康检查接口
    
    返回服务状态和基本信息
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

# 服务信息
@app.get("/info", tags=["系统"])
async def get_service_info():
    """
    获取服务信息
    
    返回详细的服务配置和状态信息
    """
    return {
        "service": {
            "name": "Clash 订阅转换服务",
            "version": "1.0.0",
            "description": "基于 FastAPI 的高性能订阅转换服务",
            "author": "开发团队",
            "license": "MIT"
        },
        "api": {
            "base_url": "/api",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json"
        },
        "features": {
            "supported_protocols": [
                "SS", "SSR", "VMess", "VLESS", "Trojan", 
                "Hysteria", "Hysteria2", "TUIC", "WireGuard"
            ],
            "supported_formats": ["Clash", "Surge", "Quantumult X"],
            "node_filters": True,
            "custom_rules": True,
            "remote_config": True,
            "emoji_support": True
        },
        "limits": {
            "max_subscription_size": "10MB",
            "max_nodes_per_subscription": 1000,
            "cache_ttl": "1小时",
            "request_timeout": "30秒"
        },
        "status": {
            "uptime": datetime.now().isoformat(),
            "timezone": "UTC",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    }

# 全局异常处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error_code="NOT_FOUND",
            message="请求的资源不存在",
            detail=f"路径 {request.url.path} 未找到"
        ).dict()
    )

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    return JSONResponse(
        status_code=405,
        content=ErrorResponse(
            error_code="METHOD_NOT_ALLOWED",
            message="请求方法不被允许",
            detail=f"路径 {request.url.path} 不支持 {request.method} 方法"
        ).dict()
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    logger.error(f"内部服务器错误: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="服务器内部错误",
            detail="请联系管理员或稍后重试"
        ).dict()
    )

# 启动消息
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 50)
    logger.info("🎉 Clash 订阅转换服务已启动")
    logger.info(f"📚 API 文档: http://localhost:8000/docs")
    logger.info(f"📖 ReDoc: http://localhost:8000/redoc")
    logger.info(f"🏥 健康检查: http://localhost:8000/health")
    logger.info(f"ℹ️ 服务信息: http://localhost:8000/info")
    logger.info("=" * 50)

if __name__ == "__main__":
    import uvicorn
    
    # 从配置文件读取服务器配置
    server_config = config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8000)
    debug = server_config.get('debug', False)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )