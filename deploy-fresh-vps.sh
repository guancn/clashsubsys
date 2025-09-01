#!/bin/bash

# ============================================================
# 全新VPS一键部署脚本
# 用途：在全新Ubuntu VPS上自动完成完整部署流程
# 流程：系统初始化 -> 应用部署 -> SSL配置 -> 服务验证
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
DOMAIN_NAME="${1:-news.guancn.me}"
SSL_EMAIL="${2:-admin@guancn.me}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 显示横幅
show_banner() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "               Clash订阅转换服务"
    echo "              全新VPS一键部署脚本"
    echo "============================================================"
    echo "  🎯 目标域名: $DOMAIN_NAME"
    echo "  📧 SSL邮箱: $SSL_EMAIL"
    echo "  🖥️  部署目录: $SCRIPT_DIR"
    echo "============================================================"
    echo -e "${NC}"
}

# 显示帮助信息
show_help() {
    echo "用法: $0 [domain_name] [ssl_email]"
    echo ""
    echo "参数:"
    echo "  domain_name  部署域名 (默认: news.guancn.me)"
    echo "  ssl_email    SSL证书邮箱 (默认: admin@guancn.me)"
    echo ""
    echo "选项:"
    echo "  -h, --help   显示帮助信息"
    echo "  --skip-init  跳过系统初始化 (适用于已初始化的服务器)"
    echo "  --dry-run    测试模式，不实际执行部署"
    echo ""
    echo "示例:"
    echo "  $0 news.guancn.me admin@guancn.me"
    echo "  $0 example.com user@example.com"
    echo "  $0 --skip-init  # 跳过系统初始化"
    echo ""
    echo "部署流程:"
    echo "  1️⃣  系统环境初始化 (Docker, Nginx, 防火墙等)"
    echo "  2️⃣  SSL证书申请和配置"
    echo "  3️⃣  应用容器构建和部署"
    echo "  4️⃣  服务验证和健康检查"
    echo ""
    exit 0
}

# 解析参数
parse_arguments() {
    SKIP_INIT=false
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                ;;
            --skip-init)
                SKIP_INIT=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                if [[ -z "$DOMAIN_NAME" ]] || [[ "$DOMAIN_NAME" == "news.guancn.me" ]]; then
                    DOMAIN_NAME="$1"
                elif [[ -z "$SSL_EMAIL" ]] || [[ "$SSL_EMAIL" == "admin@guancn.me" ]]; then
                    SSL_EMAIL="$1"
                fi
                shift
                ;;
        esac
    done
}

# 预检查
pre_deployment_checks() {
    log_step "执行部署前检查..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法确定操作系统类型"
        exit 1
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        log_error "此脚本仅支持Ubuntu系统，当前系统: $NAME"
        exit 1
    fi
    
    log_info "操作系统: $NAME $VERSION"
    
    # 检查用户权限
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        log_info "建议使用具有sudo权限的普通用户"
        exit 1
    fi
    
    if ! sudo -n true 2>/dev/null; then
        log_error "当前用户需要sudo权限"
        exit 1
    fi
    
    # 检查网络连接
    if ! ping -c 1 8.8.8.8 &>/dev/null; then
        log_error "网络连接异常"
        exit 1
    fi
    
    # 检查磁盘空间
    local available_gb=$(df -BG "$SCRIPT_DIR" | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $available_gb -lt 5 ]]; then
        log_error "磁盘空间不足，至少需要5GB可用空间"
        exit 1
    fi
    
    # 检查域名解析
    log_info "检查域名解析..."
    local domain_ip=$(dig +short "$DOMAIN_NAME" | tail -1)
    local server_ip=$(curl -s --max-time 10 https://ipinfo.io/ip || echo "unknown")
    
    if [[ "$domain_ip" != "$server_ip" ]]; then
        log_warn "域名解析可能不正确"
        log_warn "  域名IP: $domain_ip"
        log_warn "  服务器IP: $server_ip"
        
        if [[ "$DRY_RUN" != "true" ]]; then
            read -p "DNS解析不匹配，是否继续部署？(y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "部署已取消，请检查DNS解析后重试"
                exit 0
            fi
        fi
    else
        log_success "域名解析正确"
    fi
    
    log_success "预检查完成"
}

# 系统初始化
system_initialization() {
    if [[ "$SKIP_INIT" == "true" ]]; then
        log_info "跳过系统初始化"
        
        # 检查必要软件是否已安装
        local missing_software=()
        
        if ! command -v docker &> /dev/null; then
            missing_software+=("Docker")
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            missing_software+=("Docker Compose")
        fi
        
        if ! command -v nginx &> /dev/null; then
            missing_software+=("Nginx")
        fi
        
        if ! command -v certbot &> /dev/null; then
            missing_software+=("Certbot")
        fi
        
        if [[ ${#missing_software[@]} -gt 0 ]]; then
            log_error "缺少必要软件: ${missing_software[*]}"
            log_info "请运行完整部署或手动安装缺少的软件"
            exit 1
        fi
        
        log_success "系统环境检查通过"
        return 0
    fi
    
    log_step "开始系统环境初始化..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式: 模拟执行系统初始化"
        sleep 2
        log_success "系统初始化模拟完成"
        return 0
    fi
    
    # 检查初始化脚本
    if [[ ! -f "$SCRIPT_DIR/setup-fresh-vps.sh" ]]; then
        log_error "系统初始化脚本不存在: setup-fresh-vps.sh"
        exit 1
    fi
    
    # 执行系统初始化
    log_info "执行系统环境初始化脚本..."
    if "$SCRIPT_DIR/setup-fresh-vps.sh"; then
        log_success "系统环境初始化完成"
        
        # 检查是否需要重新登录
        if ! groups | grep -q docker; then
            log_warn "检测到Docker组权限需要生效"
            log_warn "请注销并重新登录，然后使用 --skip-init 参数继续部署："
            log_info "命令示例: $0 $DOMAIN_NAME $SSL_EMAIL --skip-init"
            exit 2
        fi
    else
        log_error "系统环境初始化失败"
        exit 1
    fi
}

# SSL证书配置
ssl_certificate_setup() {
    log_step "配置SSL证书..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式: 模拟SSL证书配置"
        sleep 2
        log_success "SSL证书配置模拟完成"
        return 0
    fi
    
    # 检查SSL配置脚本
    if [[ ! -f "$SCRIPT_DIR/setup-ssl.sh" ]]; then
        log_error "SSL配置脚本不存在: setup-ssl.sh"
        exit 1
    fi
    
    # 执行SSL证书配置
    log_info "申请和配置SSL证书..."
    if "$SCRIPT_DIR/setup-ssl.sh" "$DOMAIN_NAME" "$SSL_EMAIL"; then
        log_success "SSL证书配置完成"
    else
        log_error "SSL证书配置失败"
        exit 1
    fi
}

# 应用部署
application_deployment() {
    log_step "部署应用服务..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式: 模拟应用部署"
        sleep 3
        log_success "应用部署模拟完成"
        return 0
    fi
    
    # 检查生产部署脚本
    if [[ ! -f "$SCRIPT_DIR/deploy-production.sh" ]]; then
        log_error "生产部署脚本不存在: deploy-production.sh"
        exit 1
    fi
    
    # 执行应用部署
    log_info "执行生产环境部署..."
    if "$SCRIPT_DIR/deploy-production.sh" "$DOMAIN_NAME" "$SSL_EMAIL"; then
        log_success "应用部署完成"
    else
        log_error "应用部署失败"
        exit 1
    fi
}

# 服务验证
service_verification() {
    log_step "执行服务验证..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式: 模拟服务验证"
        log_success "服务验证模拟完成"
        return 0
    fi
    
    # 等待服务启动
    log_info "等待服务完全启动..."
    sleep 10
    
    # 检查容器状态
    log_info "检查Docker容器状态..."
    if docker-compose -f "$SCRIPT_DIR/docker-compose.production.yml" ps | grep -q "Up"; then
        log_success "Docker容器运行正常"
    else
        log_error "Docker容器状态异常"
        docker-compose -f "$SCRIPT_DIR/docker-compose.production.yml" ps
        return 1
    fi
    
    # 检查服务响应
    local endpoints=(
        "https://$DOMAIN_NAME/health"
        "https://$DOMAIN_NAME/"
        "https://$DOMAIN_NAME/docs"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log_info "检查服务端点: $endpoint"
        if curl -f -s -k --max-time 10 "$endpoint" > /dev/null; then
            log_success "✓ $endpoint - 响应正常"
        else
            log_error "✗ $endpoint - 响应异常"
        fi
    done
    
    # SSL证书验证
    log_info "验证SSL证书..."
    if openssl s_client -connect "$DOMAIN_NAME:443" -servername "$DOMAIN_NAME" < /dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        log_success "✓ SSL证书验证通过"
    else
        log_warn "⚠ SSL证书验证可能有问题"
    fi
    
    log_success "服务验证完成"
}

# 显示部署结果
show_deployment_result() {
    log_step "部署结果"
    
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}              🎉 部署成功完成！${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${BLUE}🧪 测试模式结果:${NC}"
        echo "  所有部署步骤模拟执行成功"
        echo "  移除 --dry-run 参数进行实际部署"
        echo ""
        return 0
    fi
    
    echo -e "${BLUE}🌐 服务访问地址:${NC}"
    echo "  主页面:      https://$DOMAIN_NAME/"
    echo "  API文档:     https://$DOMAIN_NAME/docs"
    echo "  健康检查:    https://$DOMAIN_NAME/health"
    echo ""
    
    echo -e "${BLUE}📊 监控和管理:${NC}"
    echo "  Prometheus:  http://$DOMAIN_NAME:9090/ (内网)"
    echo "  容器状态:    docker-compose -f docker-compose.production.yml ps"
    echo "  应用日志:    docker-compose -f docker-compose.production.yml logs -f"
    echo "  系统监控:    tail -f /var/log/clash-converter-monitor.log"
    echo ""
    
    echo -e "${BLUE}🔧 管理命令:${NC}"
    echo "  重启服务:    docker-compose -f docker-compose.production.yml restart"
    echo "  停止服务:    docker-compose -f docker-compose.production.yml stop"
    echo "  启动服务:    docker-compose -f docker-compose.production.yml start"
    echo "  更新应用:    git pull && docker-compose build --no-cache"
    echo ""
    
    echo -e "${BLUE}📁 重要文件:${NC}"
    echo "  应用目录:    $SCRIPT_DIR"
    echo "  配置文件:    $SCRIPT_DIR/.env.production"
    echo "  Nginx配置:   /etc/nginx/sites-available/clash-converter"
    echo "  SSL证书:     /etc/letsencrypt/live/$DOMAIN_NAME/"
    echo ""
    
    echo -e "${BLUE}🔔 自动化任务:${NC}"
    echo "  ✅ SSL证书自动续期 (每天0点和12点检查)"
    echo "  ✅ 系统监控检查 (每5分钟检查容器状态)"
    echo "  ✅ 日志自动轮转 (保留30天)"
    echo "  ✅ 数据自动备份 (每天凌晨2点)"
    echo ""
    
    echo -e "${YELLOW}🔗 下一步建议:${NC}"
    echo "  1. 测试所有功能是否正常工作"
    echo "  2. 配置域名CDN加速 (可选)"
    echo "  3. 设置外部监控和告警"
    echo "  4. 定期检查系统更新和安全补丁"
    echo ""
    
    echo -e "${GREEN}🎊 恭喜！Clash订阅转换服务已成功部署在 https://$DOMAIN_NAME${NC}"
    echo ""
}

# 错误清理
cleanup_on_error() {
    log_warn "检测到部署错误，执行清理操作..."
    
    # 停止可能启动的容器
    if [[ -f "$SCRIPT_DIR/docker-compose.production.yml" ]]; then
        docker-compose -f "$SCRIPT_DIR/docker-compose.production.yml" down 2>/dev/null || true
    fi
    
    # 恢复Nginx默认配置
    if sudo test -f "/etc/nginx/sites-enabled/clash-converter"; then
        sudo rm -f /etc/nginx/sites-enabled/clash-converter
        sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
        sudo systemctl reload nginx 2>/dev/null || true
    fi
    
    log_info "清理操作完成"
    echo ""
    echo -e "${YELLOW}部署失败，请检查错误信息并重试${NC}"
    echo -e "${YELLOW}如需帮助，请查看 FRESH_VPS_DEPLOYMENT.md 文档${NC}"
    echo ""
}

# 主函数
main() {
    # 设置错误处理
    trap cleanup_on_error ERR
    
    # 解析参数
    parse_arguments "$@"
    
    # 显示横幅
    show_banner
    
    # 显示配置信息
    log_info "部署配置:"
    log_info "  域名: $DOMAIN_NAME"
    log_info "  SSL邮箱: $SSL_EMAIL"
    log_info "  跳过初始化: $SKIP_INIT"
    log_info "  测试模式: $DRY_RUN"
    echo ""
    
    # 确认部署
    if [[ "$DRY_RUN" != "true" ]]; then
        read -p "确认开始部署？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
        echo ""
    fi
    
    # 执行部署流程
    local start_time=$(date +%s)
    
    pre_deployment_checks
    system_initialization
    ssl_certificate_setup
    application_deployment
    service_verification
    show_deployment_result
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    log_success "总部署时间: ${minutes}分${seconds}秒"
    
    # 记录部署信息
    if [[ "$DRY_RUN" != "true" ]]; then
        echo "$(date): 部署完成 - 域名: $DOMAIN_NAME, 耗时: ${minutes}m${seconds}s" >> "$SCRIPT_DIR/deployment.log"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi