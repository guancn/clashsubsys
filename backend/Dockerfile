# 安全加固的生产级后端 Dockerfile
# 基于最小权限原则和多层安全防护

# 第一阶段：依赖构建阶段
FROM python:3.11-slim as builder

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip并安装依赖
RUN pip install --upgrade pip setuptools wheel

# 安装Python依赖（使用固定版本确保安全性）
RUN pip install --no-cache-dir \
    "fastapi==0.104.1" \
    "uvicorn[standard]==0.24.0" \
    "pydantic==2.5.0" \
    "httpx==0.25.2" \
    "aiofiles==23.2.1" \
    "python-multipart==0.0.6" \
    "pyyaml==6.0.1" \
    "requests==2.31.0" \
    "jinja2==3.1.2"

# 第二阶段：运行时镜像
FROM python:3.11-slim as runtime

# 安全标签
LABEL maintainer="Clash Converter Security Team" \
      version="1.0.0" \
      description="Clash订阅转换服务后端-安全加固版" \
      security.scan="true"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    USER_ID=10001 \
    GROUP_ID=10001

# 安装运行时依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get clean

# 创建非特权用户
RUN groupadd -g $GROUP_ID appuser && \
    useradd -r -u $USER_ID -g appuser -s /bin/false -c "App User" appuser

# 创建应用目录结构
RUN mkdir -p /app/logs /app/temp /app/config && \
    chown -R appuser:appuser /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 复制应用代码并设置权限
COPY --chown=appuser:appuser . .

# 移除不必要的文件
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + || true && \
    chmod -R 755 /app && \
    chmod 750 /app/logs /app/temp /app/config

# 切换到非特权用户
USER appuser

# 健康检查（改用非特权端口检查）
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 使用 dumb-init 作为PID 1，防止僵尸进程
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# 启动命令（非特权用户运行）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]