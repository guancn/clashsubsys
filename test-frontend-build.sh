#!/bin/bash

echo "测试前端构建..."
cd frontend

echo "检查 Node.js 版本..."
node --version
npm --version

echo "安装依赖..."
npm install

echo "尝试构建..."
npm run build

if [ -d "dist" ]; then
    echo "✅ dist 目录创建成功"
    ls -la dist/
    echo "构建文件内容："
    find dist -type f -name "*.html" -o -name "*.js" -o -name "*.css" | head -10
else
    echo "❌ dist 目录未创建"
fi