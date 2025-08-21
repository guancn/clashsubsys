# 最简化的生产 Dockerfile

FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip

# 直接安装核心依赖，不使用 requirements.txt
RUN pip install --no-cache-dir \
    "fastapi>=0.100.0" \
    "uvicorn[standard]>=0.20.0" \
    "pydantic>=2.0.0" \
    "httpx>=0.24.0" \
    "aiofiles>=23.0.0" \
    "python-multipart>=0.0.6" \
    "pyyaml>=6.0" \
    "requests>=2.28.0" \
    "jinja2>=3.1.0"

# 创建必要目录
RUN mkdir -p /app/logs /app/temp /app/config

# 复制应用代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]