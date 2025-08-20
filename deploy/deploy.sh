#!/bin/bash

# Clash 订阅转换服务部署脚本
# 支持用户自定义端口配置

set -e

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认配置
DEFAULT_BACKEND_PORT=8000
DEFAULT_FRONTEND_PORT=3000
DEFAULT_NGINX_PORT=80
DEFAULT_NGINX_HTTPS_PORT=443
DEFAULT_DOMAIN="localhost"

# 读取用户配置
read_config() {
    log_info "开始配置服务端口..."
    
    read -p "后端服务端口 (默认 $DEFAULT_BACKEND_PORT): " BACKEND_PORT
    BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}
    
    read -p "前端服务端口 (默认 $DEFAULT_FRONTEND_PORT): " FRONTEND_PORT
    FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}
    
    read -p "Nginx HTTP 端口 (默认 $DEFAULT_NGINX_PORT): " NGINX_PORT
    NGINX_PORT=${NGINX_PORT:-$DEFAULT_NGINX_PORT}
    
    read -p "Nginx HTTPS 端口 (默认 $DEFAULT_NGINX_HTTPS_PORT): " NGINX_HTTPS_PORT
    NGINX_HTTPS_PORT=${NGINX_HTTPS_PORT:-$DEFAULT_NGINX_HTTPS_PORT}
    
    read -p "域名 (默认 $DEFAULT_DOMAIN): " DOMAIN
    DOMAIN=${DOMAIN:-$DEFAULT_DOMAIN}
    
    read -p "是否启用 HTTPS? (y/N): " ENABLE_HTTPS
    ENABLE_HTTPS=${ENABLE_HTTPS:-n}
    
    # 写入环境变量文件
    cat > .env <<EOF
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
NGINX_PORT=$NGINX_PORT
NGINX_HTTPS_PORT=$NGINX_HTTPS_PORT
DOMAIN=$DOMAIN
ENABLE_HTTPS=$ENABLE_HTTPS
EOF
    
    log_success "配置已保存到 .env 文件"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查端口占用
    check_port() {
        local port=$1
        local service=$2
        if ss -tlnp | grep ":$port " &> /dev/null; then
            log_warning "$service 端口 $port 已被占用，请检查或更换端口"
        fi
    }
    
    check_port $NGINX_PORT "Nginx HTTP"
    if [[ $ENABLE_HTTPS == "y" || $ENABLE_HTTPS == "Y" ]]; then
        check_port $NGINX_HTTPS_PORT "Nginx HTTPS"
    fi
    
    log_success "依赖检查完成"
}

# 生成 Nginx 配置
generate_nginx_config() {
    log_info "生成 Nginx 配置文件..."
    
    # 复制模板并替换变量
    sed "s/localhost:8000/backend:8000/g; \
         s/localhost:3000/frontend:80/g; \
         s/listen 80;/listen $NGINX_PORT;/g; \
         s/listen \[::\]:80;/listen [::]:$NGINX_PORT;/g; \
         s/server_name localhost your-domain.com;/server_name $DOMAIN;/g" \
         deploy/nginx.conf > deploy/nginx-generated.conf
    
    # 如果启用 HTTPS，生成 SSL 配置
    if [[ $ENABLE_HTTPS == "y" || $ENABLE_HTTPS == "Y" ]]; then
        log_info "启用 HTTPS 配置..."
        
        # 检查 SSL 证书目录
        mkdir -p deploy/ssl
        
        if [[ ! -f deploy/ssl/cert.pem || ! -f deploy/ssl/key.pem ]]; then
            log_warning "SSL 证书文件不存在，生成自签名证书用于测试..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout deploy/ssl/key.pem \
                -out deploy/ssl/cert.pem \
                -subj "/C=CN/ST=State/L=City/O=Organization/OU=OrgUnit/CN=$DOMAIN"
            
            log_warning "已生成自签名证书，生产环境请使用正式证书"
        fi
        
        # 更新 HTTPS 端口配置
        sed -i "s/listen 443 ssl http2;/listen $NGINX_HTTPS_PORT ssl http2;/g; \
                s/listen \[::\]:443 ssl http2;/listen [::]:$NGINX_HTTPS_PORT ssl http2;/g" \
                deploy/nginx-generated.conf
        
        # 取消 HTTP 到 HTTPS 重定向的注释
        sed -i '/# HTTP 重定向到 HTTPS/,/# }/ s/^# //' deploy/nginx-generated.conf
        sed -i "s/return 301 https:\/\/\$server_name\$request_uri;/return 301 https:\/\/$DOMAIN:$NGINX_HTTPS_PORT\$request_uri;/g" deploy/nginx-generated.conf
    fi
    
    log_success "Nginx 配置文件已生成"
}

# 构建和启动服务
start_services() {
    log_info "构建和启动服务..."
    
    # 设置环境变量
    export BACKEND_PORT
    export FRONTEND_PORT  
    export NGINX_PORT
    export NGINX_HTTPS_PORT
    export DOMAIN
    export ENABLE_HTTPS
    
    # 使用 Docker Compose 启动服务
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi
    
    log_success "服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    sleep 10  # 等待服务启动
    
    # 检查后端服务
    if curl -f http://localhost:$NGINX_PORT/api/health &> /dev/null; then
        log_success "后端服务运行正常"
    else
        log_error "后端服务异常，请检查日志"
        return 1
    fi
    
    # 检查前端服务
    if curl -f http://localhost:$NGINX_PORT/ &> /dev/null; then
        log_success "前端服务运行正常"
    else
        log_error "前端服务异常，请检查日志"
        return 1
    fi
    
    # 检查 HTTPS（如果启用）
    if [[ $ENABLE_HTTPS == "y" || $ENABLE_HTTPS == "Y" ]]; then
        if curl -k -f https://localhost:$NGINX_HTTPS_PORT/ &> /dev/null; then
            log_success "HTTPS 服务运行正常"
        else
            log_warning "HTTPS 服务可能有问题，请检查证书配置"
        fi
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "Clash 订阅转换服务部署完成！"
    echo
    echo "=============================="
    echo "      服务访问地址"
    echo "=============================="
    echo "前端访问地址: http://$DOMAIN:$NGINX_PORT"
    
    if [[ $ENABLE_HTTPS == "y" || $ENABLE_HTTPS == "Y" ]]; then
        echo "HTTPS 访问地址: https://$DOMAIN:$NGINX_HTTPS_PORT"
    fi
    
    echo "API 文档地址: http://$DOMAIN:$NGINX_PORT/docs"
    echo "健康检查地址: http://$DOMAIN:$NGINX_PORT/api/health"
    echo
    echo "=============================="
    echo "      管理命令"
    echo "=============================="
    echo "查看服务状态: docker-compose ps"
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
    echo "重启服务: docker-compose restart"
    echo "更新服务: docker-compose pull && docker-compose up -d"
    echo
    echo "配置文件位置:"
    echo "- 环境变量: .env"
    echo "- Nginx 配置: deploy/nginx-generated.conf"
    echo "- SSL 证书: deploy/ssl/"
    echo
    if [[ $ENABLE_HTTPS == "y" || $ENABLE_HTTPS == "Y" ]] && [[ -f deploy/ssl/cert.pem ]]; then
        echo "注意: 当前使用的是自签名证书，浏览器可能显示安全警告"
        echo "生产环境请使用正式的 SSL 证书"
    fi
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    rm -f deploy/nginx-generated.conf
}

# 主函数
main() {
    log_info "开始部署 Clash 订阅转换服务..."
    
    # 检查是否存在配置文件
    if [[ -f .env ]]; then
        log_info "发现现有配置文件 .env"
        read -p "是否使用现有配置? (Y/n): " USE_EXISTING
        USE_EXISTING=${USE_EXISTING:-y}
        
        if [[ $USE_EXISTING == "y" || $USE_EXISTING == "Y" ]]; then
            source .env
            log_info "已加载现有配置"
        else
            read_config
        fi
    else
        read_config
    fi
    
    # 执行部署步骤
    check_dependencies
    generate_nginx_config
    start_services
    check_services && show_deployment_info
    
    # 注册清理函数
    trap cleanup EXIT
}

# 处理命令行参数
case "${1:-}" in
    "start")
        log_info "启动服务..."
        if command -v docker-compose &> /dev/null; then
            docker-compose up -d
        else
            docker compose up -d
        fi
        ;;
    "stop")
        log_info "停止服务..."
        if command -v docker-compose &> /dev/null; then
            docker-compose down
        else
            docker compose down
        fi
        ;;
    "restart")
        log_info "重启服务..."
        if command -v docker-compose &> /dev/null; then
            docker-compose restart
        else
            docker compose restart
        fi
        ;;
    "logs")
        if command -v docker-compose &> /dev/null; then
            docker-compose logs -f
        else
            docker compose logs -f
        fi
        ;;
    "status")
        if command -v docker-compose &> /dev/null; then
            docker-compose ps
        else
            docker compose ps
        fi
        ;;
    "clean")
        log_warning "这将删除所有容器和数据，确定继续吗? (y/N)"
        read -r confirmation
        if [[ $confirmation == "y" || $confirmation == "Y" ]]; then
            if command -v docker-compose &> /dev/null; then
                docker-compose down -v --rmi all
            else
                docker compose down -v --rmi all
            fi
            log_success "清理完成"
        fi
        ;;
    "update")
        log_info "更新服务..."
        if command -v docker-compose &> /dev/null; then
            docker-compose pull && docker-compose up -d
        else
            docker compose pull && docker compose up -d
        fi
        ;;
    *)
        main
        ;;
esac