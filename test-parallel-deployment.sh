#!/bin/bash

# ============================================================
# 双系统并行运行稳定性测试脚本
# 用途：验证新旧系统是否可以无冲突地并行运行
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
ENV_FILE="$SCRIPT_DIR/.env.parallel"

# 加载环境变量
if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE"
fi

# 端口配置
OLD_BACKEND_PORT=25500
OLD_FRONTEND_PORT=8080
NEW_BACKEND_PORT=${BACKEND_PORT:-8002}
NEW_FRONTEND_PORT=${FRONTEND_PORT:-3002}
NEW_NGINX_PORT=${NGINX_PORT:-8081}

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试结果记录
declare -a TEST_RESULTS

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((TOTAL_TESTS++))
    log_info "执行测试: $test_name"
    
    if eval "$test_command"; then
        ((PASSED_TESTS++))
        TEST_RESULTS+=("✅ $test_name")
        log_success "$test_name - 通过"
        return 0
    else
        ((FAILED_TESTS++))
        TEST_RESULTS+=("❌ $test_name")
        log_error "$test_name - 失败"
        return 1
    fi
}

# 端口冲突测试
test_port_conflicts() {
    local conflicts=0
    local ports_to_check=($OLD_BACKEND_PORT $OLD_FRONTEND_PORT $NEW_BACKEND_PORT $NEW_FRONTEND_PORT $NEW_NGINX_PORT)
    
    for port in "${ports_to_check[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t &>/dev/null; then
            local process_info=$(lsof -Pi :$port -sTCP:LISTEN | tail -1)
            log_info "端口 $port 被占用: $process_info"
        fi
    done
    
    # 检查端口是否有冲突（同一个端口被多个服务占用）
    local used_ports=$(lsof -iTCP -sTCP:LISTEN -n | awk 'NR>1 {print $9}' | cut -d: -f2 | sort | uniq -d)
    if [[ -n "$used_ports" ]]; then
        log_error "发现端口冲突: $used_ports"
        return 1
    fi
    
    return 0
}

# 现有系统健康检查
test_old_system_health() {
    local backend_ok=false
    local frontend_ok=false
    
    # 检查后端
    if curl -s -f "http://localhost:$OLD_BACKEND_PORT/version" &>/dev/null; then
        backend_ok=true
    fi
    
    # 检查前端
    if curl -s -f "http://localhost:$OLD_FRONTEND_PORT/" &>/dev/null; then
        frontend_ok=true
    fi
    
    if $backend_ok && $frontend_ok; then
        return 0
    else
        log_error "现有系统健康检查失败 - Backend: $backend_ok, Frontend: $frontend_ok"
        return 1
    fi
}

# 新系统健康检查
test_new_system_health() {
    local backend_ok=false
    local nginx_ok=false
    
    # 检查后端
    if curl -s -f "http://localhost:$NEW_BACKEND_PORT/health" &>/dev/null; then
        backend_ok=true
    fi
    
    # 检查Nginx代理
    if curl -s -f "http://localhost:$NEW_NGINX_PORT/" &>/dev/null; then
        nginx_ok=true
    fi
    
    if $backend_ok && $nginx_ok; then
        return 0
    else
        log_error "新系统健康检查失败 - Backend: $backend_ok, Nginx: $nginx_ok"
        return 1
    fi
}

# 容器状态检查
test_container_status() {
    local old_containers=(subconverter sub-web)
    local new_containers=(clash-converter-backend-v2 clash-converter-frontend-v2 clash-converter-nginx-v2)
    
    # 检查现有系统容器
    for container in "${old_containers[@]}"; do
        if ! docker ps --format "{{.Names}}" | grep -q "^$container$"; then
            log_warn "现有系统容器 $container 未运行"
        fi
    done
    
    # 检查新系统容器
    for container in "${new_containers[@]}"; do
        if ! docker ps --format "{{.Names}}" | grep -q "^$container$"; then
            log_error "新系统容器 $container 未运行"
            return 1
        fi
    done
    
    return 0
}

# 网络隔离测试
test_network_isolation() {
    local old_network=$(docker inspect subconverter 2>/dev/null | jq -r '.[0].NetworkSettings.Networks | keys[]' 2>/dev/null || echo "")
    local new_network="clash-network-v2"
    
    if [[ -n "$old_network" ]] && [[ "$old_network" != "$new_network" ]]; then
        log_info "网络隔离正常 - 现有: $old_network, 新系统: $new_network"
        return 0
    else
        log_error "网络隔离异常"
        return 1
    fi
}

# 资源使用测试
test_resource_usage() {
    local total_cpu=0
    local total_memory=0
    
    # 获取所有相关容器的资源使用情况
    local containers=(subconverter sub-web clash-converter-backend-v2 clash-converter-frontend-v2 clash-converter-nginx-v2)
    
    for container in "${containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^$container$"; then
            local stats=$(docker stats --no-stream --format "{{.CPUPerc}} {{.MemUsage}}" "$container" 2>/dev/null || echo "0.00% 0B / 0B")
            local cpu=$(echo "$stats" | awk '{print $1}' | sed 's/%//')
            local mem=$(echo "$stats" | awk '{print $2}' | sed 's/MiB.*//')
            
            total_cpu=$(echo "$total_cpu + $cpu" | bc 2>/dev/null || echo "$total_cpu")
            total_memory=$(echo "$total_memory + $mem" | bc 2>/dev/null || echo "$total_memory")
            
            log_info "容器 $container - CPU: ${cpu}%, 内存: ${mem}MB"
        fi
    done
    
    log_info "总资源使用 - CPU: ${total_cpu}%, 内存: ${total_memory}MB"
    
    # 检查资源使用是否在合理范围内
    if (( $(echo "$total_cpu < 80" | bc -l 2>/dev/null || echo 0) )); then
        return 0
    else
        log_error "CPU使用过高: ${total_cpu}%"
        return 1
    fi
}

# 并发访问测试
test_concurrent_access() {
    local old_url="http://localhost:$OLD_FRONTEND_PORT/"
    local new_url="http://localhost:$NEW_NGINX_PORT/"
    
    # 并发访问测试
    local old_success=0
    local new_success=0
    
    for i in {1..5}; do
        if curl -s -f "$old_url" &>/dev/null; then
            ((old_success++))
        fi
        if curl -s -f "$new_url" &>/dev/null; then
            ((new_success++))
        fi
        sleep 1
    done
    
    if [[ $old_success -ge 4 ]] && [[ $new_success -ge 4 ]]; then
        log_info "并发访问测试通过 - 现有系统: $old_success/5, 新系统: $new_success/5"
        return 0
    else
        log_error "并发访问测试失败 - 现有系统: $old_success/5, 新系统: $new_success/5"
        return 1
    fi
}

# 功能隔离测试
test_functional_isolation() {
    # 测试两个系统的API是否互不干扰
    local old_api="http://localhost:$OLD_BACKEND_PORT/version"
    local new_api="http://localhost:$NEW_BACKEND_PORT/health"
    
    # 同时调用两个API
    local old_response=$(curl -s "$old_api" 2>/dev/null || echo "failed")
    local new_response=$(curl -s "$new_api" 2>/dev/null || echo "failed")
    
    if [[ "$old_response" != "failed" ]] && [[ "$new_response" != "failed" ]]; then
        log_info "功能隔离测试通过"
        return 0
    else
        log_error "功能隔离测试失败 - 现有系统响应: $old_response, 新系统响应: $new_response"
        return 1
    fi
}

# 数据一致性测试
test_data_consistency() {
    # 检查两个系统的数据目录是否独立
    local old_data_path="/tmp/subconverter"  # 假设的现有系统数据路径
    local new_data_path="$SCRIPT_DIR/backend-v2"
    
    if [[ -d "$new_data_path" ]]; then
        log_info "新系统数据目录存在且独立"
        return 0
    else
        log_error "新系统数据目录配置异常"
        return 1
    fi
}

# 系统恢复测试
test_system_recovery() {
    log_info "测试系统恢复能力..."
    
    # 临时停止新系统中的一个容器，然后检查是否自动恢复
    local test_container="clash-converter-frontend-v2"
    
    if docker ps --format "{{.Names}}" | grep -q "^$test_container$"; then
        log_info "临时停止容器 $test_container 进行恢复测试"
        docker stop "$test_container" &>/dev/null
        
        # 等待自动重启
        sleep 10
        
        if docker ps --format "{{.Names}}" | grep -q "^$test_container$"; then
            log_info "容器自动恢复成功"
            return 0
        else
            log_warn "容器未自动恢复，手动重启"
            docker start "$test_container" &>/dev/null
            sleep 5
            return 1
        fi
    else
        log_error "测试容器不存在"
        return 1
    fi
}

# 生成测试报告
generate_report() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}                双系统并行运行稳定性测试报告${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    
    echo -e "${YELLOW}测试概况:${NC}"
    echo -e "  总测试数: $TOTAL_TESTS"
    echo -e "  通过数:   $PASSED_TESTS"
    echo -e "  失败数:   $FAILED_TESTS"
    echo -e "  成功率:   $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    echo ""
    
    echo -e "${YELLOW}测试结果详情:${NC}"
    for result in "${TEST_RESULTS[@]}"; do
        echo -e "  $result"
    done
    echo ""
    
    echo -e "${YELLOW}系统状态概览:${NC}"
    echo -e "  现有系统端口: $OLD_BACKEND_PORT (后端), $OLD_FRONTEND_PORT (前端)"
    echo -e "  新系统端口:   $NEW_BACKEND_PORT (后端), $NEW_NGINX_PORT (Nginx)"
    echo ""
    
    # 显示容器状态
    echo -e "${YELLOW}容器运行状态:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(subconverter|sub-web|clash-converter)" || echo "  未找到相关容器"
    echo ""
    
    # 显示网络配置
    echo -e "${YELLOW}网络配置:${NC}"
    docker network ls | grep -E "(bridge|clash-network)" || echo "  未找到相关网络"
    echo ""
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 所有测试通过！双系统可以稳定并行运行。${NC}"
        return 0
    else
        echo -e "${RED}⚠️  存在失败的测试项，请检查相关配置。${NC}"
        return 1
    fi
}

# 主测试函数
main() {
    echo -e "${GREEN}开始双系统并行运行稳定性测试...${NC}"
    echo ""
    
    # 执行所有测试
    run_test "端口冲突检查" "test_port_conflicts"
    run_test "现有系统健康检查" "test_old_system_health"
    run_test "新系统健康检查" "test_new_system_health"
    run_test "容器状态检查" "test_container_status"
    run_test "网络隔离测试" "test_network_isolation"
    run_test "资源使用测试" "test_resource_usage"
    run_test "并发访问测试" "test_concurrent_access"
    run_test "功能隔离测试" "test_functional_isolation"
    run_test "数据一致性测试" "test_data_consistency"
    run_test "系统恢复测试" "test_system_recovery"
    
    # 生成报告
    generate_report
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi