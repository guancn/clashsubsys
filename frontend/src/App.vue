<template>
  <div id="app">
    <!-- 全局加载遮罩 -->
    <el-loading-service
      v-if="globalLoading"
      :lock="true"
      text="处理中..."
      background="rgba(0, 0, 0, 0.7)"
    />
    
    <!-- 路由视图 -->
    <router-view />
    
    <!-- 全局消息提示容器 -->
    <teleport to="body">
      <div id="message-container"></div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { provide } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// 全局加载状态
const globalLoading = computed(() => appStore.globalLoading)

// 提供全局方法
provide('$message', ElMessage)
provide('$notify', ElNotification)
provide('$confirm', ElMessageBox.confirm)
provide('$alert', ElMessageBox.alert)

// 监听路由变化，设置页面标题
watch(() => router.currentRoute.value, (route) => {
  document.title = route.meta?.title 
    ? `${route.meta.title} - Clash 订阅转换`
    : 'Clash 订阅转换 - 高效稳定的代理订阅转换服务'
}, { immediate: true })
</script>

<style lang="scss">
// 全局样式重置
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  height: 100%;
  font-size: 14px;
}

body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
    'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 
    'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
  line-height: 1.5;
  color: #303133;
  background-color: #f5f5f5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
  min-height: 100vh;
}

// Element Plus 样式定制
.el-button {
  border-radius: 6px;
  font-weight: 500;
  
  &.el-button--primary {
    background: linear-gradient(135deg, #409eff 0%, #66b3ff 100%);
    border: none;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
    
    &:hover {
      background: linear-gradient(135deg, #66b3ff 0%, #409eff 100%);
      box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
      transform: translateY(-1px);
    }
    
    &:active {
      transform: translateY(0);
    }
  }
}

.el-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }
  
  .el-card__header {
    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    border-bottom: 1px solid #ebeef5;
    padding: 18px 20px;
    font-weight: 600;
    color: #303133;
  }
  
  .el-card__body {
    padding: 24px;
  }
}

.el-input {
  .el-input__wrapper {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    }
    
    &.is-focus {
      box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
    }
  }
}

.el-textarea {
  .el-textarea__inner {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    }
    
    &:focus {
      box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
    }
  }
}

// 响应式布局
@media (max-width: 768px) {
  html {
    font-size: 12px;
  }
  
  .el-card .el-card__body {
    padding: 16px;
  }
}

// 滚动条样式
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
  
  &:hover {
    background: #a8a8a8;
  }
}

// 动画类
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateY(20px);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

// 辅助类
.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

.text-left {
  text-align: left;
}

.full-width {
  width: 100%;
}

.mt-0 { margin-top: 0; }
.mt-1 { margin-top: 0.25rem; }
.mt-2 { margin-top: 0.5rem; }
.mt-3 { margin-top: 0.75rem; }
.mt-4 { margin-top: 1rem; }
.mt-5 { margin-top: 1.25rem; }

.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 0.25rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-5 { margin-bottom: 1.25rem; }

.ml-0 { margin-left: 0; }
.ml-1 { margin-left: 0.25rem; }
.ml-2 { margin-left: 0.5rem; }
.ml-3 { margin-left: 0.75rem; }
.ml-4 { margin-left: 1rem; }
.ml-5 { margin-left: 1.25rem; }

.mr-0 { margin-right: 0; }
.mr-1 { margin-right: 0.25rem; }
.mr-2 { margin-right: 0.5rem; }
.mr-3 { margin-right: 0.75rem; }
.mr-4 { margin-right: 1rem; }
.mr-5 { margin-right: 1.25rem; }
</style>