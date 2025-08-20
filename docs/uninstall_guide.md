# Clash 订阅转换服务 - 卸载指南

## 概述

本指南提供了完整卸载 Clash 订阅转换服务的详细说明，包括自动卸载脚本和手动卸载方法。

## 🚨 重要提醒

**卸载前请务必备份重要数据！**

卸载操作将删除：
- 所有项目文件和配置
- Docker 容器和镜像
- 系统服务配置
- 日志文件
- SSL 证书
- 缓存和临时文件

## 🔧 自动卸载（推荐）

### 1. 交互式卸载

运行卸载脚本，根据提示选择要卸载的组件：

```bash
cd clash-sub-converter
chmod +x deploy/uninstall.sh
./deploy/uninstall.sh
```

脚本会：
1. 自动检测部署方式
2. 询问卸载选项
3. 安全地停止和删除服务
4. 生成卸载报告

### 2. 强制完全卸载

**⚠️ 危险操作：将删除所有相关组件**

```bash
./deploy/uninstall.sh --force
```

### 3. 仅清理 Docker 资源

如果只需要清理 Docker 相关资源：

```bash
./deploy/uninstall.sh --docker-only
```

## 📋 卸载选项说明

运行交互式卸载时，您可以选择以下选项：

| 选项 | 说明 | 风险等级 |
|------|------|----------|
| Docker 镜像 | 删除项目相关的 Docker 镜像 | 低 |
| 系统配置 | 删除 Systemd、Supervisor、Nginx 配置 | 中 |
| 日志文件 | 删除应用和系统日志 | 低 |
| SSL 证书 | 删除项目相关的 SSL 证书 | 中 |
| 依赖包 | 卸载 Docker、Nginx 等依赖 | **高** |
| 强制删除 | 删除当前项目目录 | 中 |

### 风险等级说明

- **低风险**：仅影响本项目，不会影响其他应用
- **中风险**：可能影响同服务器的其他应用或服务
- **高风险**：可能严重影响系统功能，需谨慎操作

## 🛠 手动卸载方法

如果自动卸载脚本无法正常工作，您可以按以下步骤手动卸载：

### 步骤 1: 停止服务

#### Docker Compose 部署
```bash
cd /path/to/clash-sub-converter
docker-compose down -v
```

#### Docker 部署
```bash
docker stop clash-converter-backend clash-converter-frontend clash-converter-nginx
docker rm clash-converter-backend clash-converter-frontend clash-converter-nginx
```

#### Systemd 服务
```bash
sudo systemctl stop clash-converter-backend clash-converter-frontend
sudo systemctl disable clash-converter-backend clash-converter-frontend
```

#### Supervisor 部署
```bash
sudo supervisorctl stop clash-converter:*
```

### 步骤 2: 删除 Docker 资源

```bash
# 删除容器
docker rm $(docker ps -aq --filter "name=clash-converter")

# 删除镜像
docker rmi $(docker images --filter "reference=*clash-converter*" -q)

# 删除网络
docker network rm clash-network

# 删除卷
docker volume rm $(docker volume ls -q --filter "name=clash-converter")

# 清理未使用资源
docker system prune -af --volumes
```

### 步骤 3: 删除系统配置

```bash
# 删除 Systemd 服务文件
sudo rm -f /etc/systemd/system/clash-converter*.service
sudo systemctl daemon-reload

# 删除 Supervisor 配置
sudo rm -f /etc/supervisor/conf.d/clash-converter.conf
sudo supervisorctl reread && sudo supervisorctl update

# 删除 Nginx 配置
sudo rm -f /etc/nginx/sites-available/clash-converter
sudo rm -f /etc/nginx/sites-enabled/clash-converter
sudo nginx -t && sudo systemctl reload nginx
```

### 步骤 4: 删除项目文件

```bash
# 删除安装目录
sudo rm -rf /opt/clash-converter

# 删除 Web 根目录文件（如果适用）
sudo rm -rf /var/www/html/clash-converter

# 删除项目目录
rm -rf /path/to/clash-sub-converter
```

### 步骤 5: 清理日志和缓存

```bash
# 删除日志文件
sudo rm -rf /var/log/clash-converter*
sudo rm -rf /var/log/nginx/*clash*

# 删除缓存
sudo rm -rf /var/cache/nginx/clash*
rm -rf /tmp/clash-converter*
rm -rf ~/.cache/clash-converter
```

### 步骤 6: 删除 SSL 证书

```bash
# 删除项目 SSL 证书
sudo rm -rf /etc/nginx/ssl/clash-converter*

# 删除 Let's Encrypt 证书（如果使用）
sudo certbot certificates | grep clash
sudo certbot delete --cert-name your-domain.com
```

### 步骤 7: 清理环境变量

```bash
# 删除环境变量文件
rm -f .env .env.local .env.production

# 清理 Shell 配置
sed -i '/clash.converter/d' ~/.bashrc
sed -i '/clash-converter/d' ~/.bashrc
```

## 🔍 验证卸载结果

运行以下命令检查是否还有残留：

```bash
# 检查进程
ps aux | grep clash-converter

# 检查 Docker 资源
docker ps -a | grep clash
docker images | grep clash

# 检查系统服务
systemctl list-unit-files | grep clash

# 检查端口占用
ss -tlnp | grep -E ":(8000|3000|80|443)"

# 检查文件系统
find /opt /etc /var -name "*clash*" 2>/dev/null
```

## 📊 常见问题排查

### 问题 1: 权限被拒绝

```bash
# 解决方案：使用 sudo 或切换到有权限的用户
sudo ./deploy/uninstall.sh
```

### 问题 2: Docker 资源删除失败

```bash
# 强制删除 Docker 资源
docker rm -f $(docker ps -aq --filter "name=clash-converter")
docker rmi -f $(docker images --filter "reference=*clash-converter*" -q)
docker system prune -af --volumes
```

### 问题 3: 系统服务删除失败

```bash
# 手动停止并删除服务
sudo systemctl stop clash-converter*
sudo systemctl disable clash-converter*
sudo rm -f /etc/systemd/system/clash-converter*.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

### 问题 4: 端口仍被占用

```bash
# 查找占用端口的进程
sudo lsof -i :8000
sudo lsof -i :3000

# 强制终止进程
sudo kill -9 <PID>
```

### 问题 5: 文件删除权限不足

```bash
# 修改文件权限后删除
sudo chown -R $(whoami):$(whoami) /path/to/files
rm -rf /path/to/files

# 或直接使用 sudo 删除
sudo rm -rf /path/to/files
```

## 🗂 备份重要数据

在卸载前，建议备份以下数据：

### 配置文件备份

```bash
# 创建备份目录
mkdir clash-converter-backup-$(date +%Y%m%d)

# 备份配置文件
cp .env clash-converter-backup-*/
cp backend/config.yaml clash-converter-backup-*/
cp deploy/nginx.conf clash-converter-backup-*/

# 备份 SSL 证书
cp -r deploy/ssl clash-converter-backup-*/

# 创建压缩包
tar -czf clash-converter-backup-$(date +%Y%m%d).tar.gz clash-converter-backup-*/
```

### 数据库备份（如果使用）

```bash
# SQLite 数据库
cp *.db clash-converter-backup-*/

# PostgreSQL
pg_dump clash_converter > clash-converter-backup-*/database.sql

# MySQL
mysqldump clash_converter > clash-converter-backup-*/database.sql
```

## 🔄 重新安装

如果需要重新安装：

1. 确保已完全卸载旧版本
2. 重新克隆项目代码
3. 按照部署手册重新部署

```bash
# 重新获取代码
git clone <repository-url> clash-sub-converter-new
cd clash-sub-converter-new

# 恢复配置文件
cp ../clash-converter-backup-*/.env .
cp ../clash-converter-backup-*/config.yaml backend/

# 重新部署
./deploy/deploy.sh
```

## ⚠️ 注意事项

1. **数据备份**: 卸载前务必备份重要数据
2. **影响评估**: 考虑卸载对其他服务的影响
3. **权限要求**: 某些操作需要管理员权限
4. **网络依赖**: 卸载可能需要网络连接
5. **时间安排**: 在维护窗口期进行卸载操作

## 📞 获取帮助

如果遇到卸载问题：

1. 查看卸载脚本生成的报告文件
2. 检查系统日志：`journalctl -xe`
3. 查看 Docker 日志：`docker logs <container>`
4. 参考项目文档或提交 Issue

---

通过本指南，您应该能够安全、完整地卸载 Clash 订阅转换服务。如有疑问，请参考故障排除部分或寻求技术支持。