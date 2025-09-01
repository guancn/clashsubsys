#!/bin/bash

# ============================================================
# SSL证书配置脚本
# 用途：为域名自动配置Let's Encrypt SSL证书
# 支持：单域名、多域名、泛域名配置
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${YELLOW}[STEP]${NC} $1"; }

# 默认配置
DOMAIN_NAME="${1:-news.guancn.me}"
SSL_EMAIL="${2:-admin@guancn.me}"
WEBROOT_PATH="/var/www/certbot"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

# 显示帮助
show_help() {
    echo "用法: $0 [domain] [email]"
    echo ""
    echo "参数:"
    echo "  domain    域名 (默认: news.guancn.me)"
    echo "  email     SSL证书邮箱 (默认: admin@guancn.me)"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --dry-run      测试模式，不实际申请证书"
    echo "  --force        强制重新申请证书"
    echo "  --wildcard     申请泛域名证书 (需要DNS验证)"
    echo ""
    echo "示例:"
    echo "  $0 news.guancn.me admin@guancn.me"
    echo "  $0 example.com user@example.com --dry-run"
    echo "  $0 *.example.com user@example.com --wildcard"
}

# 解析参数
parse_arguments() {
    DRY_RUN=false
    FORCE_RENEW=false
    WILDCARD=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE_RENEW=true
                shift
                ;;
            --wildcard)
                WILDCARD=true
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

# 检查依赖
check_dependencies() {
    log_step "检查系统依赖..."
    
    # 检查是否为root用户或有sudo权限
    if [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif sudo -n true 2>/dev/null; then
        SUDO="sudo"
    else
        log_error "需要sudo权限运行此脚本"
        exit 1
    fi
    
    # 检查Nginx
    if ! command -v nginx &> /dev/null; then
        log_error "Nginx未安装，请先安装Nginx"
        exit 1
    fi
    
    # 检查Certbot
    if ! command -v certbot &> /dev/null; then
        log_error "Certbot未安装，请先安装Certbot"
        log_info "Ubuntu/Debian: sudo apt install certbot python3-certbot-nginx"
        log_info "CentOS/RHEL: sudo yum install certbot python3-certbot-nginx"
        exit 1
    fi
    
    # 检查域名格式
    if [[ ! "$DOMAIN_NAME" =~ ^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        log_error "域名格式不正确: $DOMAIN_NAME"
        exit 1
    fi
    
    # 检查邮箱格式
    if [[ ! "$SSL_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        log_error "邮箱格式不正确: $SSL_EMAIL"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查域名解析
check_domain_resolution() {
    log_step "检查域名解析..."
    
    # 获取域名IP
    local domain_ip
    if domain_ip=$(dig +short "$DOMAIN_NAME" A | tail -1 2>/dev/null); then
        if [[ -z "$domain_ip" ]]; then
            log_warn "域名 $DOMAIN_NAME 没有A记录"
            return 1
        fi
    else
        log_warn "无法解析域名 $DOMAIN_NAME"
        return 1
    fi
    
    # 获取服务器公网IP
    local server_ip
    if server_ip=$(curl -s --max-time 10 https://ipinfo.io/ip 2>/dev/null || curl -s --max-time 10 https://api.ipify.org 2>/dev/null); then
        if [[ -z "$server_ip" ]]; then
            log_warn "无法获取服务器公网IP"
            return 1
        fi
    else
        log_warn "无法获取服务器公网IP"
        return 1
    fi
    
    log_info "域名IP: $domain_ip"
    log_info "服务器IP: $server_ip"
    
    if [[ "$domain_ip" == "$server_ip" ]]; then
        log_success "域名解析正确"
        return 0
    else
        log_warn "域名解析不匹配，可能影响SSL证书申请"
        return 1
    fi
}

# 检查现有证书
check_existing_certificate() {
    log_step "检查现有证书..."
    
    local cert_path="/etc/letsencrypt/live/$DOMAIN_NAME"
    
    if [[ -d "$cert_path" ]]; then
        local cert_file="$cert_path/fullchain.pem"
        
        if [[ -f "$cert_file" ]]; then
            # 检查证书有效期
            local expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
            local expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo 0)
            local current_epoch=$(date +%s)
            local days_left=$(( (expiry_epoch - current_epoch) / 86400 ))
            
            if [[ $days_left -gt 30 ]]; then
                log_success "证书存在且有效 (剩余 $days_left 天)"
                
                if [[ "$FORCE_RENEW" != "true" ]]; then
                    log_info "使用 --force 参数可强制重新申请"
                    return 0
                else
                    log_info "强制重新申请证书"
                    return 1
                fi
            else
                log_warn "证书即将过期 (剩余 $days_left 天)，需要续期"
                return 1
            fi
        fi
    fi
    
    log_info "未发现有效证书，需要申请新证书"
    return 1
}

# 创建Webroot目录
create_webroot() {
    log_step "创建Webroot目录..."
    
    $SUDO mkdir -p "$WEBROOT_PATH"
    $SUDO chown -R www-data:www-data "$WEBROOT_PATH" 2>/dev/null || $SUDO chown -R nginx:nginx "$WEBROOT_PATH" 2>/dev/null || true
    $SUDO chmod 755 "$WEBROOT_PATH"
    
    log_success "Webroot目录创建完成: $WEBROOT_PATH"
}

# 创建临时Nginx配置
create_temp_nginx_config() {
    log_step "创建临时Nginx配置..."
    
    local temp_config="$NGINX_AVAILABLE/temp-ssl-$DOMAIN_NAME"
    
    # 创建临时配置
    $SUDO tee "$temp_config" > /dev/null << EOF
# 临时SSL证书申请配置
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;
    
    # Let's Encrypt验证路径
    location /.well-known/acme-challenge/ {
        root $WEBROOT_PATH;
        allow all;
        try_files \$uri =404;
    }
    
    # 其他请求返回临时页面
    location / {
        return 200 'SSL证书申请中，请稍候...';
        add_header Content-Type text/plain;
    }
    
    # 隐藏服务器信息
    server_tokens off;
    
    # 基本安全配置
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    
    # 禁用默认配置
    $SUDO rm -f "$NGINX_ENABLED/default"
    
    # 启用临时配置
    $SUDO ln -sf "$temp_config" "$NGINX_ENABLED/temp-ssl-$DOMAIN_NAME"
    
    # 测试和重载Nginx
    if $SUDO nginx -t; then
        $SUDO systemctl reload nginx
        log_success "临时Nginx配置已生效"
    else
        log_error "Nginx配置测试失败"
        exit 1
    fi
}

# 申请SSL证书
obtain_certificate() {
    log_step "申请SSL证书..."
    
    local certbot_args=(
        "certonly"
        "--webroot"
        "--webroot-path=$WEBROOT_PATH"
        "--email" "$SSL_EMAIL"
        "--agree-tos"
        "--non-interactive"
        "--expand"
    )
    
    # 添加域名
    if [[ "$WILDCARD" == "true" ]]; then
        certbot_args+=("--manual" "--preferred-challenges" "dns")
        certbot_args+=("-d" "*.$DOMAIN_NAME" "-d" "$DOMAIN_NAME")
        log_warn "泛域名证书需要手动DNS验证"
    else
        certbot_args+=("-d" "$DOMAIN_NAME" "-d" "www.$DOMAIN_NAME")
    fi
    
    # 测试模式
    if [[ "$DRY_RUN" == "true" ]]; then
        certbot_args+=("--dry-run")
        log_info "测试模式：不会实际申请证书"
    fi
    
    # 强制更新
    if [[ "$FORCE_RENEW" == "true" ]]; then
        certbot_args+=("--force-renewal")
    fi
    
    # 执行Certbot
    log_info "执行: certbot ${certbot_args[*]}"
    
    if $SUDO certbot "${certbot_args[@]}"; then
        if [[ "$DRY_RUN" != "true" ]]; then
            log_success "SSL证书申请成功"
        else
            log_success "SSL证书测试通过"
        fi
    else
        log_error "SSL证书申请失败"
        cleanup_temp_config
        exit 1
    fi
}

# 验证证书
verify_certificate() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式，跳过证书验证"
        return 0
    fi
    
    log_step "验证SSL证书..."
    
    local cert_path="/etc/letsencrypt/live/$DOMAIN_NAME"
    local cert_file="$cert_path/fullchain.pem"
    local key_file="$cert_path/privkey.pem"
    
    # 检查证书文件
    if [[ ! -f "$cert_file" ]] || [[ ! -f "$key_file" ]]; then
        log_error "证书文件不存在"
        return 1
    fi
    
    # 验证证书有效性
    if openssl x509 -in "$cert_file" -text -noout > /dev/null 2>&1; then
        log_success "证书文件格式正确"
    else
        log_error "证书文件格式错误"
        return 1
    fi
    
    # 验证私钥
    if openssl rsa -in "$key_file" -check -noout > /dev/null 2>&1; then
        log_success "私钥文件格式正确"
    else
        log_error "私钥文件格式错误"
        return 1
    fi
    
    # 检查证书和私钥匹配
    local cert_hash=$(openssl x509 -noout -modulus -in "$cert_file" | openssl md5 | cut -d' ' -f2)
    local key_hash=$(openssl rsa -noout -modulus -in "$key_file" | openssl md5 | cut -d' ' -f2)
    
    if [[ "$cert_hash" == "$key_hash" ]]; then
        log_success "证书和私钥匹配"
    else
        log_error "证书和私钥不匹配"
        return 1
    fi
    
    # 显示证书信息
    local expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
    local subject=$(openssl x509 -subject -noout -in "$cert_file" | sed 's/subject=//')
    local issuer=$(openssl x509 -issuer -noout -in "$cert_file" | sed 's/issuer=//')
    
    log_info "证书信息:"
    log_info "  主体: $subject"
    log_info "  颁发者: $issuer"
    log_info "  过期时间: $expiry_date"
    
    log_success "SSL证书验证完成"
}

# 设置证书自动更新
setup_auto_renewal() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式，跳过自动更新设置"
        return 0
    fi
    
    log_step "设置证书自动更新..."
    
    # 检查是否已有定时任务
    if $SUDO crontab -l 2>/dev/null | grep -q "certbot renew"; then
        log_info "证书自动更新已配置"
    else
        # 添加定时任务
        (
            $SUDO crontab -l 2>/dev/null || echo ""
            echo "# Let's Encrypt证书自动更新 - 每天12:00和00:00检查"
            echo "0 0,12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl reload nginx'"
        ) | $SUDO crontab -
        
        log_success "证书自动更新定时任务已添加"
    fi
    
    # 创建更新钩子脚本
    local hook_script="/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"
    $SUDO mkdir -p "$(dirname "$hook_script")"
    
    $SUDO tee "$hook_script" > /dev/null << 'EOF'
#!/bin/bash
# SSL证书更新后的钩子脚本

# 重载Nginx
if systemctl is-active --quiet nginx; then
    systemctl reload nginx
    echo "$(date): Nginx reloaded after SSL certificate renewal" >> /var/log/ssl-renewal.log
fi

# 可以在这里添加其他服务的重启命令
# systemctl reload apache2
# docker-compose restart nginx
EOF
    
    $SUDO chmod +x "$hook_script"
    
    log_success "证书更新钩子脚本已创建"
}

# 清理临时配置
cleanup_temp_config() {
    log_step "清理临时配置..."
    
    local temp_config="$NGINX_ENABLED/temp-ssl-$DOMAIN_NAME"
    
    if [[ -L "$temp_config" ]]; then
        $SUDO rm -f "$temp_config"
        log_success "临时Nginx配置已清理"
    fi
    
    local temp_available="$NGINX_AVAILABLE/temp-ssl-$DOMAIN_NAME"
    if [[ -f "$temp_available" ]]; then
        $SUDO rm -f "$temp_available"
    fi
}

# 创建SSL配置片段
create_ssl_config_snippet() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "测试模式，跳过SSL配置片段创建"
        return 0
    fi
    
    log_step "创建SSL配置片段..."
    
    local ssl_snippet="/etc/nginx/snippets/ssl-$DOMAIN_NAME.conf"
    
    $SUDO tee "$ssl_snippet" > /dev/null << EOF
# SSL配置片段 - $DOMAIN_NAME
ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
ssl_private_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;

# SSL安全配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP装订
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/$DOMAIN_NAME/chain.pem;

# 安全头
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
EOF
    
    log_success "SSL配置片段已创建: $ssl_snippet"
    log_info "在Nginx配置中使用: include $ssl_snippet;"
}

# 显示结果
show_result() {
    log_step "SSL配置完成"
    
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}              SSL证书配置成功${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${BLUE}🧪 测试模式完成${NC}"
        echo "  测试域名: $DOMAIN_NAME"
        echo "  测试邮箱: $SSL_EMAIL"
        echo ""
        echo -e "${YELLOW}下一步: 移除 --dry-run 参数实际申请证书${NC}"
    else
        echo -e "${BLUE}📁 证书文件位置:${NC}"
        echo "  证书文件: /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem"
        echo "  私钥文件: /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem"
        echo "  证书链文件: /etc/letsencrypt/live/$DOMAIN_NAME/chain.pem"
        echo ""
        
        echo -e "${BLUE}🔧 配置文件:${NC}"
        echo "  SSL配置片段: /etc/nginx/snippets/ssl-$DOMAIN_NAME.conf"
        echo "  更新钩子: /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh"
        echo ""
        
        echo -e "${BLUE}🔄 自动更新:${NC}"
        echo "  定时任务已设置 (每天0点和12点检查)"
        echo "  手动更新命令: sudo certbot renew"
        echo ""
        
        echo -e "${BLUE}✅ 在Nginx配置中使用:${NC}"
        echo "  server {"
        echo "      listen 443 ssl http2;"
        echo "      server_name $DOMAIN_NAME;"
        echo "      include /etc/nginx/snippets/ssl-$DOMAIN_NAME.conf;"
        echo "      ..."
        echo "  }"
    fi
    
    echo ""
    echo -e "${YELLOW}🔗 相关命令:${NC}"
    echo "  测试证书续期: sudo certbot renew --dry-run"
    echo "  查看证书信息: sudo certbot certificates"
    echo "  撤销证书: sudo certbot revoke --cert-path /etc/letsencrypt/live/$DOMAIN_NAME/cert.pem"
    echo ""
}

# 主函数
main() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "                  SSL证书配置脚本"
    echo "                Let's Encrypt + Certbot"
    echo "============================================================"
    echo -e "${NC}"
    
    # 解析参数
    parse_arguments "$@"
    
    # 显示配置信息
    log_info "SSL配置信息:"
    log_info "  域名: $DOMAIN_NAME"
    log_info "  邮箱: $SSL_EMAIL"
    log_info "  测试模式: $DRY_RUN"
    log_info "  强制更新: $FORCE_RENEW"
    log_info "  泛域名: $WILDCARD"
    echo ""
    
    # 执行配置步骤
    check_dependencies
    
    if ! check_domain_resolution; then
        log_warn "域名解析检查失败，继续执行可能会导致证书申请失败"
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    if check_existing_certificate && [[ "$FORCE_RENEW" != "true" ]]; then
        log_success "证书已存在且有效，无需重新申请"
        create_ssl_config_snippet
        show_result
        exit 0
    fi
    
    create_webroot
    create_temp_nginx_config
    obtain_certificate
    verify_certificate
    setup_auto_renewal
    cleanup_temp_config
    create_ssl_config_snippet
    show_result
    
    if [[ "$DRY_RUN" != "true" ]]; then
        echo -e "${GREEN}🎉 SSL证书配置完成！现在可以使用HTTPS访问 $DOMAIN_NAME${NC}"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi