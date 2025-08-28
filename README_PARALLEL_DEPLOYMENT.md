# 双系统并行部署方案 🚀

> 在不影响现有subconverter系统的前提下，部署新的FastAPI + Vue.js订阅转换服务

## 📋 概述

本方案实现了现有系统与新系统的完美共存：
- **现有系统**: subconverter + sub-web (端口: 25500, 8080)  
- **新系统**: FastAPI + Vue.js (端口: 8002, 3002, 8081)
- **零冲突**: 端口隔离、网络分离、资源优化

## 🚀 快速开始

### 一键部署
```bash
# 一键完成验证 -> 部署 -> 测试
./quick-start.sh
```

### 分步骤执行
```bash
# 1. 配置验证
./validate-parallel-config.sh

# 2. 系统部署  
./deploy-parallel-v2.sh

# 3. 稳定性测试
./test-parallel-deployment.sh
```

## 📁 核心文件

### 配置文件
- `.env.parallel` - 环境变量配置
- `docker-compose.parallel.yml` - Docker Compose配置
- `deploy-v2/nginx.conf` - Nginx反向代理配置

### 部署脚本
- `quick-start.sh` - 一键部署脚本 ⭐
- `deploy-parallel-v2.sh` - 部署脚本
- `validate-parallel-config.sh` - 配置验证脚本
- `test-parallel-deployment.sh` - 稳定性测试脚本

### 文档
- `PARALLEL_DEPLOYMENT_GUIDE.md` - 详细部署指南 📖
- `README_PARALLEL_DEPLOYMENT.md` - 本文档

## 🏗️ 架构对比

| 组件 | 现有系统 | 新系统 | 隔离策略 |
|------|----------|---------|----------|
| 后端 | subconverter:25500 | FastAPI:8002 | 端口完全分离 |
| 前端 | sub-web:8080 | Vue.js:3002 | 不同端口段 |
| 代理 | nginx:80/443 | nginx-v2:8081/8443 | 独立Nginx实例 |
| 网络 | bridge | clash-network-v2 | 自定义网络隔离 |
| 数据 | 共享目录 | 独立目录 | 完全分离 |

## 🔧 端口分配

### 新系统端口
- `8002` - 后端API服务
- `3002` - 前端开发服务 
- `8081` - Nginx HTTP代理
- `8443` - Nginx HTTPS代理

### 现有系统端口 (保持不变)
- `25500` - subconverter后端
- `8080` - sub-web前端
- `80/443` - nginx代理

## 🌐 访问方式

### 新系统
```
前端界面: http://localhost:8081/
API文档:  http://localhost:8002/docs
健康检查: http://localhost:8002/health
```

### 现有系统 (不受影响)
```
前端界面: http://localhost:8080/
后端API:  http://localhost:25500/
```

## 📊 资源配置

总资源占用: CPU ≤ 1.1核心，内存 ≤ 658MB

| 服务 | CPU限制 | 内存限制 | CPU预留 | 内存预留 |
|------|---------|----------|---------|----------|
| 后端 | 0.6核 | 350MB | 0.15核 | 180MB |
| 前端 | 0.3核 | 180MB | 0.08核 | 90MB |
| Nginx | 0.2核 | 128MB | 0.05核 | 64MB |

## 🛠️ 管理命令

### 查看状态
```bash
# 查看所有容器
docker ps

# 查看新系统容器
docker-compose -f docker-compose.parallel.yml ps

# 查看资源使用
docker stats --no-stream
```

### 服务管理
```bash
# 启动/停止/重启新系统
docker-compose -f docker-compose.parallel.yml start|stop|restart

# 查看日志
docker-compose -f docker-compose.parallel.yml logs -f

# 更新服务
docker-compose -f docker-compose.parallel.yml up -d --build
```

### 健康检查
```bash
# 检查新系统健康状态
curl http://localhost:8002/health
curl http://localhost:8081/

# 检查端口占用
lsof -i :8002 -i :3002 -i :8081
```

## 🔒 安全特性

### 容器安全
- ✅ no-new-privileges: 禁止特权升级
- ✅ cap_drop: 删除所有Linux capabilities  
- ✅ read_only: 只读文件系统
- ✅ 非root用户运行

### 网络安全
- ✅ 独立网络隔离 (172.25.0.0/24)
- ✅ 最小端口暴露
- ✅ 安全头配置
- ✅ CORS控制

## 🚨 故障处理

### 常见问题
1. **端口被占用**
   ```bash
   lsof -i :8002  # 查看端口占用
   ```

2. **容器启动失败**
   ```bash
   docker-compose -f docker-compose.parallel.yml logs service_name
   ```

3. **健康检查失败**
   ```bash
   curl -v http://localhost:8002/health
   ```

### 回滚操作
```bash
# 完全停止并清理新系统
docker-compose -f docker-compose.parallel.yml down --remove-orphans
docker network rm clash-network-v2
```

## 📈 监控指标

### 关键监控项
- 端口占用状态
- 容器运行状态  
- 资源使用率
- API响应时间
- 错误日志

### 告警阈值
- CPU使用率 > 80%
- 内存使用率 > 90%
- API响应时间 > 5s
- 容器重启次数 > 3

## 🎯 验证清单

部署完成后，请确认以下项目：

- [ ] 现有系统仍正常运行 (http://localhost:8080)
- [ ] 新系统可以访问 (http://localhost:8081)  
- [ ] 无端口冲突
- [ ] 容器状态健康
- [ ] 资源使用在合理范围
- [ ] 日志无严重错误

## 📞 支持

如遇到问题，请：

1. 查看详细文档: `PARALLEL_DEPLOYMENT_GUIDE.md`
2. 运行诊断脚本: `./test-parallel-deployment.sh`
3. 检查服务日志: `docker-compose logs`
4. 查看系统资源: `docker stats`

## 🎉 成功标志

当看到以下信息时，表示部署成功：

```
🎉 新系统部署成功！

访问地址:
  Web界面:     http://localhost:8081/
  API文档:     http://localhost:8002/docs
  健康检查:    http://localhost:8002/health

现有系统端口 (不受影响):
  sub-web:     8080
  subconverter: 25500
  Nginx:       80/443
```

---

> 💡 **提示**: 此方案已通过完整的配置验证和稳定性测试，可安全用于生产环境。