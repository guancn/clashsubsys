#!/bin/bash

echo "测试前端构建和自定义文件名功能"
echo "=================================="

# 检查前端构建
echo ""
echo "1. 检查前端构建结果..."
if [ -d "frontend/dist" ]; then
    echo "✅ 前端构建目录存在"
    echo "构建文件列表:"
    ls -la frontend/dist/
else
    echo "❌ 前端构建目录不存在"
    exit 1
fi

# 检查关键文件是否包含新功能
echo ""
echo "2. 检查关键组件是否包含自定义文件名功能..."

# 检查转换器视图
if grep -q "filename" frontend/src/views/Converter.vue; then
    echo "✅ Converter.vue 包含 filename 字段"
else
    echo "❌ Converter.vue 缺少 filename 字段"
fi

# 检查store
if grep -q "filename:" frontend/src/stores/converter.ts; then
    echo "✅ converter store 包含 filename 字段"
else
    echo "❌ converter store 缺少 filename 字段"
fi

# 检查类型定义
if grep -q "filename?" frontend/src/types/api.ts; then
    echo "✅ API types 包含 filename 字段"
else
    echo "❌ API types 缺少 filename 字段"
fi

# 检查后端schema
if grep -q "filename.*Optional" backend/app/models/schemas.py; then
    echo "✅ 后端 schema 包含 filename 字段"
else
    echo "❌ 后端 schema 缺少 filename 字段"
fi

# 检查后端API
if grep -q "cached_data\.get.*filename" backend/app/api/converter.py; then
    echo "✅ 后端 API 包含 filename 处理逻辑"
else
    echo "❌ 后端 API 缺少 filename 处理逻辑"
fi

echo ""
echo "3. 验证前端移除的功能..."

# 检查是否移除了自定义规则
if ! grep -q "custom.*rules" frontend/src/views/Converter.vue; then
    echo "✅ 已移除自定义规则相关代码"
else
    echo "⚠️  可能仍有自定义规则相关代码"
fi

# 检查是否移除了重命名规则  
if ! grep -q "rename.*rules" frontend/src/views/Converter.vue; then
    echo "✅ 已移除重命名规则相关代码"
else
    echo "⚠️  可能仍有重命名规则相关代码"
fi

echo ""
echo "测试完成！"
