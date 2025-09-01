# 全新VPS部署指南 🚀

> 在全新Ubuntu VPS上从零开始部署Clash订阅转换服务

## 📋 概述

本指南用于在一台全新的Ubuntu VPS上完整部署Clash订阅转换服务，包含：
- **系统环境初始化** (Docker、Nginx、SSL等)
- **应用容器化部署** (FastAPI + Vue.js)
- **HTTPS安全配置** (Let's Encrypt证书)
- **生产级监控** (日志、备份、监控)

## 🎯 目标服务器

- **域名**: news.guancn.me
- **系统**: Ubuntu 18.04/20.04/22.04
- **最低配置**: 1GB内存，10GB磁盘空间
- **网络**: 公网IP，域名已解析

## ⚡ 快速部署

### 方法1: 一键部署 (推荐)

```bash
# 1. 登录VPS并克隆代码
cd /opt
sudo git clone https://github.com/guancn/clashsubsys.git clash-converter
cd clash-converter
sudo chown -R $USER:$USER .

# 2. 执行一键部署
./deploy-fresh-vps.sh news.guancn.me admin@guancn.me
```

### 方法2: 分步部署

```bash
# 步骤1: 系统环境初始化
./setup-fresh-vps.sh

# 注销重新登录以使docker组权限生效
exit
ssh your-user@your-server

# 步骤2: 部署应用
cd /opt/clash-converter
./deploy-production.sh news.guancn.me admin@guancn.me
```

## 📁 核心文件说明

### 部署脚本
- `setup-fresh-vps.sh` - VPS环境初始化脚本
- `deploy-production.sh` - 生产环境部署脚本
- `setup-ssl.sh` - SSL证书配置脚本

### 配置文件
- `.env.fresh-vps` - 全新VPS环境变量配置
- `nginx-production.conf` - 生产环境Nginx配置
- `docker-compose.production.yml` - Docker生产配置

### 文档
- `FRESH_VPS_DEPLOYMENT.md` - 本文档
- `PRODUCTION_MAINTENANCE.md` - 生产环境维护指南

## 🛠️ 详细部署步骤

### 步骤1: 准备工作

#### 1.1 DNS解析配置
确保域名DNS已正确解析到VPS IP：
```bash
# 检查DNS解析
dig news.guancn.me A
nslookup news.guancn.me

# 确认解析到正确的IP
curl -s https://ipinfo.io/ip  # 获取VPS公网IP
```

#### 1.2 服务器基础配置
```bash
# 更新系统 (可选)
sudo apt update && sudo apt upgrade -y

# 创建非root用户 (如果使用root登录)
sudo adduser deploy
sudo usermod -aG sudo deploy
su - deploy
```

### 步骤2: 系统环境初始化

```bash
# 克隆项目代码
cd /opt
sudo git clone https://github.com/guancn/clashsubsys.git clash-converter
cd clash-converter
sudo chown -R $USER:$USER .

# 运行系统初始化脚本
./setup-fresh-vps.sh
```

**该脚本将安装:**
- ✅ Docker & Docker Compose
- ✅ Nginx 反向代理
- ✅ Certbot SSL证书工具
- ✅ Node.js & Python3
- ✅ 防火墙配置 (UFW)
- ✅ 系统性能优化
- ✅ 时区和NTP配置

**执行后需要注销重新登录以使docker组权限生效！**

### 步骤3: 生产环境部署

```bash
# 注销重新登录
exit
ssh your-user@your-server

# 进入项目目录
cd /opt/clash-converter

# 执行生产环境部署
./deploy-production.sh news.guancn.me admin@guancn.me
```

**该脚本将完成:**
- ✅ SSL证书申请和配置
- ✅ Nginx生产配置
- ✅ Docker容器构建和启动
- ✅ 监控和日志配置
- ✅ 自动备份设置
- ✅ 健康检查验证

### 步骤4: 验证部署

```bash
# 检查容器状态
docker-compose -f docker-compose.production.yml ps

# 检查服务响应
curl -k https://news.guancn.me/health
curl -k https://news.guancn.me/

# 检查SSL证书
openssl s_client -connect news.guancn.me:443 -servername news.guancn.me < /dev/null

# 查看日志
docker-compose -f docker-compose.production.yml logs -f
```

## 🌐 访问服务

部署完成后，通过以下地址访问服务：

### 主要服务
- **🏠 首页**: https://news.guancn.me/
- **📖 API文档**: https://news.guancn.me/docs
- **💚 健康检查**: https://news.guancn.me/health

### 管理界面
- **📊 监控面板**: http://news.guancn.me:9090/ (内网访问)
- **📋 容器状态**: `docker-compose ps`
- **📝 应用日志**: `docker-compose logs -f`

## 🔧 生产环境配置

### 系统资源配置
```yaml
# 后端服务
CPU限制: 2.0核心
内存限制: 1GB
CPU预留: 0.5核心
内存预留: 512MB

# 前端服务
CPU限制: 1.0核心
内存限制: 512MB
CPU预留: 0.2核心
内存预留: 256MB
```

### 网络和安全配置
```nginx
# HTTPS重定向
HTTP (80) → HTTPS (443)

# 安全头配置
- HSTS: max-age=31536000
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- CSP: default-src 'self'

# SSL配置
- 协议: TLSv1.2, TLSv1.3
- 加密套件: ECDHE-*, AES-GCM
- OCSP装订: 已启用
```

### 监控和日志
- **日志轮转**: 自动轮转，保留30天
- **系统监控**: 每5分钟检查容器状态
- **证书续期**: 自动续期 (每天检查2次)
- **数据备份**: 每日凌晨2点自动备份

## 🚨 故障排查

### 常见问题

#### 1. SSL证书申请失败
```bash
# 检查域名解析
dig news.guancn.me A

# 检查端口80是否开放
curl -I http://news.guancn.me/.well-known/acme-challenge/test

# 手动申请证书
./setup-ssl.sh news.guancn.me admin@guancn.me --dry-run
```

#### 2. 容器启动失败
```bash
# 查看详细日志
docker-compose -f docker-compose.production.yml logs backend
docker-compose -f docker-compose.production.yml logs frontend

# 检查端口占用
lsof -i :8000 -i :3000

# 重新构建容器
docker-compose -f docker-compose.production.yml build --no-cache
```

#### 3. Nginx配置错误
```bash
# 测试Nginx配置
sudo nginx -t

# 查看Nginx错误日志
sudo tail -f /var/log/nginx/error.log

# 重新加载配置
sudo systemctl reload nginx
```

#### 4. 服务访问异常
```bash
# 检查防火墙状态
sudo ufw status

# 检查服务监听端口
netstat -tlnp | grep -E ':(80|443|8000|3000)'

# 检查Docker网络
docker network ls
docker network inspect clash-network
```

### 诊断命令
```bash
# 系统状态检查
systemctl status docker nginx

# 资源使用情况
docker stats --no-stream
free -h
df -h

# 网络连接测试
curl -v https://news.guancn.me/health
wget --spider https://news.guancn.me/
```

## 📊 管理和维护

### 日常管理命令

```bash
# 查看服务状态
docker-compose -f docker-compose.production.yml ps
systemctl status nginx docker

# 重启服务
docker-compose -f docker-compose.production.yml restart
sudo systemctl restart nginx

# 查看日志
docker-compose -f docker-compose.production.yml logs -f --tail=100
sudo tail -f /var/log/nginx/access.log

# 更新应用
git pull origin main
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### 定期维护任务

```bash
# 清理Docker资源 (每周)
docker system prune -f
docker volume prune -f

# 更新系统包 (每月)
sudo apt update && sudo apt upgrade -y

# 检查SSL证书状态
sudo certbot certificates
sudo certbot renew --dry-run

# 手动备份
./backup-system.sh
```

### 监控指标

关注以下关键指标：
- **CPU使用率** < 80%
- **内存使用率** < 90%
- **磁盘使用率** < 85%
- **API响应时间** < 2秒
- **SSL证书有效期** > 30天

## 🔄 更新和回滚

### 应用更新
```bash
# 1. 备份当前版本
./backup-system.sh

# 2. 拉取最新代码
git pull origin main

# 3. 更新容器
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# 4. 验证更新
curl https://news.guancn.me/health
```

### 紧急回滚
```bash
# 1. 停止当前服务
docker-compose -f docker-compose.production.yml down

# 2. 恢复备份
cd /opt/backups/clash-converter
tar -xzf config_YYYYMMDD_HHMMSS.tar.gz -C /opt/clash-converter/

# 3. 回滚代码版本
git reset --hard <previous-commit>

# 4. 重启服务
docker-compose -f docker-compose.production.yml up -d
```

## 📞 技术支持

### 获取帮助

```bash
# 查看脚本帮助
./setup-fresh-vps.sh --help
./deploy-production.sh --help
./setup-ssl.sh --help

# 生成系统报告
./generate-system-report.sh  # 收集系统信息用于排障
```

### 联系方式
- **GitHub Issues**: [项目Issues](https://github.com/guancn/clashsubsys/issues)
- **邮箱**: admin@guancn.me
- **文档**: 查看项目README和相关文档

---

## 🎉 部署成功标志

当您看到以下信息时，表示部署成功：

```
🎉 部署完成！服务已在 https://news.guancn.me 上运行

🌐 访问地址:
  主页面:     https://news.guancn.me/
  API文档:    https://news.guancn.me/docs
  健康检查:   https://news.guancn.me/health

✅ 注意事项:
  ✅ SSL证书将自动续期
  ✅ 日志自动轮转 (保留30天)
  ✅ 系统监控已启用 (每5分钟检查)
  ✅ 数据备份已设置 (每天凌晨2点)
```

恭喜！您已成功在全新VPS上部署了企业级的Clash订阅转换服务！