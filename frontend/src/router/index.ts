import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: '首页',
      keepAlive: false
    }
  },
  {
    path: '/converter',
    name: 'Converter',
    component: () => import('@/views/Converter.vue'),
    meta: {
      title: '订阅转换',
      keepAlive: true
    }
  },
  {
    path: '/help',
    name: 'Help',
    component: () => import('@/views/Help.vue'),
    meta: {
      title: '使用帮助',
      keepAlive: true
    }
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('@/views/About.vue'),
    meta: {
      title: '关于我们',
      keepAlive: true
    }
  },
  {
    path: '/result/:id',
    name: 'Result',
    component: () => import('@/views/Result.vue'),
    meta: {
      title: '转换结果',
      keepAlive: false
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在'
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta?.title 
    ? `${to.meta.title} - Clash 订阅转换`
    : 'Clash 订阅转换 - 高效稳定的代理订阅转换服务'
  
  next()
})

// 全局后置钩子
router.afterEach((to, from) => {
  // 页面访问统计等逻辑
  if (import.meta.env.DEV) {
    console.log(`路由跳转: ${from.path} -> ${to.path}`)
  }
})

export default router