#!/bin/bash

# ============================================================
# Clash订阅转换器 V2 并行部署脚本
# 用途：在现有系统运行的基础上，部署新的FastAPI+Vue.js系统
# 特点：端口隔离、网络分离、资源优化、不影响现有服务
# ============================================================

set -e  # 遇到错误立即退出
set -u  # 使用未定义变量时报错

# 配置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 环境变量文件
ENV_FILE="$PROJECT_ROOT/.env.parallel"

# 配置参数
COMPOSE_FILE="docker-compose.parallel.yml"
CONTAINER_PREFIX="clash-converter"
NETWORK_NAME="clash-network-v2"

# 检查依赖
check_dependencies() {
    log_step "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi
    
    log_info "所有依赖检查通过"
}

# 检查端口占用
check_port_conflicts() {
    log_step "检查端口冲突..."
    
    # 从环境变量文件读取端口
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
        PORTS_TO_CHECK=(
            "${BACKEND_PORT:-8002}"
            "${FRONTEND_PORT:-3002}" 
            "${NGINX_PORT:-8081}"
            "${NGINX_HTTPS_PORT:-8443}"
        )
    else
        PORTS_TO_CHECK=(8002 3002 8081 8443)
    fi
    
    for port in "${PORTS_TO_CHECK[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t &>/dev/null; then
            log_error "端口 $port 已被占用，请修改配置或停止占用该端口的服务"
            lsof -Pi :$port -sTCP:LISTEN
            exit 1
        fi
    done
    
    log_info "端口检查完成，无冲突"
}

# 检查现有系统状态
check_existing_system() {
    log_step "检查现有系统状态..."
    
    # 检查现有容器
    EXISTING_CONTAINERS=(subconverter sub-web)
    RUNNING_COUNT=0
    
    for container in "${EXISTING_CONTAINERS[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$container$"; then
            log_info "现有系统容器 $container 正在运行"
            ((RUNNING_COUNT++))
        else
            log_warn "现有系统容器 $container 未运行"
        fi
    done
    
    if [[ $RUNNING_COUNT -eq 0 ]]; then
        log_warn "未发现现有系统运行中的容器，这可能不是预期情况"
        read -p "是否继续部署？(y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "部署已取消"
            exit 0
        fi
    else
        log_info "检测到 $RUNNING_COUNT 个现有系统容器正在运行"
    fi
}

# 创建必要目录
create_directories() {
    log_step "创建必要目录..."
    
    # 创建日志目录
    mkdir -p "$PROJECT_ROOT/backend-v2/logs"
    mkdir -p "$PROJECT_ROOT/deploy-v2/ssl"
    mkdir -p "$PROJECT_ROOT/backups-v2"
    
    # 设置正确的权限
    chmod 755 "$PROJECT_ROOT/backend-v2"
    chmod 755 "$PROJECT_ROOT/backend-v2/logs"
    chmod 755 "$PROJECT_ROOT/deploy-v2/ssl"
    
    log_info "目录创建完成"
}

# 验证配置文件
validate_config_files() {
    log_step "验证配置文件..."
    
    # 检查必要文件
    REQUIRED_FILES=(
        "$PROJECT_ROOT/$COMPOSE_FILE"
        "$PROJECT_ROOT/deploy-v2/nginx.conf"
        "$PROJECT_ROOT/backend/Dockerfile"
        "$PROJECT_ROOT/frontend/Dockerfile"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "必需文件不存在: $file"
            exit 1
        fi
    done
    
    # 检查Docker Compose配置
    if ! docker-compose -f "$PROJECT_ROOT/$COMPOSE_FILE" config &>/dev/null; then
        log_error "Docker Compose配置文件有语法错误"
        docker-compose -f "$PROJECT_ROOT/$COMPOSE_FILE" config
        exit 1
    fi
    
    log_info "配置文件验证通过"
}

# 备份现有配置
backup_existing_config() {
    log_step "备份现有配置..."
    
    BACKUP_DIR="$PROJECT_ROOT/backups-v2/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份重要配置文件
    if [[ -f "$PROJECT_ROOT/test.docker-compose.yml" ]]; then
        cp "$PROJECT_ROOT/test.docker-compose.yml" "$BACKUP_DIR/"
    fi
    
    if [[ -f "$PROJECT_ROOT/test.sub.guancn.me" ]]; then
        cp "$PROJECT_ROOT/test.sub.guancn.me" "$BACKUP_DIR/"
    fi
    
    log_info "配置已备份至: $BACKUP_DIR"
}

# 停止现有新系统容器（如果存在）
stop_existing_v2_containers() {
    log_step "停止现有新系统容器（如果存在）..."
    
    V2_CONTAINERS=(
        "clash-converter-backend-v2"
        "clash-converter-frontend-v2" 
        "clash-converter-nginx-v2"
    )
    
    for container in "${V2_CONTAINERS[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "停止容器: $container"
            docker stop "$container" || true
            docker rm "$container" || true
        fi
    done
    
    # 清理网络（如果存在且无其他容器使用）
    if docker network ls | grep -q "$NETWORK_NAME"; then
        log_info "清理网络: $NETWORK_NAME"
        docker network rm "$NETWORK_NAME" 2>/dev/null || true
    fi
}

# 构建和启动服务
deploy_services() {
    log_step "构建和启动新系统服务..."
    
    cd "$PROJECT_ROOT"
    
    # 加载环境变量
    if [[ -f "$ENV_FILE" ]]; then
        log_info "加载环境变量文件: $ENV_FILE"
        set -a  # 导出所有变量
        source "$ENV_FILE"
        set +a
    fi
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # 启动服务
    log_info "启动服务..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_info "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_step "等待服务就绪..."
    
    # 获取端口配置
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    BACKEND_PORT=${BACKEND_PORT:-8002}
    NGINX_PORT=${NGINX_PORT:-8081}
    
    # 等待后端服务
    log_info "等待后端服务就绪..."
    for i in {1..60}; do
        if curl -f -s "http://localhost:$BACKEND_PORT/health" &>/dev/null; then
            log_info "后端服务已就绪"
            break
        fi
        if [[ $i -eq 60 ]]; then
            log_error "后端服务启动超时"
            exit 1
        fi
        sleep 2
    done
    
    # 等待前端服务
    log_info "等待前端服务就绪..."
    for i in {1..30}; do
        if curl -f -s "http://localhost:$NGINX_PORT/" &>/dev/null; then
            log_info "前端服务已就绪"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "前端服务启动超时"
            exit 1
        fi
        sleep 2
    done
}

# 执行健康检查
health_check() {
    log_step "执行健康检查..."
    
    # 获取端口配置
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    BACKEND_PORT=${BACKEND_PORT:-8002}
    NGINX_PORT=${NGINX_PORT:-8081}
    
    # 检查后端API
    log_info "检查后端API健康状态..."
    BACKEND_HEALTH=$(curl -s "http://localhost:$BACKEND_PORT/health" | jq -r '.status' 2>/dev/null || echo "error")
    if [[ "$BACKEND_HEALTH" == "ok" ]]; then
        log_info "✓ 后端API健康检查通过"
    else
        log_error "✗ 后端API健康检查失败"
        return 1
    fi
    
    # 检查前端访问
    log_info "检查前端访问..."
    if curl -f -s "http://localhost:$NGINX_PORT/" &>/dev/null; then
        log_info "✓ 前端访问检查通过"
    else
        log_error "✗ 前端访问检查失败"
        return 1
    fi
    
    # 检查容器状态
    log_info "检查容器运行状态..."
    V2_CONTAINERS=(
        "clash-converter-backend-v2"
        "clash-converter-frontend-v2"
        "clash-converter-nginx-v2"
    )
    
    for container in "${V2_CONTAINERS[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "^$container.*Up"; then
            log_info "✓ 容器 $container 运行正常"
        else
            log_error "✗ 容器 $container 状态异常"
            return 1
        fi
    done
    
    return 0
}

# 显示部署信息
show_deployment_info() {
    log_step "部署完成！"
    
    # 获取端口配置
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
    
    BACKEND_PORT=${BACKEND_PORT:-8002}
    FRONTEND_PORT=${FRONTEND_PORT:-3002}
    NGINX_PORT=${NGINX_PORT:-8081}
    NGINX_HTTPS_PORT=${NGINX_HTTPS_PORT:-8443}
    
    echo ""
    echo -e "${GREEN}🎉 新系统部署成功！${NC}"
    echo ""
    echo -e "${BLUE}访问地址:${NC}"
    echo -e "  Web界面:     http://localhost:$NGINX_PORT/"
    echo -e "  API文档:     http://localhost:$BACKEND_PORT/docs"
    echo -e "  健康检查:    http://localhost:$BACKEND_PORT/health"
    echo ""
    echo -e "${BLUE}服务端口分配:${NC}"
    echo -e "  后端API:     $BACKEND_PORT"
    echo -e "  前端开发:    $FRONTEND_PORT"
    echo -e "  Nginx HTTP:  $NGINX_PORT"
    echo -e "  Nginx HTTPS: $NGINX_HTTPS_PORT (如果启用SSL)"
    echo ""
    echo -e "${BLUE}现有系统端口 (不受影响):${NC}"
    echo -e "  sub-web:     8080"
    echo -e "  subconverter: 25500"
    echo -e "  Nginx:       80/443"
    echo ""
    echo -e "${YELLOW}管理命令:${NC}"
    echo -e "  查看状态: docker-compose -f $COMPOSE_FILE ps"
    echo -e "  查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo -e "  停止服务: docker-compose -f $COMPOSE_FILE stop"
    echo -e "  重启服务: docker-compose -f $COMPOSE_FILE restart"
    echo ""
}

# 主函数
main() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "    Clash订阅转换器 V2 - 并行部署脚本"
    echo "    版本: 1.0.0"
    echo "    支持: FastAPI + Vue.js + Docker"
    echo "============================================================"
    echo -e "${NC}"
    
    # 执行部署步骤
    check_dependencies
    check_port_conflicts
    check_existing_system
    create_directories
    validate_config_files
    backup_existing_config
    stop_existing_v2_containers
    deploy_services
    wait_for_services
    
    # 健康检查
    if health_check; then
        show_deployment_info
    else
        log_error "健康检查失败，请检查日志"
        echo ""
        echo -e "${YELLOW}调试命令:${NC}"
        echo -e "  查看容器状态: docker-compose -f $COMPOSE_FILE ps"
        echo -e "  查看详细日志: docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi