# Clash 订阅转换服务

一个基于 FastAPI + Vue.js 的高性能 Clash 代理订阅转换服务，支持多种代理协议转换和自定义规则配置。

## ✨ 功能特性

- 🚀 **多协议支持**: SS、SSR、V2Ray、Trojan、Hysteria、TUIC、WireGuard 等
- 🔧 **灵活配置**: 支持远程配置规则（ACL4SSR、Subconverter 规则）
- 🎯 **节点管理**: 节点过滤、重命名、排序、国旗 Emoji 自动添加
- 📱 **现代化界面**: Vue.js 3 + TypeScript + Element Plus 响应式设计
- 🐳 **容器化部署**: Docker + Docker Compose，支持用户自定义端口
- 🛡️ **安全可靠**: HTTPS 支持、速率限制、安全头配置
- ⚡ **高性能**: 异步处理、缓存机制、Nginx 反向代理优化
- 📚 **完整文档**: 新手友好的部署指南和故障排除

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Ubuntu 18.04+ / CentOS 7+ / Debian 9+

### 一键部署

```bash
# 克隆项目
git clone https://github.com/your-org/clash-sub-converter.git
cd clash-sub-converter

# 运行自动部署脚本
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

脚本将自动：
- 引导您配置端口和域名
- 检查系统依赖
- 构建和启动所有服务
- 生成 SSL 证书（可选）
- 验证服务状态

### 手动部署

```bash
# 1. 配置环境变量
cp .env.example .env
nano .env  # 根据需要修改端口配置

# 2. 启动服务
docker-compose up -d --build

# 3. 验证部署
curl http://localhost/api/health
```

## 🌐 访问服务

部署完成后，可通过以下地址访问：

- **Web 界面**: http://your-domain.com:端口
- **API 文档**: http://your-domain.com:端口/docs
- **健康检查**: http://your-domain.com:端口/api/health

## 📖 使用说明

### Web 界面使用

1. **添加订阅链接**: 在转换页面输入您的订阅地址
2. **配置转换选项**: 选择目标格式、过滤规则等
3. **开始转换**: 点击转换按钮，等待处理完成
4. **下载配置**: 下载生成的配置文件或复制订阅链接

### API 调用示例

```bash
# POST 方式转换
curl -X POST "http://localhost:8000/api/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "url": ["https://example.com/subscription"],
    "target": "clash",
    "emoji": true,
    "udp": true
  }'

# GET 方式转换
curl "http://localhost:8000/api/convert?url=https://example.com/sub&target=clash&emoji=true"
```

## ⚙️ 配置说明

### 环境变量配置

```bash
# 端口配置 - 可根据需要修改
BACKEND_PORT=8000      # 后端服务端口
FRONTEND_PORT=3000     # 前端服务端口
NGINX_PORT=80          # Nginx HTTP 端口
NGINX_HTTPS_PORT=443   # Nginx HTTPS 端口

# 域名配置
DOMAIN=your-domain.com

# 其他配置
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

### 后端配置 (backend/config.yaml)

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

rules:
  default_remote_config: "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/ACL4SSR_Online.ini"
  
cors:
  allow_origins: ["*"]
  allow_methods: ["GET", "POST", "PUT", "DELETE"]
```

## 🛠 管理命令

### Docker Compose 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 更新服务
docker-compose pull && docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 使用部署脚本管理

```bash
# 启动服务
./deploy/deploy.sh start

# 停止服务
./deploy/deploy.sh stop

# 重启服务
./deploy/deploy.sh restart

# 查看日志
./deploy/deploy.sh logs

# 查看状态
./deploy/deploy.sh status

# 更新服务
./deploy/deploy.sh update

# 清理资源
./deploy/deploy.sh clean
```

## 📊 性能优化

### 系统级优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
sysctl -p
```

### 应用级优化

- 启用缓存机制减少重复处理
- 使用 Nginx 反向代理和压缩
- 合理配置 worker 进程数
- 定期清理日志和缓存

## 🔒 安全配置

### HTTPS 配置

使用 Let's Encrypt 自动获取 SSL 证书：

```bash
# 部署时选择启用 HTTPS
./deploy/deploy.sh
# 选择 "y" 启用 HTTPS

# 或手动配置
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 安全加固

- 启用防火墙和速率限制
- 设置安全请求头
- 使用非默认端口
- 定期更新系统和依赖

## 🗑️ 完全卸载

如果需要完全卸载服务：

```bash
# 交互式卸载（推荐）
./deploy/uninstall.sh

# 强制完全卸载
./deploy/uninstall.sh --force

# 仅清理 Docker 资源
./deploy/uninstall.sh --docker-only
```

详细卸载说明请参考 [卸载指南](docs/uninstall_guide.md)。

## 📁 项目结构

```
clash-sub-converter/
├── backend/                  # Python FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── core/            # 核心业务逻辑
│   │   ├── models/          # 数据模型
│   │   └── utils/           # 工具函数
│   ├── tests/               # 测试代码
│   └── requirements.txt     # Python 依赖
├── frontend/                 # Vue.js 前端
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   ├── views/           # 页面组件
│   │   ├── stores/          # 状态管理
│   │   └── api/             # API 调用
│   └── package.json         # Node.js 依赖
├── deploy/                   # 部署配置
│   ├── deploy.sh            # 部署脚本
│   ├── uninstall.sh         # 卸载脚本
│   └── nginx.conf           # Nginx 配置
├── docs/                     # 文档
│   ├── deployment_guide.md  # 部署指南
│   └── uninstall_guide.md   # 卸载指南
├── docker-compose.yml       # Docker 编排配置
└── .env.example             # 环境变量模板
```

## 🧪 测试

运行后端测试：

```bash
cd backend
pip install -r test_requirements.txt
pytest
```

运行前端测试：

```bash
cd frontend
npm run test
```

## 📚 文档

- [部署指南](docs/deployment_guide.md) - 详细的部署和配置说明
- [卸载指南](docs/uninstall_guide.md) - 完整的卸载操作指南
- [API 文档](http://localhost/docs) - 在线 API 文档（部署后访问）

## 🔧 故障排除

### 常见问题

1. **端口被占用**: 修改 `.env` 文件中的端口配置
2. **权限问题**: 使用 `sudo` 运行部署脚本
3. **Docker 问题**: 检查 Docker 服务状态和权限
4. **网络问题**: 检查防火墙和网络连接

### 日志查看

```bash
# 应用日志
docker-compose logs -f backend
docker-compose logs -f frontend

# Nginx 日志
docker-compose logs -f nginx

# 系统日志
journalctl -u docker -f
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库
- [subconverter](https://github.com/tindy2013/subconverter) - 订阅转换灵感来源
- [ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) - 规则配置参考

## 📞 支持

如果您遇到问题或需要帮助：

1. 查看 [常见问题](docs/deployment_guide.md#故障排除)
2. 搜索已有的 [Issues](https://github.com/your-org/clash-sub-converter/issues)
3. 创建新的 Issue 详细描述问题
4. 联系维护者

---

**⭐ 如果这个项目对您有帮助，请给一个 Star！**