#!/bin/bash

# ============================================================
# 并行部署配置验证脚本
# 用途：验证所有配置文件和目录结构是否正确
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

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 验证计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 检查函数
check_file() {
    local file_path="$1"
    local file_desc="$2"
    
    ((TOTAL_CHECKS++))
    
    if [[ -f "$file_path" ]]; then
        log_success "✓ $file_desc 存在"
        ((PASSED_CHECKS++))
        return 0
    else
        log_error "✗ $file_desc 不存在: $file_path"
        ((FAILED_CHECKS++))
        return 1
    fi
}

check_directory() {
    local dir_path="$1"
    local dir_desc="$2"
    
    ((TOTAL_CHECKS++))
    
    if [[ -d "$dir_path" ]]; then
        log_success "✓ $dir_desc 存在"
        ((PASSED_CHECKS++))
        return 0
    else
        log_warn "⚠ $dir_desc 不存在，将自动创建: $dir_path"
        mkdir -p "$dir_path"
        ((PASSED_CHECKS++))
        return 0
    fi
}

check_env_vars() {
    local env_file="$1"
    
    ((TOTAL_CHECKS++))
    
    if [[ ! -f "$env_file" ]]; then
        log_error "✗ 环境变量文件不存在: $env_file"
        ((FAILED_CHECKS++))
        return 1
    fi
    
    # 检查关键环境变量
    local required_vars=(
        "BACKEND_PORT"
        "FRONTEND_PORT" 
        "NGINX_PORT"
        "NGINX_HTTPS_PORT"
        "NETWORK_SUBNET"
    )
    
    source "$env_file"
    
    for var in "${required_vars[@]}"; do
        if [[ -n "${!var}" ]]; then
            log_info "  ✓ $var=${!var}"
        else
            log_error "  ✗ $var 未设置"
            ((FAILED_CHECKS++))
            return 1
        fi
    done
    
    log_success "✓ 环境变量配置检查通过"
    ((PASSED_CHECKS++))
    return 0
}

check_port_config() {
    local env_file="$1"
    
    ((TOTAL_CHECKS++))
    
    source "$env_file"
    
    # 检查端口分配是否合理
    local new_ports=($BACKEND_PORT $FRONTEND_PORT $NGINX_PORT $NGINX_HTTPS_PORT)
    local old_ports=(25500 8080 80 443)
    
    log_info "新系统端口配置:"
    log_info "  后端: $BACKEND_PORT"
    log_info "  前端: $FRONTEND_PORT"
    log_info "  Nginx HTTP: $NGINX_PORT"
    log_info "  Nginx HTTPS: $NGINX_HTTPS_PORT"
    
    log_info "现有系统端口 (避免冲突):"
    log_info "  subconverter: 25500"
    log_info "  sub-web: 8080"
    log_info "  nginx: 80, 443"
    
    # 检查端口冲突
    for new_port in "${new_ports[@]}"; do
        for old_port in "${old_ports[@]}"; do
            if [[ "$new_port" == "$old_port" ]]; then
                log_error "✗ 端口冲突: $new_port 与现有系统冲突"
                ((FAILED_CHECKS++))
                return 1
            fi
        done
    done
    
    log_success "✓ 端口配置无冲突"
    ((PASSED_CHECKS++))
    return 0
}

check_docker_compose_syntax() {
    local compose_file="$1"
    
    ((TOTAL_CHECKS++))
    
    # 检查基本的Docker Compose结构
    if [[ -f "$compose_file" ]]; then
        # 检查必要的字段
        if grep -q "version:" "$compose_file" && \
           grep -q "services:" "$compose_file" && \
           grep -q "networks:" "$compose_file"; then
            log_success "✓ Docker Compose配置结构正确"
            
            # 检查服务定义
            if grep -q "clash-backend-v2:" "$compose_file" && \
               grep -q "clash-frontend-v2:" "$compose_file" && \
               grep -q "nginx-v2:" "$compose_file"; then
                log_info "  ✓ 所有必需服务已定义"
                ((PASSED_CHECKS++))
                return 0
            else
                log_error "✗ 缺少必需的服务定义"
                ((FAILED_CHECKS++))
                return 1
            fi
        else
            log_error "✗ Docker Compose配置结构不完整"
            ((FAILED_CHECKS++))
            return 1
        fi
    else
        log_error "✗ Docker Compose配置文件不存在"
        ((FAILED_CHECKS++))
        return 1
    fi
}

check_nginx_config_syntax() {
    local nginx_config="$1"
    
    ((TOTAL_CHECKS++))
    
    # 简单的Nginx配置语法检查
    if [[ -f "$nginx_config" ]]; then
        # 检查基本的语法结构
        if grep -q "server {" "$nginx_config" && grep -q "location" "$nginx_config"; then
            log_success "✓ Nginx配置结构正确"
            ((PASSED_CHECKS++))
            
            # 检查上游服务器配置
            if grep -q "upstream.*backend-v2" "$nginx_config" && grep -q "upstream.*frontend-v2" "$nginx_config"; then
                log_info "  ✓ 上游服务器配置正确"
            else
                log_warn "  ⚠ 上游服务器配置可能不完整"
            fi
            
            return 0
        else
            log_error "✗ Nginx配置结构异常"
            ((FAILED_CHECKS++))
            return 1
        fi
    else
        log_error "✗ Nginx配置文件不存在"
        ((FAILED_CHECKS++))
        return 1
    fi
}

check_dockerfile_syntax() {
    local dockerfile="$1"
    local desc="$2"
    
    ((TOTAL_CHECKS++))
    
    if [[ -f "$dockerfile" ]]; then
        # 检查基本的Dockerfile语法
        if grep -q "FROM" "$dockerfile"; then
            log_success "✓ $desc Dockerfile语法正确"
            ((PASSED_CHECKS++))
            return 0
        else
            log_error "✗ $desc Dockerfile缺少FROM指令"
            ((FAILED_CHECKS++))
            return 1
        fi
    else
        log_error "✗ $desc Dockerfile不存在: $dockerfile"
        ((FAILED_CHECKS++))
        return 1
    fi
}

generate_validation_report() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}                  并行部署配置验证报告${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    
    echo -e "${YELLOW}验证概况:${NC}"
    echo -e "  总检查项: $TOTAL_CHECKS"
    echo -e "  通过项:   $PASSED_CHECKS"
    echo -e "  失败项:   $FAILED_CHECKS"
    echo -e "  成功率:   $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}🎉 所有配置验证通过！可以进行部署。${NC}"
        echo ""
        echo -e "${YELLOW}下一步操作:${NC}"
        echo -e "  1. 运行部署脚本: ./deploy-parallel-v2.sh"
        echo -e "  2. 等待服务启动完成"
        echo -e "  3. 运行稳定性测试: ./test-parallel-deployment.sh"
        echo ""
        return 0
    else
        echo -e "${RED}⚠️  配置存在问题，请修复后再进行部署。${NC}"
        echo ""
        echo -e "${YELLOW}建议修复步骤:${NC}"
        echo -e "  1. 检查缺失的文件和目录"
        echo -e "  2. 验证环境变量配置"
        echo -e "  3. 修复配置文件语法错误"
        echo -e "  4. 重新运行此验证脚本"
        echo ""
        return 1
    fi
}

main() {
    echo -e "${GREEN}开始验证并行部署配置...${NC}"
    echo ""
    
    # 1. 检查核心配置文件
    echo -e "${YELLOW}[1/7] 检查核心配置文件${NC}"
    check_file "$SCRIPT_DIR/.env.parallel" "环境变量配置文件"
    check_file "$SCRIPT_DIR/docker-compose.parallel.yml" "Docker Compose配置文件"
    check_file "$SCRIPT_DIR/deploy-v2/nginx.conf" "Nginx配置文件"
    echo ""
    
    # 2. 检查Dockerfile
    echo -e "${YELLOW}[2/7] 检查Dockerfile${NC}"
    check_file "$SCRIPT_DIR/backend/Dockerfile" "后端Dockerfile"
    check_file "$SCRIPT_DIR/frontend/Dockerfile" "前端Dockerfile"
    echo ""
    
    # 3. 检查目录结构
    echo -e "${YELLOW}[3/7] 检查目录结构${NC}"
    check_directory "$SCRIPT_DIR/backend-v2/logs" "后端日志目录"
    check_directory "$SCRIPT_DIR/deploy-v2/ssl" "SSL证书目录"
    check_directory "$SCRIPT_DIR/backups-v2" "备份目录"
    echo ""
    
    # 4. 检查环境变量
    echo -e "${YELLOW}[4/7] 检查环境变量配置${NC}"
    check_env_vars "$SCRIPT_DIR/.env.parallel"
    echo ""
    
    # 5. 检查端口配置
    echo -e "${YELLOW}[5/7] 检查端口配置${NC}"
    check_port_config "$SCRIPT_DIR/.env.parallel"
    echo ""
    
    # 6. 检查配置文件语法
    echo -e "${YELLOW}[6/7] 检查配置文件语法${NC}"
    check_docker_compose_syntax "$SCRIPT_DIR/docker-compose.parallel.yml"
    check_nginx_config_syntax "$SCRIPT_DIR/deploy-v2/nginx.conf"
    check_dockerfile_syntax "$SCRIPT_DIR/backend/Dockerfile" "后端"
    check_dockerfile_syntax "$SCRIPT_DIR/frontend/Dockerfile" "前端"
    echo ""
    
    # 7. 生成报告
    echo -e "${YELLOW}[7/7] 生成验证报告${NC}"
    generate_validation_report
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi