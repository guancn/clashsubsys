#!/bin/bash

# ============================================================
# 生产环境完整部署脚本
# 用途：在全新VPS上一键部署Clash订阅转换服务
# 支持：SSL证书、Docker容器、Nginx代理、监控等
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN_NAME="${1:-news.guancn.me}"
SSL_EMAIL="${2:-admin@guancn.me}"
APP_DIR="/opt/clash-converter"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 错误处理
handle_error() {
    log_error "部署过程中发生错误，正在清理..."
    cleanup_on_failure
    exit 1
}

trap handle_error ERR

# 显示帮助信息
show_help() {
    echo "用法: $0 [domain_name] [ssl_email]"
    echo ""
    echo "参数:"
    echo "  domain_name  域名 (默认: news.guancn.me)"
    echo "  ssl_email    SSL证书邮箱 (默认: admin@guancn.me)"
    echo ""
    echo "示例:"
    echo "  $0 news.guancn.me admin@guancn.me"
    echo "  $0 example.com user@example.com"
    exit 0
}

# 检查参数
check_parameters() {
    if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_help
    fi
    
    log_info "部署参数:"
    log_info "  域名: $DOMAIN_NAME"
    log_info "  SSL邮箱: $SSL_EMAIL"
    log_info "  应用目录: $APP_DIR"
}

# 预检查
pre_deployment_checks() {
    log_step "执行部署前检查..."
    
    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
    
    # 检查Docker和Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先运行 setup-fresh-vps.sh"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先运行 setup-fresh-vps.sh"
        exit 1
    fi
    
    # 检查Nginx
    if ! command -v nginx &> /dev/null; then
        log_error "Nginx未安装，请先运行 setup-fresh-vps.sh"
        exit 1
    fi
    
    # 检查Certbot
    if ! command -v certbot &> /dev/null; then
        log_error "Certbot未安装，请先运行 setup-fresh-vps.sh"
        exit 1
    fi
    
    # 检查域名解析
    log_info "检查域名解析..."
    local domain_ip=$(dig +short "$DOMAIN_NAME" | tail -1)
    local server_ip=$(curl -s https://ipinfo.io/ip || curl -s https://api.ipify.org)
    
    if [[ "$domain_ip" != "$server_ip" ]]; then
        log_warn "域名解析可能不正确"
        log_warn "  域名IP: $domain_ip"
        log_warn "  服务器IP: $server_ip"
        read -p "是否继续部署？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    else
        log_success "域名解析正确"
    fi
    
    log_success "部署前检查完成"
}

# 创建生产环境配置
create_production_config() {
    log_step "创建生产环境配置..."
    
    # 创建.env.production文件
    cat > "$SCRIPT_DIR/.env.production" << EOF
# 生产环境配置
NODE_ENV=production
ENVIRONMENT=production

# 域名配置
DOMAIN_NAME=$DOMAIN_NAME
SSL_EMAIL=$SSL_EMAIL

# 应用端口
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# 应用配置
APP_NAME=Clash订阅转换服务
APP_VERSION=2.0.0
APP_DEBUG=false

# 安全配置
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)

# 数据库配置（如需要）
# DATABASE_URL=postgresql://user:password@localhost:5432/clash_converter

# Redis配置（如需要）
# REDIS_URL=redis://localhost:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/clash-converter/app.log

# 性能配置
WORKERS=4
MAX_CONNECTIONS=1000
TIMEOUT=60

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090

# 备份配置
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
EOF
    
    log_success "生产环境配置创建完成"
}

# 创建Docker Compose生产配置
create_docker_compose_production() {
    log_step "创建Docker Compose生产配置..."
    
    cat > "$SCRIPT_DIR/docker-compose.production.yml" << 'EOF'
version: '3.8'

# 生产环境Docker Compose配置
# 适用于news.guancn.me域名部署

services:
  # 后端服务 - FastAPI
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      args:
        - ENV=production
    container_name: clash-converter-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - WORKERS=4
    volumes:
      - ./backend/config.yaml:/app/config.yaml:ro
      - ./logs/backend:/app/logs
      - ./data:/app/data
    networks:
      - clash-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 前端服务 - Vue.js
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_BASE_URL=https://news.guancn.me/api
        - VITE_APP_ENV=production
    container_name: clash-converter-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:8080"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - clash-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.2'
          memory: 256M
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /var/cache/nginx:noexec,nosuid,size=100m
      - /var/run:noexec,nosuid,size=10m
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 监控服务 - Prometheus (可选)
  monitoring:
    image: prom/prometheus:latest
    container_name: clash-converter-monitoring
    restart: unless-stopped
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - clash-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 128M
    security_opt:
      - no-new-privileges:true

networks:
  clash-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
    driver_opts:
      com.docker.network.bridge.name: clash-bridge
      com.docker.network.bridge.enable_icc: "true"
      com.docker.network.bridge.enable_ip_masquerade: "true"

volumes:
  prometheus_data:
    driver: local
EOF
    
    log_success "Docker Compose生产配置创建完成"
}

# 设置SSL证书
setup_ssl_certificate() {
    log_step "设置SSL证书..."
    
    # 创建certbot web root目录
    sudo mkdir -p /var/www/certbot
    sudo chown www-data:www-data /var/www/certbot
    
    # 临时Nginx配置用于证书获取
    sudo tee /etc/nginx/sites-available/temp-ssl << EOF > /dev/null
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }
    
    location / {
        return 200 'SSL证书获取中，请稍候...';
        add_header Content-Type text/plain;
    }
}
EOF
    
    # 启用临时配置
    sudo ln -sf /etc/nginx/sites-available/temp-ssl /etc/nginx/sites-enabled/temp-ssl
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # 测试Nginx配置并重载
    sudo nginx -t && sudo systemctl reload nginx
    
    # 获取SSL证书
    log_info "正在获取SSL证书..."
    if sudo certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$SSL_EMAIL" \
        --agree-tos \
        --non-interactive \
        --domains "$DOMAIN_NAME,www.$DOMAIN_NAME"; then
        log_success "SSL证书获取成功"
    else
        log_error "SSL证书获取失败"
        exit 1
    fi
    
    # 设置证书自动续期
    (sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -
    
    log_success "SSL证书设置完成"
}

# 配置Nginx
setup_nginx() {
    log_step "配置Nginx..."
    
    # 复制生产Nginx配置
    sudo cp "$SCRIPT_DIR/nginx-production.conf" /etc/nginx/sites-available/clash-converter
    
    # 删除临时配置
    sudo rm -f /etc/nginx/sites-enabled/temp-ssl
    sudo rm -f /etc/nginx/sites-available/temp-ssl
    
    # 启用新配置
    sudo ln -sf /etc/nginx/sites-available/clash-converter /etc/nginx/sites-enabled/clash-converter
    
    # 测试配置
    if sudo nginx -t; then
        sudo systemctl reload nginx
        log_success "Nginx配置完成"
    else
        log_error "Nginx配置测试失败"
        exit 1
    fi
}

# 部署应用
deploy_application() {
    log_step "部署应用..."
    
    # 创建必要目录
    mkdir -p logs/{backend,frontend,nginx}
    mkdir -p data/cache
    mkdir -p monitoring
    
    # 创建Prometheus配置
    cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'clash-converter'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF
    
    # 构建和启动服务
    log_info "构建Docker镜像..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    log_info "启动服务..."
    docker-compose -f docker-compose.production.yml up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    local max_attempts=12
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s http://localhost:8000/health > /dev/null && \
           curl -f -s http://localhost:3000/ > /dev/null; then
            log_success "服务启动成功"
            break
        fi
        
        ((attempt++))
        log_info "等待服务启动... ($attempt/$max_attempts)"
        sleep 10
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "服务启动超时"
        docker-compose -f docker-compose.production.yml logs
        exit 1
    fi
}

# 设置监控和日志
setup_monitoring() {
    log_step "设置监控和日志..."
    
    # 创建logrotate配置
    sudo tee /etc/logrotate.d/clash-converter << 'EOF' > /dev/null
/opt/clash-converter/logs/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        docker-compose -f /opt/clash-converter/docker-compose.production.yml restart > /dev/null 2>&1 || true
    endscript
}
EOF
    
    # 创建系统监控脚本
    cat > monitor-system.sh << 'EOF'
#!/bin/bash
# 系统监控脚本

SERVICES=("clash-converter-backend" "clash-converter-frontend")
LOG_FILE="/var/log/clash-converter-monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

for service in "${SERVICES[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^$service$"; then
        log_message "WARNING: Service $service is not running"
        # 尝试重启服务
        cd /opt/clash-converter
        docker-compose -f docker-compose.production.yml restart "$service" >> "$LOG_FILE" 2>&1
    fi
done

# 检查磁盘空间
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    log_message "WARNING: Disk usage is $DISK_USAGE%"
fi

# 检查内存使用
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", ($3/$2)*100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    log_message "WARNING: Memory usage is $MEM_USAGE%"
fi
EOF
    
    chmod +x monitor-system.sh
    
    # 添加到定时任务
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/clash-converter/monitor-system.sh") | crontab -
    
    log_success "监控和日志设置完成"
}

# 设置备份
setup_backup() {
    log_step "设置备份..."
    
    # 创建备份脚本
    cat > backup-system.sh << 'EOF'
#!/bin/bash
# 系统备份脚本

BACKUP_DIR="/opt/backups/clash-converter"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/clash-converter"

mkdir -p "$BACKUP_DIR"

# 备份配置文件
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    "$APP_DIR"/*.yml \
    "$APP_DIR"/*.conf \
    "$APP_DIR"/.env* \
    /etc/nginx/sites-available/clash-converter

# 备份应用数据
if [ -d "$APP_DIR/data" ]; then
    tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" "$APP_DIR/data"
fi

# 清理旧备份 (保留30天)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] Backup completed: $BACKUP_DIR"
EOF
    
    chmod +x backup-system.sh
    
    # 添加到定时任务
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/clash-converter/backup-system.sh") | crontab -
    
    log_success "备份设置完成"
}

# 最终验证
final_verification() {
    log_step "执行最终验证..."
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f docker-compose.production.yml ps
    
    # 检查网站访问
    local tests=(
        "https://$DOMAIN_NAME/health"
        "https://$DOMAIN_NAME/docs"
        "https://$DOMAIN_NAME/"
    )
    
    for url in "${tests[@]}"; do
        if curl -f -s -k "$url" > /dev/null; then
            log_success "✓ $url - 访问正常"
        else
            log_error "✗ $url - 访问失败"
        fi
    done
    
    # SSL证书检查
    if openssl s_client -connect "$DOMAIN_NAME:443" -servername "$DOMAIN_NAME" < /dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        log_success "✓ SSL证书验证通过"
    else
        log_warn "⚠ SSL证书验证可能有问题"
    fi
    
    log_success "最终验证完成"
}

# 失败清理
cleanup_on_failure() {
    log_warn "正在清理失败的部署..."
    
    # 停止Docker容器
    docker-compose -f docker-compose.production.yml down 2>/dev/null || true
    
    # 恢复默认Nginx配置
    sudo rm -f /etc/nginx/sites-enabled/clash-converter
    sudo rm -f /etc/nginx/sites-enabled/temp-ssl
    sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
    sudo systemctl reload nginx 2>/dev/null || true
    
    log_info "清理完成"
}

# 显示部署结果
show_deployment_result() {
    log_step "部署结果"
    
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}              Clash订阅转换服务部署完成${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    
    echo -e "${BLUE}🌐 访问地址:${NC}"
    echo "  主页面:     https://$DOMAIN_NAME/"
    echo "  API文档:    https://$DOMAIN_NAME/docs"
    echo "  健康检查:   https://$DOMAIN_NAME/health"
    echo ""
    
    echo -e "${BLUE}📊 监控地址:${NC}"
    echo "  Prometheus: http://$DOMAIN_NAME:9090/ (内网访问)"
    echo ""
    
    echo -e "${BLUE}🔧 管理命令:${NC}"
    echo "  查看状态:   docker-compose -f docker-compose.production.yml ps"
    echo "  查看日志:   docker-compose -f docker-compose.production.yml logs -f"
    echo "  重启服务:   docker-compose -f docker-compose.production.yml restart"
    echo "  停止服务:   docker-compose -f docker-compose.production.yml stop"
    echo ""
    
    echo -e "${BLUE}📁 重要文件:${NC}"
    echo "  应用目录:   $APP_DIR"
    echo "  配置文件:   $APP_DIR/.env.production"
    echo "  Docker配置: $APP_DIR/docker-compose.production.yml"
    echo "  Nginx配置:  /etc/nginx/sites-available/clash-converter"
    echo "  SSL证书:    /etc/letsencrypt/live/$DOMAIN_NAME/"
    echo ""
    
    echo -e "${BLUE}🚨 注意事项:${NC}"
    echo "  ✅ SSL证书将自动续期"
    echo "  ✅ 日志自动轮转 (保留30天)"
    echo "  ✅ 系统监控已启用 (每5分钟检查)"
    echo "  ✅ 数据备份已设置 (每天凌晨2点)"
    echo ""
    
    echo -e "${YELLOW}🔗 相关命令:${NC}"
    echo "  SSL证书续期: sudo certbot renew"
    echo "  Nginx重载:   sudo systemctl reload nginx"
    echo "  查看监控:    tail -f /var/log/clash-converter-monitor.log"
    echo "  手动备份:    ./backup-system.sh"
    echo ""
}

# 主函数
main() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "         Clash订阅转换服务 - 生产环境部署脚本"
    echo "         Domain: $DOMAIN_NAME"
    echo "         Version: 2.0.0"
    echo "============================================================"
    echo -e "${NC}"
    
    # 检查参数
    check_parameters "$@"
    
    # 执行部署步骤
    pre_deployment_checks
    create_production_config
    create_docker_compose_production
    setup_ssl_certificate
    setup_nginx
    deploy_application
    setup_monitoring
    setup_backup
    final_verification
    show_deployment_result
    
    echo -e "${GREEN}🎉 部署完成！服务已在 https://$DOMAIN_NAME 上运行${NC}"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi