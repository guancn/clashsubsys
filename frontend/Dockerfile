# 安全加固的前端 Dockerfile
# 多阶段构建 + 最小权限原则 + 安全防护

# 第一阶段：依赖安装阶段
FROM node:18-alpine as dependencies

# 安全标签
LABEL stage=dependencies

# 设置环境变量
ENV NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

# 创建非特权用户
RUN addgroup -g 10001 -S nodeuser && \
    adduser -u 10001 -S nodeuser -G nodeuser

# 安装构建依赖
RUN apk add --no-cache dumb-init

# 设置工作目录
WORKDIR /app
RUN chown nodeuser:nodeuser /app

# 切换到非特权用户
USER nodeuser

# 复制 package 文件
COPY --chown=nodeuser:nodeuser package*.json ./

# 清理npm缓存并安装依赖
RUN npm ci --only=production --no-audit --no-fund --unsafe-perm=false

# 第二阶段：构建阶段
FROM node:18-alpine as builder

# 安全标签
LABEL stage=builder

# 接收构建参数
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_APP_PREFIX=/

# 设置环境变量
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_APP_PREFIX=$VITE_APP_PREFIX \
    NODE_ENV=production \
    NPM_CONFIG_CACHE=/tmp/.npm

# 创建非特权用户
RUN addgroup -g 10001 -S nodeuser && \
    adduser -u 10001 -S nodeuser -G nodeuser

# 设置工作目录
WORKDIR /app
RUN chown nodeuser:nodeuser /app

# 从依赖阶段复制node_modules
COPY --from=dependencies --chown=nodeuser:nodeuser /app/node_modules ./node_modules
COPY --from=dependencies --chown=nodeuser:nodeuser /app/package*.json ./

# 切换到非特权用户
USER nodeuser

# 安装构建依赖
RUN npm install --only=dev --no-audit --no-fund

# 复制源代码
COPY --chown=nodeuser:nodeuser . .

# 构建应用
RUN npm run build

# 第三阶段：生产运行阶段
FROM nginx:1.24-alpine as runtime

# 安全标签
LABEL maintainer="Clash Converter Security Team" \
      version="1.0.0" \
      description="Clash订阅转换服务前端-安全加固版" \
      security.scan="true"

# 设置环境变量
ENV NGINX_USER_ID=10001 \
    NGINX_GROUP_ID=10001

# 安装运行时依赖
RUN apk add --no-cache \
    curl \
    dumb-init \
    && rm -rf /var/cache/apk/*

# 创建非特权用户
RUN addgroup -g $NGINX_GROUP_ID -S nginxuser && \
    adduser -u $NGINX_USER_ID -S nginxuser -G nginxuser -s /bin/false

# 创建必要的目录并设置权限
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run/nginx \
    && chown -R nginxuser:nginxuser /var/cache/nginx /var/log/nginx /var/run/nginx \
    && chmod 755 /var/cache/nginx /var/log/nginx /var/run/nginx

# 复制构建产物
COPY --from=builder --chown=nginxuser:nginxuser /app/dist /usr/share/nginx/html

# 复制安全加固的 nginx 配置
COPY --chown=nginxuser:nginxuser nginx.conf /etc/nginx/nginx.conf

# 设置文件权限
RUN find /usr/share/nginx/html -type f -exec chmod 644 {} \; \
    && find /usr/share/nginx/html -type d -exec chmod 755 {} \; \
    && chmod 644 /etc/nginx/nginx.conf

# 移除不必要的文件和清理系统
RUN rm -rf /usr/share/nginx/html/*.map \
    && find /usr/share/nginx/html -name "*.txt" -delete \
    && find /usr/share/nginx/html -name ".*" -delete || true

# 暴露端口
EXPOSE 8080

# 切换到非特权用户
USER nginxuser

# 健康检查（使用非特权端口）
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# 使用 dumb-init 作为PID 1
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# 启动命令（非特权用户运行）
CMD ["nginx", "-g", "daemon off;"]