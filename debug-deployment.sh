#!/bin/bash

# 部署状态调试脚本

echo "=== 部署状态调试 ==="
echo

echo "1. 检查当前Git提交:"
git log --oneline -5

echo
echo "2. 检查前端nginx.conf文件（最新5行）:"
tail -5 frontend/nginx.conf

echo
echo "3. 检查外层nginx配置（最新5行）:"
tail -5 deploy/nginx-production.conf

echo
echo "4. 检查Docker容器状态:"
docker ps | grep clash

echo
echo "5. 检查前端容器内的nginx配置:"
docker exec clash-converter-frontend cat /etc/nginx/nginx.conf | tail -10

echo
echo "6. 检查生产环境nginx配置:"
cat /etc/nginx/sites-available/sub.guancn.me | tail -10

echo
echo "7. 测试静态资源直接访问:"
curl -I https://sub.guancn.me/clash/assets/js/index-V5h6eqlB.js 2>&1 | head -5

echo
echo "8. 测试带斜杠的静态资源访问:"
curl -I https://sub.guancn.me/clash/assets/js/index-V5h6eqlB.js/ 2>&1 | head -5

echo
echo "=== 调试完成 ==="