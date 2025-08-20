# Clash 订阅转换服务 - 完整部署手册

## 概述

本手册将指导您完成 Clash 订阅转换服务的完整部署，包括 Docker 容器化部署、传统部署以及 Nginx 反向代理配置。

## 📋 前置要求

### 系统要求
- **操作系统**: Ubuntu 18.04+ / CentOS 7+ / Debian 9+
- **内存**: 最少 512MB，推荐 1GB+
- **磁盘空间**: 最少 2GB，推荐 5GB+
- **网络**: 稳定的互联网连接

### 必需软件

#### Docker 部署（推荐）
- Docker 20.10+
- Docker Compose 2.0+

#### 传统部署
- Python 3.8+
- Node.js 16+
- Nginx 1.18+

## 🚀 快速部署（Docker）

### 1. 克隆项目

```bash
git clone <your-repository-url>
cd clash-sub-converter
```

### 2. 配置环境变量

复制并编辑环境变量文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置端口信息：

```bash
# 端口配置 - 可根据需要修改
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_PORT=80
NGINX_HTTPS_PORT=443

# 域名配置
DOMAIN=your-domain.com

# API 基础地址
API_BASE_URL=http://localhost:8000

# 日志级别
LOG_LEVEL=INFO
```

### 3. 运行部署脚本

使用提供的自动化部署脚本：

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

脚本会自动：
- 引导您配置端口和域名
- 检查系统依赖
- 生成 Nginx 配置
- 构建和启动服务
- 验证服务状态

### 4. 验证部署

访问以下地址验证服务：

- **前端**: http://your-domain.com:端口
- **API 文档**: http://your-domain.com:端口/docs
- **健康检查**: http://your-domain.com:端口/api/health

## 🔧 手动部署

### 1. Docker Compose 部署

#### 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: clash-converter-backend
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./backend/config.yaml:/app/config.yaml:ro
      - ./backend/logs:/app/logs
    networks:
      - clash-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: clash-converter-frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT:-3000}:80"
    depends_on:
      - backend
    networks:
      - clash-network

  nginx:
    image: nginx:alpine
    container_name: clash-converter-nginx
    restart: unless-stopped
    ports:
      - "${NGINX_PORT:-80}:80"
      - "${NGINX_HTTPS_PORT:-443}:443"
    volumes:
      - ./deploy/nginx-generated.conf:/etc/nginx/nginx.conf:ro
      - ./deploy/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - clash-network

networks:
  clash-network:
    driver: bridge
```

#### 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2. 传统部署方式

#### 后端部署

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 前端部署

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 使用 Nginx 提供静态文件服务
sudo cp -r dist/* /var/www/html/
```

## 🌐 Nginx 配置

### 1. 基础 Nginx 配置

创建 `/etc/nginx/sites-available/clash-converter`：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

### 2. 启用站点

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/clash-converter /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 3. HTTPS 配置（可选）

使用 Let's Encrypt 获取 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 性能优化

### 1. 系统级优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
sysctl -p
```

### 2. Nginx 性能优化

```nginx
# worker 进程数
worker_processes auto;

# 事件模型
events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # 开启 gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types text/css application/javascript application/json;
    
    # 缓存设置
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
    
    # 连接池
    upstream backend {
        server 127.0.0.1:8000;
        keepalive 32;
    }
}
```

### 3. 应用层优化

编辑 `backend/config.yaml`：

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4  # 根据 CPU 核心数调整
  
# 缓存配置  
cache:
  enabled: true
  ttl: 3600  # 1小时
  max_size: 1000  # 最大缓存项数
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# UFW 防火墙
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8000  # 如果需要直接访问后端
sudo ufw enable
```

### 2. Nginx 安全头

```nginx
# 安全头设置
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# 隐藏 Nginx 版本
server_tokens off;

# 限制请求大小
client_max_body_size 10M;

# 速率限制
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=5 nodelay;
```

### 3. 应用安全

```yaml
# backend/config.yaml 安全配置
security:
  # CORS 设置
  cors_origins: ["https://your-domain.com"]
  
  # API 限制
  rate_limit:
    enabled: true
    requests_per_minute: 60
    
  # 日志设置
  logging:
    level: "WARNING"  # 生产环境使用 WARNING 级别
    sensitive_data: false  # 不记录敏感数据
```

## 🔄 服务管理

### 1. Systemd 服务（传统部署）

创建 `/etc/systemd/system/clash-converter.service`：

```ini
[Unit]
Description=Clash Subscription Converter
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/opt/clash-converter/backend
Environment=PYTHONPATH=/opt/clash-converter/backend
ExecStart=/opt/clash-converter/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable clash-converter
sudo systemctl start clash-converter
sudo systemctl status clash-converter
```

### 2. Docker 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service-name]

# 更新服务
docker-compose pull
docker-compose up -d

# 清理资源
docker-compose down -v --rmi all
```

## 📈 监控和日志

### 1. 日志配置

后端日志位置：
- Docker: `docker-compose logs backend`
- 传统部署: `/opt/clash-converter/backend/logs/app.log`

Nginx 日志位置：
- 访问日志: `/var/log/nginx/access.log`
- 错误日志: `/var/log/nginx/error.log`

### 2. 健康检查

创建监控脚本 `/opt/scripts/health_check.sh`：

```bash
#!/bin/bash

# 检查后端服务
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "$(date): Backend service is healthy"
else
    echo "$(date): Backend service is down"
    # 重启服务
    systemctl restart clash-converter
fi

# 检查前端服务
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "$(date): Frontend service is healthy"
else
    echo "$(date): Frontend service is down"
    systemctl restart nginx
fi
```

设置定时任务：

```bash
# 每5分钟检查一次
*/5 * * * * /opt/scripts/health_check.sh >> /var/log/health_check.log 2>&1
```

## 🚨 故障排除

### 常见问题

#### 1. 端口被占用

```bash
# 查看端口占用
sudo netstat -tlnp | grep :8000

# 杀死占用进程
sudo kill -9 <PID>
```

#### 2. 权限问题

```bash
# 修复文件权限
sudo chown -R www-data:www-data /opt/clash-converter
sudo chmod -R 755 /opt/clash-converter
```

#### 3. 内存不足

```bash
# 检查内存使用
free -h

# 添加交换空间
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Docker 相关问题

```bash
# 重启 Docker
sudo systemctl restart docker

# 清理 Docker 资源
docker system prune -a

# 查看容器日志
docker logs -f <container-name>
```

### 日志分析

#### 查看关键日志

```bash
# 后端错误日志
tail -f /opt/clash-converter/backend/logs/error.log

# Nginx 错误日志
tail -f /var/log/nginx/error.log

# 系统日志
journalctl -u clash-converter -f
```

#### 常见错误码

- **500**: 后端服务异常，检查后端日志
- **502**: 后端服务无响应，检查服务状态
- **503**: 服务过载，检查资源使用情况
- **404**: 路由配置错误，检查 Nginx 配置

## 🔄 维护和更新

### 1. 定期维护

```bash
#!/bin/bash
# maintenance.sh - 维护脚本

# 清理日志文件（保留最近7天）
find /var/log -name "*.log" -mtime +7 -delete

# 清理缓存
rm -rf /tmp/clash-converter-cache/*

# 更新系统
sudo apt update && sudo apt upgrade -y

# 重启服务
sudo systemctl restart clash-converter nginx
```

### 2. 备份和恢复

```bash
# 备份配置文件
tar -czf clash-converter-backup-$(date +%Y%m%d).tar.gz \
    /opt/clash-converter/backend/config.yaml \
    /etc/nginx/sites-available/clash-converter \
    .env

# 恢复配置
tar -xzf clash-converter-backup-*.tar.gz -C /
```

### 3. 版本更新

```bash
# 使用 Docker
cd /opt/clash-converter
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# 传统部署
cd /opt/clash-converter
git pull origin main
source backend/venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart clash-converter

cd frontend
npm install
npm run build
sudo cp -r dist/* /var/www/html/
```

## 📞 支持和反馈

### 获取帮助

1. **文档**: 查看项目 README 和 API 文档
2. **日志**: 检查应用和系统日志
3. **社区**: 提交 Issue 到项目仓库

### 性能调优建议

1. **硬件要求**:
   - 2核 CPU，2GB 内存（推荐配置）
   - SSD 硬盘提升 I/O 性能

2. **网络优化**:
   - 使用 CDN 加速静态资源
   - 启用 HTTP/2 和 gzip 压缩

3. **缓存策略**:
   - API 响应缓存
   - 静态资源缓存
   - 浏览器缓存设置

---

## 🎯 快速参考

### 常用命令

```bash
# Docker 部署
./deploy/deploy.sh                    # 自动部署
docker-compose up -d                  # 启动服务
docker-compose logs -f                # 查看日志
docker-compose down                   # 停止服务

# 服务管理
sudo systemctl status clash-converter # 查看状态  
sudo systemctl restart nginx         # 重启 Nginx
sudo nginx -t                        # 测试配置

# 日志查看
tail -f /var/log/nginx/error.log     # Nginx 日志
journalctl -u clash-converter -f     # 服务日志
```

### 重要文件路径

```
/opt/clash-converter/              # 应用目录
/etc/nginx/sites-available/        # Nginx 配置
/var/log/nginx/                    # Nginx 日志
/etc/systemd/system/               # 系统服务
~/.env                            # 环境变量
```

通过本手册，您应该能够成功部署和管理 Clash 订阅转换服务。如遇问题，请参考故障排除部分或寻求技术支持。