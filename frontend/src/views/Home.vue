<template>
  <div class="home-container">
    <!-- 顶部导航 -->
    <header class="header">
      <div class="container">
        <div class="header-content">
          <div class="logo">
            <img src="/logo.svg" alt="Clash Converter" class="logo-img" />
            <span class="logo-text">Clash 订阅转换</span>
          </div>
          <nav class="nav">
            <router-link to="/converter" class="nav-link">开始转换</router-link>
            <router-link to="/help" class="nav-link">使用帮助</router-link>
            <router-link to="/about" class="nav-link">关于</router-link>
          </nav>
        </div>
      </div>
    </header>

    <!-- 主要内容 -->
    <main class="main">
      <!-- 英雄区域 -->
      <section class="hero">
        <div class="container">
          <div class="hero-content">
            <h1 class="hero-title">
              <span class="gradient-text">高效稳定</span>的 Clash 订阅转换服务
            </h1>
            <p class="hero-description">
              支持多种代理协议转换，提供自定义规则配置，让您的代理订阅更加智能和便捷
            </p>
            <div class="hero-actions">
              <el-button 
                type="primary" 
                size="large" 
                @click="$router.push('/converter')"
                class="cta-button"
              >
                <el-icon><Connection /></el-icon>
                立即开始转换
              </el-button>
              <el-button 
                size="large" 
                @click="scrollToFeatures"
                class="secondary-button"
              >
                <el-icon><InfoFilled /></el-icon>
                了解更多
              </el-button>
            </div>
          </div>
          <div class="hero-image">
            <div class="floating-card">
              <div class="card-header">
                <div class="card-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div class="card-title">Clash Config</div>
              </div>
              <div class="card-content">
                <div class="config-line">
                  <span class="key">port:</span>
                  <span class="value">7890</span>
                </div>
                <div class="config-line">
                  <span class="key">mode:</span>
                  <span class="value">rule</span>
                </div>
                <div class="config-line">
                  <span class="key">proxies:</span>
                </div>
                <div class="config-line indent">
                  <span class="key">- name:</span>
                  <span class="value">"🇭🇰 Hong Kong"</span>
                </div>
                <div class="config-line indent">
                  <span class="key">type:</span>
                  <span class="value">vmess</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 功能特性 -->
      <section class="features" ref="featuresRef">
        <div class="container">
          <div class="section-header">
            <h2 class="section-title">强大功能特性</h2>
            <p class="section-description">
              专业级的订阅转换服务，满足各种使用场景
            </p>
          </div>
          <div class="features-grid">
            <div 
              v-for="(feature, index) in features" 
              :key="index"
              class="feature-card"
              :class="{ 'animate' : featureVisible }"
              :style="{ animationDelay: `${index * 100}ms` }"
            >
              <div class="feature-icon">
                <component :is="feature.icon" />
              </div>
              <h3 class="feature-title">{{ feature.title }}</h3>
              <p class="feature-description">{{ feature.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 支持协议 -->
      <section class="protocols">
        <div class="container">
          <div class="section-header">
            <h2 class="section-title">支持的协议</h2>
            <p class="section-description">
              兼容主流代理协议，满足不同需求
            </p>
          </div>
          <div class="protocols-grid">
            <div 
              v-for="(protocol, index) in protocols" 
              :key="index"
              class="protocol-card"
            >
              <div class="protocol-icon">
                {{ protocol.icon }}
              </div>
              <div class="protocol-name">{{ protocol.name }}</div>
              <div class="protocol-description">{{ protocol.description }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 统计信息 -->
      <section class="stats">
        <div class="container">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-number">{{ stats.conversions }}</div>
              <div class="stat-label">总转换次数</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ stats.protocols }}</div>
              <div class="stat-label">支持协议</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ stats.uptime }}</div>
              <div class="stat-label">服务可用率</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ stats.speed }}</div>
              <div class="stat-label">平均响应时间</div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-section">
            <h3>Clash 订阅转换</h3>
            <p>高效稳定的代理订阅转换服务</p>
          </div>
          <div class="footer-section">
            <h4>快速链接</h4>
            <ul>
              <li><router-link to="/converter">订阅转换</router-link></li>
              <li><router-link to="/help">使用帮助</router-link></li>
              <li><router-link to="/about">关于我们</router-link></li>
            </ul>
          </div>
          <div class="footer-section">
            <h4>技术支持</h4>
            <ul>
              <li><a href="/docs" target="_blank">API 文档</a></li>
              <li><a href="https://github.com" target="_blank">GitHub</a></li>
              <li><a href="mailto:support@example.com">联系我们</a></li>
            </ul>
          </div>
        </div>
        <div class="footer-bottom">
          <p>&copy; {{ currentYear }} Clash 订阅转换服务. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  Connection, 
  InfoFilled, 
  Lightning, 
  Shield, 
  Tools, 
  CloudUpload,
  Monitor,
  Setting
} from '@element-plus/icons-vue'

// 功能特性数据
const features = [
  {
    icon: Lightning,
    title: '快速转换',
    description: '基于高性能架构，秒级完成订阅转换，支持批量处理多个订阅链接'
  },
  {
    icon: Shield,
    title: '安全可靠',
    description: '采用安全的处理机制，不存储用户数据，保护您的隐私安全'
  },
  {
    icon: Tools,
    title: '灵活配置',
    description: '支持自定义规则、节点过滤、重命名等高级功能，满足个性化需求'
  },
  {
    icon: CloudUpload,
    title: '多格式支持',
    description: '支持输出 Clash、Surge、Quantumult X 等多种客户端格式'
  },
  {
    icon: Monitor,
    title: '实时监控',
    description: '提供转换状态监控、错误诊断等功能，确保服务稳定运行'
  },
  {
    icon: Setting,
    title: '易于集成',
    description: '提供 REST API 接口，支持第三方应用集成和自动化部署'
  }
]

// 支持的协议
const protocols = [
  { name: 'Shadowsocks', icon: 'SS', description: '经典稳定的代理协议' },
  { name: 'ShadowsocksR', icon: 'SSR', description: '增强版 SS 协议' },
  { name: 'VMess', icon: 'V2', description: 'V2Ray 核心协议' },
  { name: 'VLESS', icon: 'VL', description: '轻量级 V2Ray 协议' },
  { name: 'Trojan', icon: 'TJ', description: '模拟 HTTPS 流量' },
  { name: 'Hysteria', icon: 'HY', description: '基于 QUIC 的高速协议' },
  { name: 'TUIC', icon: 'TC', description: '基于 QUIC 的轻量协议' },
  { name: 'WireGuard', icon: 'WG', description: '现代化 VPN 协议' }
]

// 统计数据
const stats = ref({
  conversions: '10,000+',
  protocols: '8+',
  uptime: '99.9%',
  speed: '<2s'
})

// 响应式数据
const featuresRef = ref<HTMLElement>()
const featureVisible = ref(false)
const currentYear = new Date().getFullYear()

// 滚动到功能区域
const scrollToFeatures = () => {
  featuresRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// 监听滚动事件，实现动画效果
onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          featureVisible.value = true
        }
      })
    },
    { threshold: 0.2 }
  )
  
  if (featuresRef.value) {
    observer.observe(featuresRef.value)
  }
})
</script>

<style lang="scss" scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

// 顶部导航
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  z-index: 100;
  
  .header-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0;
  }
  
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .logo-img {
      width: 32px;
      height: 32px;
    }
    
    .logo-text {
      font-size: 20px;
      font-weight: 700;
      color: #2c3e50;
    }
  }
  
  .nav {
    display: flex;
    gap: 32px;
    
    .nav-link {
      color: #64748b;
      text-decoration: none;
      font-weight: 500;
      transition: color 0.3s;
      
      &:hover, &.router-link-active {
        color: #409eff;
      }
    }
  }
}

// 主要内容
.main {
  margin-top: 80px;
}

// 英雄区域
.hero {
  padding: 120px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  overflow: hidden;
  
  .container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 80px;
    align-items: center;
  }
  
  .hero-title {
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 24px;
    
    .gradient-text {
      background: linear-gradient(135deg, #ffd700 0%, #ffeb3b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
  }
  
  .hero-description {
    font-size: 1.25rem;
    line-height: 1.6;
    margin-bottom: 40px;
    opacity: 0.9;
  }
  
  .hero-actions {
    display: flex;
    gap: 16px;
    
    .cta-button {
      padding: 16px 32px;
      font-size: 16px;
      font-weight: 600;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(64, 158, 255, 0.3);
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(64, 158, 255, 0.4);
      }
    }
    
    .secondary-button {
      background: rgba(255, 255, 255, 0.1);
      border: 2px solid rgba(255, 255, 255, 0.3);
      color: white;
      backdrop-filter: blur(10px);
      
      &:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
        transform: translateY(-2px);
      }
    }
  }
  
  .hero-image {
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    
    .floating-card {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(20px);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
      animation: float 6s ease-in-out infinite;
      min-width: 320px;
      
      .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid #eee;
        
        .card-dots {
          display: flex;
          gap: 8px;
          
          span {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff5f56;
            
            &:nth-child(2) {
              background: #ffbd2e;
            }
            
            &:nth-child(3) {
              background: #27ca3f;
            }
          }
        }
        
        .card-title {
          font-weight: 600;
          color: #2c3e50;
        }
      }
      
      .card-content {
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 14px;
        line-height: 1.6;
        
        .config-line {
          display: flex;
          margin-bottom: 8px;
          
          &.indent {
            padding-left: 20px;
          }
          
          .key {
            color: #e74c3c;
            font-weight: 600;
            margin-right: 8px;
          }
          
          .value {
            color: #27ae60;
          }
        }
      }
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-20px);
  }
}

// 功能特性
.features {
  padding: 120px 0;
  background: white;
  
  .section-header {
    text-align: center;
    margin-bottom: 80px;
    
    .section-title {
      font-size: 2.5rem;
      font-weight: 700;
      color: #2c3e50;
      margin-bottom: 16px;
    }
    
    .section-description {
      font-size: 1.125rem;
      color: #64748b;
      max-width: 600px;
      margin: 0 auto;
    }
  }
  
  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 40px;
    
    .feature-card {
      text-align: center;
      padding: 40px 24px;
      border-radius: 16px;
      background: white;
      border: 1px solid #e2e8f0;
      transition: all 0.3s ease;
      opacity: 0;
      transform: translateY(30px);
      
      &.animate {
        opacity: 1;
        transform: translateY(0);
      }
      
      &:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
        border-color: #409eff;
      }
      
      .feature-icon {
        width: 64px;
        height: 64px;
        margin: 0 auto 24px;
        background: linear-gradient(135deg, #409eff, #66b3ff);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 24px;
      }
      
      .feature-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 12px;
      }
      
      .feature-description {
        color: #64748b;
        line-height: 1.6;
      }
    }
  }
}

// 支持协议
.protocols {
  padding: 120px 0;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  
  .protocols-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 24px;
    
    .protocol-card {
      text-align: center;
      padding: 24px 16px;
      background: white;
      border-radius: 12px;
      transition: transform 0.3s ease;
      
      &:hover {
        transform: translateY(-4px);
      }
      
      .protocol-icon {
        width: 48px;
        height: 48px;
        margin: 0 auto 12px;
        background: linear-gradient(135deg, #409eff, #66b3ff);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 14px;
      }
      
      .protocol-name {
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 4px;
      }
      
      .protocol-description {
        font-size: 12px;
        color: #64748b;
      }
    }
  }
}

// 统计信息
.stats {
  padding: 80px 0;
  background: #2c3e50;
  color: white;
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 40px;
    
    .stat-card {
      text-align: center;
      
      .stat-number {
        font-size: 3rem;
        font-weight: 800;
        color: #ffd700;
        margin-bottom: 8px;
      }
      
      .stat-label {
        font-size: 1rem;
        opacity: 0.8;
      }
    }
  }
}

// 页脚
.footer {
  background: #1a202c;
  color: white;
  padding: 60px 0 20px;
  
  .footer-content {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 40px;
    margin-bottom: 40px;
    
    .footer-section {
      h3, h4 {
        margin-bottom: 16px;
        color: #ffd700;
      }
      
      p {
        opacity: 0.8;
        line-height: 1.6;
      }
      
      ul {
        list-style: none;
        
        li {
          margin-bottom: 8px;
          
          a {
            color: #cbd5e0;
            text-decoration: none;
            transition: color 0.3s;
            
            &:hover {
              color: #409eff;
            }
          }
        }
      }
    }
  }
  
  .footer-bottom {
    text-align: center;
    padding-top: 20px;
    border-top: 1px solid #2d3748;
    opacity: 0.6;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .hero {
    .container {
      grid-template-columns: 1fr;
      gap: 40px;
      text-align: center;
    }
    
    .hero-title {
      font-size: 2.5rem;
    }
    
    .hero-actions {
      justify-content: center;
    }
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .protocols-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .footer-content {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>