# 生产环境部署指南 - 与现有系统共存

## 概述

本指南将帮助您在已部署 `subconverter + sub-web` 系统的服务器上部署新的 Clash 订阅转换服务，实现两套系统的完美共存。

## 🎯 部署架构

### 系统共存方案
- **现有系统**: `subconverter + sub-web`
  - 访问路径: `https://sub.guancn.me/` (前端)
  - API路径: `https://sub.guancn.me/sub` (后端)
  - 端口: `8080` (前端), `25500` (后端)

- **新系统**: `Clash 转换器`
  - 访问路径: `https://sub.guancn.me/clash/` (前端)
  - API路径: `https://sub.guancn.me/clash/api/` (后端)
  - 端口: `3001` (前端), `8001` (后端)

### 路由规则
```nginx
# 现有系统路由 (保持不变)
location /sub { ... }      # subconverter API
location / { ... }         # sub-web 前端

# 新系统路由 (新增)
location /clash/api/ { ... }  # Clash 转换器 API
location /clash/ { ... }      # Clash 转换器前端
```

## 📋 部署前检查

### 1. 系统要求
- Ubuntu 18.04+ / CentOS 7+ / Debian 9+
- Docker 20.10+
- Docker Compose 2.0+
- 可用内存: 1GB+
- 可用磁盘: 2GB+

### 2. 端口检查
确保以下端口未被占用：
- `8001` - 新的后端服务
- `3001` - 新的前端服务

```bash
# 检查端口占用
sudo ss -tlnp | grep -E ":(8001|3001)"
```

### 3. 现有系统检查
确保现有系统正常运行：
```bash
# 检查现有服务
sudo ss -tlnp | grep -E ":(25500|8080)"
curl -s http://127.0.0.1:25500/version
curl -s http://127.0.0.1:8080/
```

## 🚀 快速部署

### 1. 克隆项目
```bash
# 在服务器上克隆项目
git clone https://github.com/guancn/clashsubsys.git
cd clashsubsys
```

### 2. 运行部署脚本
```bash
# 给脚本执行权限
chmod +x deploy/deploy-production.sh

# 运行部署脚本
./deploy/deploy-production.sh
```

部署脚本会自动：
1. 检查系统环境和端口
2. 备份现有 Nginx 配置
3. 更新 Nginx 配置支持双系统
4. 构建和启动新服务
5. 验证服务状态

### 3. 验证部署
部署完成后，访问以下地址验证：

- **新系统前端**: https://sub.guancn.me/clash/
- **新系统API**: https://sub.guancn.me/clash/api/health
- **原有系统**: https://sub.guancn.me/ (确保仍正常)

## 🔧 手动部署步骤

如果自动部署脚本遇到问题，可以按以下步骤手动部署：

### 1. 配置环境变量
```bash
cp .env.production .env
```

### 2. 备份现有 Nginx 配置
```bash
sudo cp /etc/nginx/sites-available/sub.guancn.me /etc/nginx/sites-available/sub.guancn.me.backup
```

### 3. 更新 Nginx 配置
```bash
sudo cp deploy/nginx-production.conf /etc/nginx/sites-available/sub.guancn.me
sudo nginx -t
sudo systemctl reload nginx
```

### 4. 启动服务
```bash
docker-compose -f docker-compose.production.yml up -d --build
```

### 5. 验证服务
```bash
# 检查容器状态
docker-compose -f docker-compose.production.yml ps

# 检查日志
docker-compose -f docker-compose.production.yml logs -f

# 测试 API
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:3001/
```

## 📊 服务管理

### Docker Compose 命令
```bash
# 查看服务状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f [service-name]

# 重启服务
docker-compose -f docker-compose.production.yml restart

# 停止服务
docker-compose -f docker-compose.production.yml down

# 更新服务
git pull
docker-compose -f docker-compose.production.yml up -d --build

# 清理未使用的镜像
docker system prune -f
```

### 系统服务状态
```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 检查端口监听
sudo ss -tlnp | grep -E ":(80|443|8001|3001|8080|25500)"

# 查看系统资源使用
htop
df -h
```

## 🔍 故障排除

### 常见问题

#### 1. 端口冲突
**现象**: 容器启动失败，提示端口被占用
**解决**:
```bash
# 查找占用端口的进程
sudo lsof -i :8001
sudo lsof -i :3001

# 杀死占用进程
sudo kill -9 <PID>

# 或修改端口配置
nano .env.production
```

#### 2. Nginx 配置错误
**现象**: 访问新系统返回 502 或 404
**解决**:
```bash
# 检查 Nginx 配置
sudo nginx -t

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 恢复备份配置
sudo cp /etc/nginx/sites-available/sub.guancn.me.backup /etc/nginx/sites-available/sub.guancn.me
sudo systemctl reload nginx
```

#### 3. 容器启动失败
**现象**: 容器状态为 Exit 或 Restarting
**解决**:
```bash
# 查看容器日志
docker logs clash-converter-backend
docker logs clash-converter-frontend

# 检查配置文件
docker-compose -f docker-compose.production.yml config

# 重建容器
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

#### 4. API 无法访问
**现象**: 前端加载正常，但 API 请求失败
**解决**:
```bash
# 检查后端服务
curl http://127.0.0.1:8001/health

# 检查网络连接
docker network ls
docker network inspect clash-network

# 检查防火墙
sudo ufw status
```

### 日志查看
```bash
# 应用日志
docker-compose -f docker-compose.production.yml logs -f backend
docker-compose -f docker-compose.production.yml logs -f frontend

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 系统日志
sudo journalctl -u nginx -f
sudo journalctl -u docker -f
```

## 🔄 维护和更新

### 定期维护
```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 清理 Docker 资源
docker system prune -f --volumes

# 3. 查看磁盘使用
df -h
du -sh /var/lib/docker

# 4. 检查日志大小
du -sh /var/log/nginx
du -sh ./backend/logs/

# 5. 清理日志 (保留最近 7 天)
find ./backend/logs/ -name "*.log" -mtime +7 -delete
```

### 版本更新
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据
cp -r backend/logs backend/logs.backup

# 3. 更新服务
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build

# 4. 验证更新
curl https://sub.guancn.me/clash/api/health
```

## 🛡️ 安全配置

### 防火墙设置
```bash
# 允许必要端口
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制内部端口访问 (可选)
sudo ufw deny 8001
sudo ufw deny 3001
sudo ufw deny 25500
sudo ufw deny 8080
```

### SSL 证书更新
```bash
# 检查证书状态
sudo certbot certificates

# 手动更新证书
sudo certbot renew

# 测试自动更新
sudo certbot renew --dry-run
```

## 📈 性能优化

### 系统级优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 监控设置
```bash
# 安装监控工具
sudo apt install htop iotop nethogs

# 设置简单的健康检查脚本
cat > /opt/health_check.sh << 'EOF'
#!/bin/bash
if ! curl -f -s https://sub.guancn.me/clash/api/health > /dev/null; then
    echo "$(date): Clash API health check failed" >> /var/log/health_check.log
    docker-compose -f /path/to/clashsubsys/docker-compose.production.yml restart
fi
EOF

chmod +x /opt/health_check.sh

# 添加定时任务
echo "*/5 * * * * /opt/health_check.sh" | crontab -
```

## 🗑️ 卸载

如果需要完全移除新系统：

```bash
# 1. 停止和删除容器
docker-compose -f docker-compose.production.yml down -v --rmi all

# 2. 恢复 Nginx 配置
sudo cp /etc/nginx/sites-available/sub.guancn.me.backup /etc/nginx/sites-available/sub.guancn.me
sudo nginx -t && sudo systemctl reload nginx

# 3. 删除项目文件
cd ..
rm -rf clashsubsys

# 4. 清理 Docker 资源
docker system prune -af --volumes
```

## 📞 技术支持

如遇问题，请：
1. 查看本文档的故障排除部分
2. 检查系统和容器日志
3. 确认现有系统是否正常运行
4. 提供详细的错误信息

---

## 🎉 部署成功

部署完成后，您将拥有：
- **两套独立的订阅转换系统**
- **统一的域名访问入口**
- **完整的 SSL 加密**
- **自动化的运维脚本**

现在您可以：
- 通过 `https://sub.guancn.me/` 访问原有系统
- 通过 `https://sub.guancn.me/clash/` 访问新系统
- 两套系统完全独立，互不影响