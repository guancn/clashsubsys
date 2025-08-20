#!/bin/bash

# Clash 订阅转换服务 - 完整卸载脚本
# 安全地卸载项目对系统所做的所有修改

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
PROJECT_NAME="clash-sub-converter"
DEFAULT_INSTALL_PATH="/opt/clash-converter"
DEFAULT_WEB_ROOT="/var/www/html"

# 卸载选项
REMOVE_DOCKER_IMAGES=false
REMOVE_SYSTEM_CONFIGS=false
REMOVE_LOGS=false
REMOVE_SSL_CERTS=false
REMOVE_DEPENDENCIES=false
FORCE_REMOVE=false

# 显示卸载说明
show_uninstall_info() {
    log_info "Clash 订阅转换服务卸载程序"
    echo
    echo "此脚本将帮助您完整卸载 Clash 订阅转换服务及其相关组件。"
    echo "包括但不限于："
    echo "  - Docker 容器和镜像"
    echo "  - 系统服务配置"
    echo "  - Nginx 配置"
    echo "  - 日志文件"
    echo "  - SSL 证书"
    echo "  - 项目文件"
    echo
    echo "请根据提示选择要卸载的组件。"
    echo
}

# 确认操作
confirm_uninstall() {
    echo -e "${YELLOW}警告：此操作将删除项目相关的所有文件和配置！${NC}"
    read -p "确定要继续卸载吗？(y/N): " confirm
    
    if [[ $confirm != "y" && $confirm != "Y" ]]; then
        log_info "取消卸载操作"
        exit 0
    fi
}

# 检测部署方式
detect_deployment_type() {
    log_info "检测部署方式..."
    
    DEPLOYMENT_TYPE="unknown"
    
    # 检查 Docker Compose
    if [[ -f "docker-compose.yml" ]] && command -v docker-compose &> /dev/null; then
        DEPLOYMENT_TYPE="docker-compose"
        log_info "检测到 Docker Compose 部署"
    elif command -v docker &> /dev/null && docker ps -a | grep -q "clash-converter"; then
        DEPLOYMENT_TYPE="docker"
        log_info "检测到 Docker 部署"
    fi
    
    # 检查系统服务
    if systemctl is-active --quiet clash-converter-backend 2>/dev/null || \
       systemctl is-active --quiet clash-converter-frontend 2>/dev/null || \
       systemctl is-active --quiet clash-converter 2>/dev/null; then
        DEPLOYMENT_TYPE="systemd"
        log_info "检测到 Systemd 服务部署"
    fi
    
    # 检查 Supervisor
    if command -v supervisorctl &> /dev/null && \
       supervisorctl status | grep -q "clash-converter" 2>/dev/null; then
        DEPLOYMENT_TYPE="supervisor"
        log_info "检测到 Supervisor 部署"
    fi
    
    if [[ $DEPLOYMENT_TYPE == "unknown" ]]; then
        log_warning "未检测到标准部署，将进行通用清理"
    fi
}

# 获取用户选择
get_user_options() {
    log_info "请选择要卸载的组件："
    echo
    
    read -p "是否删除 Docker 镜像？(y/N): " remove_images
    [[ $remove_images == "y" || $remove_images == "Y" ]] && REMOVE_DOCKER_IMAGES=true
    
    read -p "是否删除系统配置文件？(y/N): " remove_configs
    [[ $remove_configs == "y" || $remove_configs == "Y" ]] && REMOVE_SYSTEM_CONFIGS=true
    
    read -p "是否删除日志文件？(y/N): " remove_logs
    [[ $remove_logs == "y" || $remove_logs == "Y" ]] && REMOVE_LOGS=true
    
    read -p "是否删除 SSL 证书？(y/N): " remove_ssl
    [[ $remove_ssl == "y" || $remove_ssl == "Y" ]] && REMOVE_SSL_CERTS=true
    
    read -p "是否卸载相关依赖包？(谨慎操作) (y/N): " remove_deps
    [[ $remove_deps == "y" || $remove_deps == "Y" ]] && REMOVE_DEPENDENCIES=true
    
    read -p "强制删除所有相关文件？(y/N): " force_remove
    [[ $force_remove == "y" || $force_remove == "Y" ]] && FORCE_REMOVE=true
}

# 停止服务
stop_services() {
    log_info "停止运行中的服务..."
    
    case $DEPLOYMENT_TYPE in
        "docker-compose")
            if [[ -f "docker-compose.yml" ]]; then
                log_info "停止 Docker Compose 服务..."
                if command -v docker-compose &> /dev/null; then
                    docker-compose down -v 2>/dev/null || true
                else
                    docker compose down -v 2>/dev/null || true
                fi
            fi
            ;;
            
        "docker")
            log_info "停止 Docker 容器..."
            docker stop clash-converter-backend clash-converter-frontend clash-converter-nginx 2>/dev/null || true
            docker rm clash-converter-backend clash-converter-frontend clash-converter-nginx 2>/dev/null || true
            ;;
            
        "systemd")
            log_info "停止 Systemd 服务..."
            sudo systemctl stop clash-converter-backend 2>/dev/null || true
            sudo systemctl stop clash-converter-frontend 2>/dev/null || true
            sudo systemctl stop clash-converter 2>/dev/null || true
            sudo systemctl disable clash-converter-backend 2>/dev/null || true
            sudo systemctl disable clash-converter-frontend 2>/dev/null || true
            sudo systemctl disable clash-converter 2>/dev/null || true
            ;;
            
        "supervisor")
            log_info "停止 Supervisor 进程..."
            sudo supervisorctl stop clash-converter:* 2>/dev/null || true
            ;;
    esac
    
    # 通用进程清理
    log_info "终止相关进程..."
    pkill -f "clash-converter" 2>/dev/null || true
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
}

# 删除 Docker 资源
remove_docker_resources() {
    log_info "清理 Docker 资源..."
    
    # 停止并删除容器
    docker stop $(docker ps -aq --filter "name=clash-converter") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=clash-converter") 2>/dev/null || true
    
    # 删除网络
    docker network rm clash-network 2>/dev/null || true
    docker network rm $(docker network ls -q --filter "name=clash") 2>/dev/null || true
    
    # 删除卷
    docker volume rm $(docker volume ls -q --filter "name=clash-converter") 2>/dev/null || true
    
    # 删除镜像（如果选择）
    if [[ $REMOVE_DOCKER_IMAGES == true ]]; then
        log_info "删除 Docker 镜像..."
        docker rmi $(docker images --filter "reference=*clash-converter*" -q) 2>/dev/null || true
        docker rmi $(docker images --filter "reference=clash-sub-converter*" -q) 2>/dev/null || true
        
        # 清理未使用的镜像
        docker image prune -f 2>/dev/null || true
    fi
    
    log_success "Docker 资源清理完成"
}

# 删除系统服务配置
remove_system_configs() {
    if [[ $REMOVE_SYSTEM_CONFIGS != true ]]; then
        return
    fi
    
    log_info "删除系统配置文件..."
    
    # Systemd 服务文件
    if [[ -d "/etc/systemd/system" ]]; then
        sudo rm -f /etc/systemd/system/clash-converter*.service
        sudo systemctl daemon-reload 2>/dev/null || true
    fi
    
    # Supervisor 配置
    if [[ -f "/etc/supervisor/conf.d/clash-converter.conf" ]]; then
        sudo rm -f /etc/supervisor/conf.d/clash-converter.conf
        sudo supervisorctl reread 2>/dev/null || true
        sudo supervisorctl update 2>/dev/null || true
    fi
    
    # Nginx 配置
    NGINX_SITES_DIR="/etc/nginx/sites-available"
    NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
    
    if [[ -d "$NGINX_SITES_DIR" ]]; then
        sudo rm -f "$NGINX_SITES_DIR/clash-converter"
        sudo rm -f "$NGINX_SITES_DIR/clash-sub-converter"
    fi
    
    if [[ -d "$NGINX_ENABLED_DIR" ]]; then
        sudo rm -f "$NGINX_ENABLED_DIR/clash-converter"
        sudo rm -f "$NGINX_ENABLED_DIR/clash-sub-converter"
    fi
    
    # 重载 Nginx 配置
    if systemctl is-active --quiet nginx; then
        sudo nginx -t && sudo systemctl reload nginx 2>/dev/null || true
    fi
    
    log_success "系统配置清理完成"
}

# 删除项目文件
remove_project_files() {
    log_info "删除项目文件..."
    
    # 删除安装目录
    if [[ -d "$DEFAULT_INSTALL_PATH" ]]; then
        log_info "删除安装目录: $DEFAULT_INSTALL_PATH"
        sudo rm -rf "$DEFAULT_INSTALL_PATH"
    fi
    
    # 删除当前目录（如果在项目目录中）
    CURRENT_DIR=$(pwd)
    PROJECT_DIR=$(dirname "$(readlink -f "$0")")
    
    if [[ $(basename "$PROJECT_DIR") == *"clash"* ]] || [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
        if [[ $FORCE_REMOVE == true ]]; then
            log_warning "强制删除当前项目目录: $PROJECT_DIR"
            cd /tmp
            rm -rf "$PROJECT_DIR"
        else
            log_warning "检测到项目目录，请手动删除: $PROJECT_DIR"
        fi
    fi
    
    # 删除 Web 根目录中的文件
    if [[ -d "$DEFAULT_WEB_ROOT" ]]; then
        # 查找可能的项目文件
        find "$DEFAULT_WEB_ROOT" -name "*clash*" -type f -delete 2>/dev/null || true
        find "$DEFAULT_WEB_ROOT" -name "index.html" -exec grep -l "clash" {} \; -delete 2>/dev/null || true
    fi
    
    # 删除临时文件
    rm -rf /tmp/clash-converter* 2>/dev/null || true
    rm -rf /tmp/nginx-* 2>/dev/null || true
    
    log_success "项目文件清理完成"
}

# 删除日志文件
remove_log_files() {
    if [[ $REMOVE_LOGS != true ]]; then
        return
    fi
    
    log_info "删除日志文件..."
    
    # 应用日志
    sudo rm -rf /var/log/clash-converter* 2>/dev/null || true
    sudo rm -rf /var/log/nginx/*clash* 2>/dev/null || true
    
    # 系统日志中的相关条目（不删除整个日志文件）
    if command -v journalctl &> /dev/null; then
        sudo journalctl --vacuum-time=1d --unit=clash-converter* 2>/dev/null || true
    fi
    
    # Docker 日志
    docker system prune -f --volumes 2>/dev/null || true
    
    log_success "日志文件清理完成"
}

# 删除 SSL 证书
remove_ssl_certificates() {
    if [[ $REMOVE_SSL_CERTS != true ]]; then
        return
    fi
    
    log_info "删除 SSL 证书..."
    
    # 项目相关的 SSL 证书
    sudo rm -rf /etc/nginx/ssl/clash-converter* 2>/dev/null || true
    rm -rf ./deploy/ssl 2>/dev/null || true
    
    # Let's Encrypt 证书（谨慎操作）
    if command -v certbot &> /dev/null; then
        DOMAINS=$(certbot certificates 2>/dev/null | grep -E "clash|converter" | awk '{print $2}' || true)
        for domain in $DOMAINS; do
            if [[ -n "$domain" ]]; then
                log_warning "发现可能相关的 Let's Encrypt 证书: $domain"
                read -p "是否删除证书 $domain？(y/N): " confirm_cert
                if [[ $confirm_cert == "y" || $confirm_cert == "Y" ]]; then
                    sudo certbot delete --cert-name "$domain" --non-interactive 2>/dev/null || true
                fi
            fi
        done
    fi
    
    log_success "SSL 证书清理完成"
}

# 删除缓存和临时文件
remove_cache_files() {
    log_info "删除缓存和临时文件..."
    
    # Nginx 缓存
    sudo rm -rf /var/cache/nginx/clash* 2>/dev/null || true
    
    # Python 缓存
    find /tmp -name "__pycache__" -type d -path "*clash*" -exec rm -rf {} + 2>/dev/null || true
    find /tmp -name "*.pyc" -path "*clash*" -delete 2>/dev/null || true
    
    # Node.js 缓存
    rm -rf /tmp/.vite* 2>/dev/null || true
    rm -rf /tmp/vite-* 2>/dev/null || true
    
    # 用户缓存目录
    rm -rf ~/.cache/clash-converter 2>/dev/null || true
    
    log_success "缓存文件清理完成"
}

# 清理环境变量和配置
cleanup_environment() {
    log_info "清理环境变量和配置..."
    
    # 删除环境变量文件
    rm -f .env 2>/dev/null || true
    rm -f .env.local 2>/dev/null || true
    rm -f .env.production 2>/dev/null || true
    
    # 删除用户配置
    rm -rf ~/.config/clash-converter 2>/dev/null || true
    rm -rf ~/.local/share/clash-converter 2>/dev/null || true
    
    # 清理用户 shell 配置中的相关别名或路径
    for shell_config in ~/.bashrc ~/.zshrc ~/.profile; do
        if [[ -f "$shell_config" ]]; then
            sed -i.bak '/clash.converter/d' "$shell_config" 2>/dev/null || true
            sed -i.bak '/clash-converter/d' "$shell_config" 2>/dev/null || true
        fi
    done
    
    log_success "环境配置清理完成"
}

# 卸载依赖包（谨慎操作）
remove_dependencies() {
    if [[ $REMOVE_DEPENDENCIES != true ]]; then
        return
    fi
    
    log_warning "正在卸载依赖包（谨慎操作）..."
    
    read -p "确定要卸载 Docker 和相关依赖吗？这可能影响其他应用！(y/N): " confirm_deps
    
    if [[ $confirm_deps == "y" || $confirm_deps == "Y" ]]; then
        # 检查是否还有其他 Docker 应用在运行
        RUNNING_CONTAINERS=$(docker ps -q | wc -l)
        TOTAL_CONTAINERS=$(docker ps -a -q | wc -l)
        
        if [[ $TOTAL_CONTAINERS -gt 0 ]]; then
            log_warning "检测到 $TOTAL_CONTAINERS 个 Docker 容器（$RUNNING_CONTAINERS 个运行中）"
            read -p "仍然要卸载 Docker 吗？(y/N): " confirm_docker
            
            if [[ $confirm_docker == "y" || $confirm_docker == "Y" ]]; then
                # 卸载 Docker
                sudo apt remove docker docker-engine docker.io containerd runc docker-compose -y 2>/dev/null || true
                sudo yum remove docker docker-client docker-client-latest docker-common docker-latest -y 2>/dev/null || true
                
                # 删除 Docker 数据
                sudo rm -rf /var/lib/docker 2>/dev/null || true
                sudo rm -rf /var/lib/containerd 2>/dev/null || true
            fi
        fi
        
        # 询问是否卸载 Nginx
        if systemctl is-active --quiet nginx; then
            NGINX_SITES=$(ls /etc/nginx/sites-enabled/ 2>/dev/null | wc -l)
            if [[ $NGINX_SITES -gt 0 ]]; then
                log_warning "检测到 Nginx 正在为 $NGINX_SITES 个站点提供服务"
                read -p "仍然要卸载 Nginx 吗？(y/N): " confirm_nginx
                
                if [[ $confirm_nginx == "y" || $confirm_nginx == "Y" ]]; then
                    sudo systemctl stop nginx
                    sudo systemctl disable nginx
                    sudo apt remove nginx nginx-common -y 2>/dev/null || true
                    sudo yum remove nginx -y 2>/dev/null || true
                fi
            fi
        fi
    fi
    
    log_success "依赖包卸载完成"
}

# 验证卸载结果
verify_uninstall() {
    log_info "验证卸载结果..."
    
    local issues=0
    
    # 检查进程
    if pgrep -f "clash-converter" >/dev/null 2>&1; then
        log_error "发现残留进程"
        ((issues++))
    fi
    
    # 检查 Docker 容器
    if docker ps -a | grep -q "clash-converter" 2>/dev/null; then
        log_error "发现残留 Docker 容器"
        ((issues++))
    fi
    
    # 检查系统服务
    if systemctl list-unit-files | grep -q "clash-converter" 2>/dev/null; then
        log_error "发现残留系统服务"
        ((issues++))
    fi
    
    # 检查端口占用
    for port in 8000 3000 80 443; do
        if ss -tlnp | grep ":$port " | grep -q "clash\|converter" 2>/dev/null; then
            log_error "端口 $port 仍被相关进程占用"
            ((issues++))
        fi
    done
    
    if [[ $issues -eq 0 ]]; then
        log_success "卸载验证通过，未发现残留组件"
    else
        log_warning "发现 $issues 个潜在问题，可能需要手动清理"
    fi
}

# 生成卸载报告
generate_uninstall_report() {
    local report_file="uninstall_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成卸载报告: $report_file"
    
    cat > "$report_file" <<EOF
Clash 订阅转换服务卸载报告
=============================

卸载时间: $(date)
部署类型: $DEPLOYMENT_TYPE

已执行的卸载操作:
- 停止服务: ✓
- 删除 Docker 资源: $([ "$REMOVE_DOCKER_IMAGES" = true ] && echo "✓" || echo "部分")
- 删除系统配置: $([ "$REMOVE_SYSTEM_CONFIGS" = true ] && echo "✓" || echo "跳过")
- 删除日志文件: $([ "$REMOVE_LOGS" = true ] && echo "✓" || echo "跳过")
- 删除 SSL 证书: $([ "$REMOVE_SSL_CERTS" = true ] && echo "✓" || echo "跳过")
- 删除依赖包: $([ "$REMOVE_DEPENDENCIES" = true ] && echo "✓" || echo "跳过")
- 清理缓存: ✓
- 清理环境: ✓

可能需要手动清理的项目:
EOF

    # 检查可能的残留项目
    [[ -d "/opt/clash-converter" ]] && echo "- /opt/clash-converter 目录" >> "$report_file"
    [[ -f "/etc/nginx/sites-available/clash-converter" ]] && echo "- Nginx 配置文件" >> "$report_file"
    
    if command -v docker &> /dev/null && docker images | grep -q clash 2>/dev/null; then
        echo "- Docker 镜像（使用 docker images | grep clash 查看）" >> "$report_file"
    fi
    
    cat >> "$report_file" <<EOF

如需完全清理，请检查以下位置:
- ~/.bashrc 或 ~/.zshrc 中的别名
- /etc/hosts 中的域名记录
- 防火墙规则中的端口设置
- Let's Encrypt 证书（如果使用）

EOF
    
    log_success "卸载报告已生成: $report_file"
}

# 主函数
main() {
    # 检查权限
    if [[ $EUID -eq 0 ]]; then
        log_warning "建议不要以 root 用户运行此脚本"
        read -p "继续执行吗？(y/N): " continue_as_root
        [[ $continue_as_root != "y" && $continue_as_root != "Y" ]] && exit 0
    fi
    
    show_uninstall_info
    confirm_uninstall
    detect_deployment_type
    get_user_options
    
    echo
    log_info "开始执行卸载操作..."
    
    # 执行卸载步骤
    stop_services
    
    if command -v docker &> /dev/null; then
        remove_docker_resources
    fi
    
    remove_system_configs
    remove_project_files
    remove_log_files
    remove_ssl_certificates
    remove_cache_files
    cleanup_environment
    remove_dependencies
    
    # 验证和报告
    verify_uninstall
    generate_uninstall_report
    
    echo
    log_success "🎉 Clash 订阅转换服务卸载完成！"
    echo
    echo "================================================================"
    echo "                      卸载完成总结"
    echo "================================================================"
    echo "✅ 服务已停止并删除"
    echo "✅ Docker 资源已清理"
    echo "✅ 系统配置已移除"
    echo "✅ 缓存和临时文件已清理"
    echo "✅ 环境变量已清理"
    echo
    echo "如果您在使用过程中修改了以下内容，可能需要手动恢复："
    echo "• 防火墙规则"
    echo "• /etc/hosts 文件"
    echo "• SSL 证书配置"
    echo "• 其他自定义配置"
    echo
    echo "感谢您使用 Clash 订阅转换服务！"
    echo "================================================================"
}

# 处理命令行参数
case "${1:-}" in
    "--force")
        FORCE_REMOVE=true
        REMOVE_DOCKER_IMAGES=true
        REMOVE_SYSTEM_CONFIGS=true
        REMOVE_LOGS=true
        REMOVE_SSL_CERTS=true
        main
        ;;
    "--docker-only")
        log_info "仅清理 Docker 资源..."
        detect_deployment_type
        stop_services
        remove_docker_resources
        ;;
    "--help"|"-h")
        echo "Clash 订阅转换服务卸载脚本"
        echo
        echo "用法: $0 [选项]"
        echo
        echo "选项:"
        echo "  --force       强制删除所有组件（危险操作）"
        echo "  --docker-only 仅清理 Docker 相关资源"
        echo "  --help, -h    显示此帮助信息"
        echo
        echo "交互式卸载请直接运行: $0"
        ;;
    *)
        main
        ;;
esac