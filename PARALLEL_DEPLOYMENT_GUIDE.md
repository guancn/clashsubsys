# 双系统并行部署方案

## 概述

本方案实现了在现有订阅转换系统运行的基础上，部署新的FastAPI + Vue.js系统，确保两个系统可以同时运行而不相互影响。

## 系统架构对比

### 现有系统 (不受影响)
- **后端**: subconverter (端口: 25500)
- **前端**: sub-web (端口: 8080)
- **代理**: nginx (端口: 80/443)
- **网络**: docker默认bridge网络
- **域名**: sub.guancn.me

### 新系统 (并行运行)
- **后端**: FastAPI (端口: 8002)
- **前端**: Vue.js (端口: 3002)
- **代理**: nginx-v2 (端口: 8081/8443)
- **网络**: clash-network-v2 (172.25.0.0/24)
- **路由**: 通过路径前缀 /clash-v2/ 区分

## 端口分配策略

| 服务类型 | 现有系统端口 | 新系统端口 | 冲突避免策略 |
|----------|-------------|------------|--------------|
| 后端API  | 25500       | 8002       | 完全不同的端口段 |
| 前端服务 | 8080        | 3002       | 使用3000段端口 |
| HTTP代理 | 80          | 8081       | 8000段端口 |
| HTTPS代理| 443         | 8443       | 8000段端口 |

## 网络隔离策略

### 现有系统网络
```yaml
# 使用Docker默认网络
networks:
  - default  # 通常是 bridge 网络
```

### 新系统网络
```yaml
# 独立的自定义网络
networks:
  clash-network-v2:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/24  # 避免与现有网络冲突
```

## 资源限制优化

为确保双系统稳定运行，新系统采用保守的资源限制：

### 后端服务
```yaml
resources:
  limits:
    cpus: '0.6'      # 60% CPU限制
    memory: 350M     # 350MB内存限制
  reservations:
    cpus: '0.15'     # 15% CPU预留
    memory: 180M     # 180MB内存预留
```

### 前端服务
```yaml
resources:
  limits:
    cpus: '0.3'      # 30% CPU限制
    memory: 180M     # 180MB内存限制
  reservations:
    cpus: '0.08'     # 8% CPU预留
    memory: 90M      # 90MB内存预留
```

### Nginx服务
```yaml
resources:
  limits:
    cpus: '0.2'      # 20% CPU限制
    memory: 128M     # 128MB内存限制
  reservations:
    cpus: '0.05'     # 5% CPU预留
    memory: 64M      # 64MB内存预留
```

**总资源占用**: CPU ≤ 1.1核心，内存 ≤ 658MB

## 部署文件结构

```
subt/
├── .env.parallel                    # 新系统环境变量配置
├── docker-compose.parallel.yml     # 新系统Docker Compose配置
├── deploy-parallel-v2.sh           # 并行部署脚本
├── test-parallel-deployment.sh     # 稳定性测试脚本
├── validate-parallel-config.sh     # 配置验证脚本
├── deploy-v2/
│   ├── nginx.conf                   # 新系统Nginx配置
│   └── ssl/                         # SSL证书目录
├── backend-v2/
│   └── logs/                        # 新系统后端日志
└── backups-v2/                      # 配置备份目录
```

## 部署流程

### 1. 预检查阶段
```bash
# 验证配置文件
./validate-parallel-config.sh
```

**检查项目**:
- [x] 环境变量配置完整性
- [x] Docker Compose文件语法
- [x] Nginx配置文件正确性
- [x] Dockerfile存在性
- [x] 端口冲突检查
- [x] 目录结构完整性

### 2. 部署阶段
```bash
# 执行并行部署
./deploy-parallel-v2.sh
```

**部署步骤**:
1. **依赖检查**: Docker、Docker Compose可用性
2. **端口检查**: 确保新系统端口未被占用
3. **现有系统检查**: 验证现有系统运行状态
4. **目录创建**: 创建必要的日志和配置目录
5. **配置验证**: 验证所有配置文件正确性
6. **配置备份**: 备份现有系统配置
7. **容器清理**: 停止可能存在的旧版新系统容器
8. **服务部署**: 构建镜像并启动新系统服务
9. **健康检查**: 等待服务就绪并验证功能

### 3. 验证阶段
```bash
# 执行稳定性测试
./test-parallel-deployment.sh
```

**测试项目**:
- [x] 端口冲突检查
- [x] 现有系统健康检查
- [x] 新系统健康检查
- [x] 容器状态检查
- [x] 网络隔离测试
- [x] 资源使用测试
- [x] 并发访问测试
- [x] 功能隔离测试
- [x] 数据一致性测试
- [x] 系统恢复测试

## 访问方式

### 现有系统 (保持不变)
- **前端界面**: http://sub.guancn.me/
- **后端API**: http://sub.guancn.me/sub/

### 新系统 (并行运行)
- **前端界面**: http://localhost:8081/ 或 http://sub.guancn.me/clash-v2/
- **后端API**: http://localhost:8002/docs
- **健康检查**: http://localhost:8002/health

## 路径路由策略

新系统通过路径前缀区分，实现同域名下的多系统共存：

```nginx
# 现有系统路由 (不变)
location /sub {
    proxy_pass http://127.0.0.1:25500;
}
location / {
    proxy_pass http://127.0.0.1:8080;
}

# 新系统路由 (新增)
location /clash-v2/api/ {
    rewrite ^/clash-v2/api/(.*) /clash/api/$1 break;
    proxy_pass http://clash-backend-v2;
}
location /clash-v2/ {
    rewrite ^/clash-v2/(.*) /$1 break;
    proxy_pass http://clash-frontend-v2;
}
```

## 管理命令

### 查看系统状态
```bash
# 查看所有容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 查看新系统容器状态
docker-compose -f docker-compose.parallel.yml ps

# 查看资源使用情况
docker stats --no-stream
```

### 服务管理
```bash
# 启动新系统
docker-compose -f docker-compose.parallel.yml start

# 停止新系统
docker-compose -f docker-compose.parallel.yml stop

# 重启新系统
docker-compose -f docker-compose.parallel.yml restart

# 查看新系统日志
docker-compose -f docker-compose.parallel.yml logs -f
```

### 故障排查
```bash
# 检查端口占用
lsof -i :8002 -i :3002 -i :8081 -i :8443

# 检查网络连接
docker network ls
docker network inspect clash-network-v2

# 健康检查
curl -f http://localhost:8002/health
curl -f http://localhost:8081/
```

## 回滚策略

如需回滚新系统而不影响现有系统：

```bash
# 停止并删除新系统
docker-compose -f docker-compose.parallel.yml down --remove-orphans

# 清理镜像 (可选)
docker image rm clash-converter-backend-v2:latest
docker image rm clash-converter-frontend-v2:latest

# 清理网络
docker network rm clash-network-v2

# 清理卷和目录 (可选)
rm -rf backend-v2/logs/*
rm -rf backups-v2/*
```

## 监控指标

### 关键监控项
1. **端口占用状态**: 确保无冲突
2. **容器运行状态**: 所有容器健康运行
3. **资源使用率**: CPU和内存在合理范围
4. **响应时间**: API和前端响应正常
5. **错误率**: 日志中无严重错误

### 告警阈值
- CPU使用率 > 80%
- 内存使用率 > 90%
- 容器重启次数 > 3
- API响应时间 > 5秒
- 健康检查失败 > 2次

## 安全配置

### 容器安全
- `no-new-privileges: true`: 禁止容器获取新权限
- `cap_drop: ALL`: 删除所有Linux capabilities
- `read_only: true`: 文件系统只读 (除必要的写入目录)
- 非root用户运行

### 网络安全
- 独立网络隔离
- 最小端口暴露
- 内部服务间通信加密

### 访问控制
- 安全头设置 (X-Frame-Options, X-XSS-Protection等)
- CORS配置
- 请求大小限制

## 性能优化

### 缓存策略
- 静态资源缓存 (7天)
- API响应缓存
- Nginx gzip压缩

### 连接优化
- Keepalive连接复用
- 上游连接池
- 合理的超时设置

### 资源优化
- 镜像多阶段构建
- 不必要文件清理
- 合理的资源限制

## 故障恢复

### 自动恢复
- 容器健康检查和自动重启
- 服务依赖等待机制
- 优雅的错误处理

### 手动恢复
- 详细的日志记录
- 配置备份恢复
- 快速故障排查指南

## 总结

通过本并行部署方案，我们成功实现了:

✅ **零影响部署**: 现有系统完全不受影响，继续正常运行  
✅ **端口隔离**: 完全避免端口冲突，两系统独立运行  
✅ **网络隔离**: 独立的Docker网络，避免网络干扰  
✅ **资源优化**: 合理的资源分配，确保系统稳定性  
✅ **安全加固**: 多层安全配置，保障系统安全  
✅ **便于管理**: 完善的部署、测试和管理工具  
✅ **快速恢复**: 完整的备份和恢复策略  

该方案为生产环境中的系统升级和并行运行提供了一个可靠、安全且易于管理的解决方案。