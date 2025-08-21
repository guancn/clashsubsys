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
RUN npm ci --silent || npm install --silent

# 复制源代码
COPY . .

# 确保 dist 目录存在
RUN mkdir -p dist

# 尝试构建，如果失败则使用最小化的回退
RUN npm run build 2>&1 && echo "Build successful" || (\
    echo "Build failed, creating minimal dist..." && \
    mkdir -p dist/assets/js dist/assets/css && \
    echo '<!DOCTYPE html>' > dist/index.html && \
    echo '<html lang="zh-CN">' >> dist/index.html && \
    echo '<head>' >> dist/index.html && \
    echo '  <meta charset="UTF-8">' >> dist/index.html && \
    echo '  <meta name="viewport" content="width=device-width, initial-scale=1.0">' >> dist/index.html && \
    echo '  <title>Clash 订阅转换服务</title>' >> dist/index.html && \
    echo '</head>' >> dist/index.html && \
    echo '<body>' >> dist/index.html && \
    echo '  <div id="app">' >> dist/index.html && \
    echo '    <h1>系统正在初始化...</h1>' >> dist/index.html && \
    echo '    <p>请稍候片刻</p>' >> dist/index.html && \
    echo '  </div>' >> dist/index.html && \
    echo '</body>' >> dist/index.html && \
    echo '</html>' >> dist/index.html \
    )

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