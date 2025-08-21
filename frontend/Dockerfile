# 简化的前端 Dockerfile

# 构建阶段
FROM node:18-alpine as builder

# 设置工作目录
WORKDIR /app

# 接收构建参数
ARG VITE_API_BASE_URL=https://sub.guancn.me/clash/api
ARG VITE_APP_PREFIX=/clash

# 设置环境变量
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_PREFIX=$VITE_APP_PREFIX
ENV NODE_ENV=production

# 复制 package 文件
COPY package.json package-lock.json* ./

# 安装依赖（包含sass支持）
RUN if [ -f package-lock.json ]; then \
        npm ci --no-audit --no-fund; \
    else \
        npm install --no-audit --no-fund; \
    fi

# 复制源代码
COPY . .

# 确保 dist 目录存在
RUN mkdir -p dist

# 调试信息
RUN echo "=== Build Environment ===" && \
    echo "Node version: $(node --version)" && \
    echo "NPM version: $(npm --version)" && \
    echo "Working directory: $(pwd)" && \
    echo "Environment variables:" && \
    printenv | grep VITE_ && \
    echo "Package.json scripts:" && \
    cat package.json | grep -A 10 '"scripts"' && \
    echo "Node modules check:" && \
    ls -la node_modules/.bin/vite || echo "Vite not found in node_modules" && \
    echo "Vite executable check:" && \
    which vite || echo "Vite command not in PATH" && \
    echo "NPX check:" && \
    npx vite --version || echo "NPX vite failed" && \
    echo "========================="

# 构建应用 - 必须成功
RUN npx vite build --mode production

# 生产阶段
FROM nginx:alpine

# 安装必要工具
RUN apk add --no-cache curl

# 复制构建产物到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 设置基本权限（使用 root 用户简化）
RUN chmod -R 755 /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["nginx", "-g", "daemon off;"]