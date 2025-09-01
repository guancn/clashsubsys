#!/bin/bash

# ============================================================
# 全新Ubuntu VPS环境初始化脚本
# 用途：在全新VPS上安装所有必需软件和配置环境
# 适用：Ubuntu 18.04/20.04/22.04
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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        log_info "建议使用具有sudo权限的普通用户"
        exit 1
    fi
    
    # 检查sudo权限
    if ! sudo -n true 2>/dev/null; then
        log_error "当前用户没有sudo权限，请联系管理员"
        exit 1
    fi
}

# 系统信息检查
check_system() {
    log_step "检查系统信息..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法确定操作系统类型"
        exit 1
    fi
    
    source /etc/os-release
    log_info "操作系统: $NAME $VERSION"
    
    # 检查是否为Ubuntu
    if [[ "$ID" != "ubuntu" ]]; then
        log_error "此脚本仅支持Ubuntu系统"
        exit 1
    fi
    
    # 检查系统资源
    local mem_gb=$(free -g | awk 'NR==2{printf "%.1f", $2}')
    local disk_gb=$(df -BG / | awk 'NR==2{print $2}' | sed 's/G//')
    
    log_info "内存: ${mem_gb}GB"
    log_info "磁盘: ${disk_gb}GB"
    
    # 最低配置检查
    if (( $(echo "$mem_gb < 1.0" | bc -l) )); then
        log_warn "内存不足1GB，可能影响性能"
    fi
    
    if [[ $disk_gb -lt 10 ]]; then
        log_warn "磁盘空间不足10GB，可能影响安装"
    fi
}

# 更新系统
update_system() {
    log_step "更新系统软件包..."
    
    sudo apt update
    sudo apt upgrade -y
    sudo apt install -y curl wget git vim nano htop unzip lsof net-tools
    
    log_success "系统更新完成"
}

# 安装Docker
install_docker() {
    log_step "安装Docker..."
    
    # 检查Docker是否已安装
    if command -v docker &> /dev/null; then
        log_info "Docker已安装: $(docker --version)"
        return 0
    fi
    
    # 卸载旧版本
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # 安装必需依赖
    sudo apt install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 设置稳定版仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker Engine
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    
    # 启动Docker服务
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # 将当前用户添加到docker组
    sudo usermod -aG docker $USER
    
    log_success "Docker安装完成: $(sudo docker --version)"
    log_warn "请注销后重新登录以使docker组权限生效"
}

# 安装Docker Compose
install_docker_compose() {
    log_step "安装Docker Compose..."
    
    # 检查Docker Compose是否已安装
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose已安装: $(docker-compose --version)"
        return 0
    fi
    
    # 获取最新版本号
    local latest_version=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
    
    # 下载Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/download/${latest_version}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建符号链接
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log_success "Docker Compose安装完成: $(docker-compose --version)"
}

# 安装Nginx
install_nginx() {
    log_step "安装Nginx..."
    
    # 检查Nginx是否已安装
    if command -v nginx &> /dev/null; then
        log_info "Nginx已安装: $(nginx -v 2>&1)"
        return 0
    fi
    
    # 安装Nginx
    sudo apt install -y nginx
    
    # 启动Nginx服务
    sudo systemctl enable nginx
    sudo systemctl start nginx
    
    # 检查Nginx状态
    if sudo systemctl is-active --quiet nginx; then
        log_success "Nginx安装并启动成功"
    else
        log_error "Nginx启动失败"
        exit 1
    fi
}

# 安装Certbot (Let's Encrypt SSL)
install_certbot() {
    log_step "安装Certbot (SSL证书)..."
    
    # 检查Certbot是否已安装
    if command -v certbot &> /dev/null; then
        log_info "Certbot已安装: $(certbot --version 2>&1 | head -1)"
        return 0
    fi
    
    # 安装snapd
    sudo apt install -y snapd
    
    # 安装certbot
    sudo snap install core; sudo snap refresh core
    sudo snap install --classic certbot
    
    # 创建符号链接
    sudo ln -sf /snap/bin/certbot /usr/bin/certbot
    
    log_success "Certbot安装完成"
}

# 安装Node.js和npm
install_nodejs() {
    log_step "安装Node.js和npm..."
    
    # 检查Node.js是否已安装
    if command -v node &> /dev/null; then
        log_info "Node.js已安装: $(node --version)"
        return 0
    fi
    
    # 安装NodeSource仓库
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    
    # 安装Node.js
    sudo apt install -y nodejs
    
    log_success "Node.js安装完成: $(node --version)"
    log_success "npm安装完成: $(npm --version)"
}

# 安装Python3和pip
install_python() {
    log_step "安装Python3和pip..."
    
    # 检查Python3是否已安装
    if command -v python3 &> /dev/null; then
        log_info "Python3已安装: $(python3 --version)"
    else
        sudo apt install -y python3 python3-pip python3-venv
        log_success "Python3安装完成: $(python3 --version)"
    fi
    
    # 安装常用Python包
    pip3 install --user pyyaml requests
}

# 配置防火墙
setup_firewall() {
    log_step "配置UFW防火墙..."
    
    # 安装ufw
    sudo apt install -y ufw
    
    # 重置防火墙规则
    sudo ufw --force reset
    
    # 默认策略
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # 允许SSH
    sudo ufw allow ssh
    sudo ufw allow 22/tcp
    
    # 允许HTTP和HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # 允许应用端口
    sudo ufw allow 8000:8999/tcp  # 应用端口范围
    
    # 启用防火墙
    echo 'y' | sudo ufw enable
    
    log_success "防火墙配置完成"
    sudo ufw status
}

# 创建应用目录
create_app_directory() {
    log_step "创建应用目录..."
    
    local app_dir="/opt/clash-converter"
    
    # 创建应用目录
    sudo mkdir -p "$app_dir"
    sudo chown $USER:$USER "$app_dir"
    
    # 创建子目录
    mkdir -p "$app_dir"/{logs,ssl,backups,config}
    
    log_success "应用目录创建完成: $app_dir"
    echo "export CLASH_APP_DIR=\"$app_dir\"" >> ~/.bashrc
}

# 优化系统性能
optimize_system() {
    log_step "优化系统性能..."
    
    # 增加文件描述符限制
    echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
    
    # 优化内核参数
    cat << 'EOF' | sudo tee -a /etc/sysctl.conf
# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 6000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 60
vm.dirty_background_ratio = 2
EOF
    
    # 应用内核参数
    sudo sysctl -p
    
    log_success "系统性能优化完成"
}

# 设置时区和NTP
setup_timezone() {
    log_step "设置时区和时间同步..."
    
    # 设置时区为亚洲/上海
    sudo timedatectl set-timezone Asia/Shanghai
    
    # 安装NTP
    sudo apt install -y ntp ntpdate
    
    # 同步时间
    sudo ntpdate -s time.nist.gov
    
    # 启用NTP服务
    sudo systemctl enable ntp
    sudo systemctl start ntp
    
    log_success "时区和时间同步设置完成"
    date
}

# 创建部署用户
setup_deploy_user() {
    log_step "设置部署环境..."
    
    # 创建.env文件模板
    cat > ~/.env.deploy << 'EOF'
# 部署配置
DOMAIN_NAME=news.guancn.me
APP_DIR=/opt/clash-converter
DEPLOY_USER=$USER
DEPLOY_GROUP=$USER

# 应用配置
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# 数据库配置 (如需要)
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=clash_converter
# DB_USER=clash_user
# DB_PASS=secure_password

# SSL配置
SSL_EMAIL=admin@guancn.me
CERTBOT_DOMAIN=news.guancn.me
EOF
    
    log_success "部署环境设置完成"
    log_info "部署配置文件: ~/.env.deploy"
}

# 显示安装总结
show_summary() {
    log_step "安装总结"
    
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}              Ubuntu VPS 环境初始化完成${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    
    echo -e "${BLUE}已安装软件:${NC}"
    echo "  ✅ Docker: $(docker --version 2>/dev/null || echo '需要重新登录')"
    echo "  ✅ Docker Compose: $(docker-compose --version)"
    echo "  ✅ Nginx: $(nginx -v 2>&1)"
    echo "  ✅ Certbot: $(certbot --version 2>&1 | head -1)"
    echo "  ✅ Node.js: $(node --version)"
    echo "  ✅ Python3: $(python3 --version)"
    
    echo ""
    echo -e "${BLUE}系统配置:${NC}"
    echo "  ✅ 防火墙已配置 (端口: 22, 80, 443, 8000-8999)"
    echo "  ✅ 时区已设置: $(timedatectl show --property=Timezone --value)"
    echo "  ✅ 应用目录: /opt/clash-converter"
    echo "  ✅ 系统性能已优化"
    
    echo ""
    echo -e "${BLUE}下一步操作:${NC}"
    echo "  1. 注销并重新登录 (使docker组权限生效)"
    echo "  2. 克隆项目代码:"
    echo "     cd /opt/clash-converter"
    echo "     git clone https://github.com/guancn/clashsubsys.git ."
    echo "  3. 运行完整部署脚本:"
    echo "     ./deploy-production.sh news.guancn.me"
    
    echo ""
    echo -e "${YELLOW}重要提醒:${NC}"
    echo "  🔔 请注销后重新登录以使docker组权限生效"
    echo "  🔔 确保DNS解析 news.guancn.me 指向此VPS IP"
    echo "  🔔 部署前请检查域名解析是否生效"
    
    echo ""
}

# 主函数
main() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "          Ubuntu VPS 环境初始化脚本"
    echo "          适用于 Ubuntu 18.04/20.04/22.04"
    echo "============================================================"
    echo -e "${NC}"
    
    # 执行初始化步骤
    check_root
    check_system
    update_system
    install_docker
    install_docker_compose
    install_nginx
    install_certbot
    install_nodejs
    install_python
    setup_firewall
    create_app_directory
    optimize_system
    setup_timezone
    setup_deploy_user
    show_summary
    
    echo -e "${GREEN}🎉 VPS环境初始化完成！请注销重新登录。${NC}"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi