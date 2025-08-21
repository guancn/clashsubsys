#!/bin/bash

# Clash 订阅转换服务 - 生产环境部署脚本
# 与现有 subconverter+sub-web 系统共存部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用 root 用户运行此脚本"
        exit 1
    fi
}

# 检查 Docker 和 Docker Compose
check_docker() {
    log_info "检查 Docker 环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查 Docker 服务状态
    if ! sudo systemctl is-active --quiet docker; then
        log_error "Docker 服务未运行，请启动 Docker 服务"
        exit 1
    fi
    
    log_success "Docker 环境检查完成"
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用情况..."
    
    local ports=(8001 3001)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if ss -tlnp | grep -q ":${port} "; then
            occupied_ports+=($port)
        fi
    done
    
    if [ ${#occupied_ports[@]} -ne 0 ]; then
        log_error "以下端口被占用: ${occupied_ports[*]}"
        log_info "请检查并释放这些端口，或修改 .env.production 文件中的端口配置"
        exit 1
    fi
    
    log_success "端口检查完成，8001 和 3001 端口可用"
}

# 检查现有系统
check_existing_system() {
    log_info "检查现有 subconverter 系统..."
    
    # 检查现有系统端口
    if ! ss -tlnp | grep -q ":25500 " || ! ss -tlnp | grep -q ":8080 "; then
        log_warning "现有 subconverter 系统似乎未运行"
        log_warning "端口 25500 (subconverter) 或 8080 (sub-web) 未被占用"
        
        read -p "是否继续部署? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    else
        log_success "现有系统正常运行，端口 25500 和 8080 已占用"
    fi
}

# 备份现有 Nginx 配置
backup_nginx_config() {
    local nginx_config="/etc/nginx/sites-available/sub.guancn.me"
    
    if [ -f "$nginx_config" ]; then
        log_info "备份现有 Nginx 配置..."
        sudo cp "$nginx_config" "${nginx_config}.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "Nginx 配置已备份"
    else
        log_warning "未找到现有 Nginx 配置文件: $nginx_config"
    fi
}

# 更新 Nginx 配置
update_nginx_config() {
    log_info "更新 Nginx 配置以支持双系统..."
    
    local nginx_config="/etc/nginx/sites-available/sub.guancn.me"
    local new_config="./deploy/nginx-production.conf"
    
    if [ ! -f "$new_config" ]; then
        log_error "新的 Nginx 配置文件不存在: $new_config"
        exit 1
    fi
    
    # 复制新配置
    sudo cp "$new_config" "$nginx_config"
    
    # 测试 Nginx 配置
    if sudo nginx -t; then
        log_success "Nginx 配置测试通过"
        
        # 重载 Nginx
        sudo systemctl reload nginx
        log_success "Nginx 配置已更新并重载"
    else
        log_error "Nginx 配置测试失败，正在恢复备份..."
        
        # 恢复备份
        local backup_file=$(ls ${nginx_config}.backup.* | tail -1)
        if [ -f "$backup_file" ]; then
            sudo cp "$backup_file" "$nginx_config"
            sudo systemctl reload nginx
            log_info "已恢复备份配置"
        fi
        
        exit 1
    fi
}

# 构建和启动服务
deploy_services() {
    log_info "构建和启动 Clash 转换器服务..."
    
    # 复制生产环境配置
    cp .env.production .env
    
    # 构建和启动服务
    docker-compose -f docker-compose.production.yml up -d --build
    
    log_success "服务部署完成"
}

# 验证服务状态
verify_services() {
    log_info "验证服务状态..."
    
    sleep 10  # 等待服务启动
    
    local services=("clash-converter-backend:8001" "clash-converter-frontend:3001")
    local failed_services=()
    
    for service in "${services[@]}"; do
        local name=${service%:*}
        local port=${service#*:}
        
        if docker ps | grep -q "$name"; then
            if ss -tlnp | grep -q ":${port} "; then
                log_success "$name 服务运行正常 (端口 $port)"
            else
                log_error "$name 服务端口 $port 未监听"
                failed_services+=($name)
            fi
        else
            log_error "$name 容器未运行"
            failed_services+=($name)
        fi
    done
    
    if [ ${#failed_services[@]} -ne 0 ]; then
        log_error "以下服务部署失败: ${failed_services[*]}"
        log_info "查看服务日志:"
        docker-compose -f docker-compose.production.yml logs
        exit 1
    fi
    
    log_success "所有服务运行正常"
}

# 测试 API 接口
test_api() {
    log_info "测试 API 接口..."
    
    # 测试健康检查
    if curl -f -s "http://127.0.0.1:8001/health" > /dev/null; then
        log_success "后端 API 健康检查通过"
    else
        log_error "后端 API 健康检查失败"
        exit 1
    fi
    
    # 测试前端访问
    if curl -f -s "http://127.0.0.1:3001/" > /dev/null; then
        log_success "前端服务访问正常"
    else
        log_error "前端服务访问失败"
        exit 1
    fi
    
    # 测试通过 Nginx 的路由
    if curl -f -s "https://sub.guancn.me/clash/api/health" > /dev/null; then
        log_success "通过 Nginx 的 API 路由测试通过"
    else
        log_warning "通过 Nginx 的 API 路由测试失败，请检查 SSL 证书和 Nginx 配置"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "=== Clash 订阅转换服务部署完成 ==="
    echo
    echo "📊 服务信息:"
    echo "  • 后端服务: http://127.0.0.1:8001"
    echo "  • 前端服务: http://127.0.0.1:3001"
    echo
    echo "🌐 访问地址:"
    echo "  • Clash 转换器: https://sub.guancn.me/clash/"
    echo "  • Clash API: https://sub.guancn.me/clash/api/"
    echo "  • 原有系统: https://sub.guancn.me/"
    echo "  • 原有 API: https://sub.guancn.me/sub"
    echo
    echo "🐳 Docker 管理命令:"
    echo "  • 查看状态: docker-compose -f docker-compose.production.yml ps"
    echo "  • 查看日志: docker-compose -f docker-compose.production.yml logs -f"
    echo "  • 停止服务: docker-compose -f docker-compose.production.yml down"
    echo "  • 重启服务: docker-compose -f docker-compose.production.yml restart"
    echo
    echo "📝 重要提示:"
    echo "  • 新系统与现有系统完全独立，不会相互影响"
    echo "  • 原有的 subconverter+sub-web 系统继续正常运行"
    echo "  • 如需卸载，运行: ./deploy/uninstall.sh --docker-only"
    echo
}

# 主函数
main() {
    echo "========================================="
    echo "  Clash 订阅转换服务 - 生产环境部署"
    echo "  与现有系统共存部署方案"
    echo "========================================="
    echo
    
    # 检查系统环境
    check_root
    check_docker
    check_existing_system
    check_ports
    
    # 确认部署
    echo "📋 部署概要:"
    echo "  • 新系统端口: 8001 (后端), 3001 (前端)"
    echo "  • 访问路径: /clash/ (前端), /clash/api/ (后端)"
    echo "  • 现有系统: 保持不变"
    echo
    
    read -p "确认开始部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
    
    # 执行部署
    backup_nginx_config
    update_nginx_config
    deploy_services
    verify_services
    test_api
    show_deployment_info
    
    log_success "🎉 部署完成！您现在可以访问两套转换系统了！"
}

# 执行主函数
main "$@"