#!/bin/bash

# 简单的 Docker Compose 版本检测测试脚本

echo "=== Docker Compose 版本检测测试 ==="

# 检查 Docker Compose - 支持新旧两种版本
local compose_cmd=""
if command -v docker-compose &> /dev/null; then
    compose_cmd="docker-compose"
    echo "✅ 检测到旧版 Docker Compose: $(docker-compose --version)"
elif docker compose version &> /dev/null; then
    compose_cmd="docker compose"
    echo "✅ 检测到新版 Docker Compose: $(docker compose version)"
else
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "🎯 将使用命令: $compose_cmd"

# 测试 compose 命令
echo "📋 测试配置验证..."
if $compose_cmd -f docker-compose.production.yml config &> /dev/null; then
    echo "✅ Docker Compose 配置文件验证通过"
else
    echo "⚠️  Docker Compose 配置文件验证失败，请检查配置"
fi

echo "🎉 测试完成！"