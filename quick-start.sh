#!/bin/bash

# ============================================================
# 并行部署快速开始脚本
# 一键完成配置验证、部署和测试
# ============================================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "============================================================"
echo "    Clash订阅转换器 V2 - 并行部署快速开始"
echo "    自动执行: 配置验证 -> 系统部署 -> 稳定性测试"
echo "============================================================"
echo -e "${NC}"

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 步骤1: 配置验证
echo -e "${BLUE}步骤 1/3: 配置验证${NC}"
echo "正在验证所有配置文件和依赖..."
if ./validate-parallel-config.sh; then
    echo -e "${GREEN}✅ 配置验证通过${NC}"
else
    echo -e "${RED}❌ 配置验证失败，请修复后重试${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}配置验证完成，按任意键继续部署...${NC}"
read -n 1 -s

# 步骤2: 系统部署
echo ""
echo -e "${BLUE}步骤 2/3: 系统部署${NC}"
echo "正在部署新系统并等待服务启动..."
if ./deploy-parallel-v2.sh; then
    echo -e "${GREEN}✅ 系统部署成功${NC}"
else
    echo -e "${RED}❌ 系统部署失败${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}系统部署完成，按任意键开始稳定性测试...${NC}"
read -n 1 -s

# 步骤3: 稳定性测试
echo ""
echo -e "${BLUE}步骤 3/3: 稳定性测试${NC}"
echo "正在测试双系统并行运行的稳定性..."
if ./test-parallel-deployment.sh; then
    echo -e "${GREEN}✅ 稳定性测试通过${NC}"
else
    echo -e "${RED}❌ 稳定性测试失败${NC}"
    echo -e "${YELLOW}建议检查系统状态和日志${NC}"
fi

# 显示最终结果
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}                    快速部署完成${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

# 获取端口配置
if [[ -f ".env.parallel" ]]; then
    source ".env.parallel"
fi

BACKEND_PORT=${BACKEND_PORT:-8002}
NGINX_PORT=${NGINX_PORT:-8081}

echo -e "${BLUE}服务访问地址:${NC}"
echo "  新系统前端: http://localhost:$NGINX_PORT/"
echo "  新系统API:  http://localhost:$BACKEND_PORT/docs"
echo "  健康检查:   http://localhost:$BACKEND_PORT/health"
echo ""
echo -e "${BLUE}现有系统 (无影响):${NC}"
echo "  前端界面: http://localhost:8080/"
echo "  后端API:  http://localhost:25500/"
echo ""
echo -e "${BLUE}管理命令:${NC}"
echo "  查看状态: docker-compose -f docker-compose.parallel.yml ps"
echo "  查看日志: docker-compose -f docker-compose.parallel.yml logs -f"
echo "  重启服务: docker-compose -f docker-compose.parallel.yml restart"
echo "  停止服务: docker-compose -f docker-compose.parallel.yml stop"
echo ""
echo -e "${YELLOW}📖 详细文档: PARALLEL_DEPLOYMENT_GUIDE.md${NC}"
echo ""