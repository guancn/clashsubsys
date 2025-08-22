#!/bin/bash

echo "=== 容器内配置详细检查 ==="
echo

echo "1. 检查容器内nginx完整配置:"
docker exec clash-converter-frontend cat /etc/nginx/nginx.conf

echo
echo "2. 检查容器内文件结构:"
docker exec clash-converter-frontend find /usr/share/nginx/html -type f | head -10

echo
echo "3. 检查容器内clash目录:"
docker exec clash-converter-frontend ls -la /usr/share/nginx/html/

echo
echo "4. 测试容器内部直接访问:"
docker exec clash-converter-frontend curl -I http://localhost/clash/assets/js/index-V5h6eqlB.js 2>&1 | head -5

echo
echo "5. 测试容器内部带斜杠访问:"
docker exec clash-converter-frontend curl -I http://localhost/clash/assets/js/index-V5h6eqlB.js/ 2>&1 | head -5

echo
echo "=== 检查完成 ==="