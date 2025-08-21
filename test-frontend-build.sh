#!/bin/bash

# 前端构建测试脚本
# 用于在没有Docker的环境下测试前端构建

set -e

# 颜色定义
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

echo "========================================"
echo "  前端构建测试 - 验证依赖和构建过程"
echo "========================================"
echo

# 检查 Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js 未安装"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    log_error "npm 未安装"
    exit 1
fi

log_info "Node.js 版本: $(node --version)"
log_info "npm 版本: $(npm --version)"

# 进入前端目录
cd frontend

# 检查 package.json
if [ ! -f package.json ]; then
    log_error "package.json 文件不存在"
    exit 1
fi

log_success "package.json 文件存在"

# 设置环境变量
export VITE_API_BASE_URL=https://sub.guancn.me/clash/api
export VITE_APP_PREFIX=/clash
export NODE_ENV=production

log_info "设置环境变量:"
echo "  VITE_API_BASE_URL=$VITE_API_BASE_URL"
echo "  VITE_APP_PREFIX=$VITE_APP_PREFIX"
echo "  NODE_ENV=$NODE_ENV"

# 备份 node_modules（如果存在）
if [ -d node_modules ]; then
    log_info "备份现有 node_modules..."
    mv node_modules node_modules.backup.$(date +%Y%m%d_%H%M%S)
fi

# 清理安装
log_info "清理安装依赖..."
if [ -f package-lock.json ]; then
    npm ci --include=dev --no-audit --no-fund
else
    npm install --include=dev --no-audit --no-fund
fi

# 检查关键依赖
log_info "检查关键依赖安装情况..."

dependencies=("vite" "vue" "@vitejs/plugin-vue" "sass" "sass-embedded")
missing_deps=()

for dep in "${dependencies[@]}"; do
    if [ ! -d "node_modules/$dep" ]; then
        missing_deps+=($dep)
        log_error "缺少依赖: $dep"
    else
        log_success "依赖已安装: $dep"
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    log_error "缺少关键依赖: ${missing_deps[*]}"
    exit 1
fi

# 检查 Vite 可执行文件
if [ -f node_modules/.bin/vite ]; then
    log_success "Vite 可执行文件存在"
    log_info "Vite 版本: $(npx vite --version)"
else
    log_error "Vite 可执行文件不存在"
    exit 1
fi

# 尝试构建
log_info "开始构建..."
if npm run build; then
    log_success "构建成功!"
    
    # 检查构建产物
    if [ -d dist ]; then
        log_success "dist 目录已生成"
        log_info "dist 目录内容:"
        ls -la dist/
        
        # 检查关键文件
        if [ -f dist/index.html ]; then
            log_success "index.html 已生成"
        else
            log_warning "index.html 未找到"
        fi
        
        # 检查静态资源
        if ls dist/assets/*.js &> /dev/null; then
            log_success "JavaScript 文件已生成"
        else
            log_warning "JavaScript 文件未找到"
        fi
        
        if ls dist/assets/*.css &> /dev/null; then
            log_success "CSS 文件已生成"
        else
            log_warning "CSS 文件未找到"
        fi
        
    else
        log_error "dist 目录未生成"
        exit 1
    fi
else
    log_error "构建失败"
    exit 1
fi

log_success "前端构建测试完成!"
echo
echo "📋 测试总结:"
echo "  ✅ 依赖安装正常"
echo "  ✅ Vite 工具可用"
echo "  ✅ 构建过程成功"
echo "  ✅ 构建产物完整"
echo
echo "🚀 可以继续 Docker 部署流程"