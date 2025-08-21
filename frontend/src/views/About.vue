<template>
  <div class="about-container">
    <el-card class="about-card">
      <template #header>
        <div class="card-header">
          <h2>关于我们</h2>
        </div>
      </template>
      
      <div class="about-content">
        <div class="intro-section">
          <h3>项目介绍</h3>
          <p>
            Clash 订阅转换服务是一个高性能、现代化的代理订阅转换工具，
            基于 FastAPI + Vue.js 3 构建，支持多种代理协议转换和自定义规则配置。
          </p>
        </div>
        
        <div class="features-section">
          <h3>核心特性</h3>
          <el-row :gutter="20">
            <el-col :span="12" v-for="feature in features" :key="feature.title">
              <div class="feature-item">
                <el-icon class="feature-icon" :color="feature.color">
                  <component :is="feature.icon" />
                </el-icon>
                <h4>{{ feature.title }}</h4>
                <p>{{ feature.description }}</p>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <div class="tech-stack-section">
          <h3>技术栈</h3>
          <div class="tech-categories">
            <div class="tech-category">
              <h4>前端技术</h4>
              <ul>
                <li>Vue.js 3 + TypeScript</li>
                <li>Element Plus UI 框架</li>
                <li>Pinia 状态管理</li>
                <li>Vite 构建工具</li>
              </ul>
            </div>
            <div class="tech-category">
              <h4>后端技术</h4>
              <ul>
                <li>Python FastAPI</li>
                <li>异步 HTTP 处理</li>
                <li>Pydantic 数据验证</li>
                <li>内存缓存机制</li>
              </ul>
            </div>
            <div class="tech-category">
              <h4>部署技术</h4>
              <ul>
                <li>Docker 容器化</li>
                <li>Nginx 反向代理</li>
                <li>SSL/HTTPS 支持</li>
                <li>自动化部署脚本</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="stats-section">
          <h3>项目统计</h3>
          <el-row :gutter="20">
            <el-col :span="6" v-for="stat in stats" :key="stat.label">
              <div class="stat-item">
                <div class="stat-number">{{ stat.value }}</div>
                <div class="stat-label">{{ stat.label }}</div>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <div class="contact-section">
          <h3>开源地址</h3>
          <div class="links">
            <el-button type="primary" @click="openGitHub">
              <el-icon><Share /></el-icon>
              GitHub 仓库
            </el-button>
            <el-button type="success" @click="openIssues">
              <el-icon><ChatDotRound /></el-icon>
              问题反馈
            </el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { 
  Cpu, 
  Monitor, 
  Setting, 
  Share, 
  ChatDotRound,
  Connection,
  Shield,
  Lightning
} from '@element-plus/icons-vue'

const features = [
  {
    title: '多协议支持',
    description: '支持 SS、SSR、V2Ray、Trojan 等 8+ 种主流代理协议',
    icon: Connection,
    color: '#409eff'
  },
  {
    title: '高性能处理',
    description: '异步处理架构，支持大量节点的高效转换',
    icon: Lightning,
    color: '#67c23a'
  },
  {
    title: '安全可靠',
    description: 'HTTPS 加密传输，安全头配置，速率限制保护',
    icon: Shield,
    color: '#e6a23c'
  },
  {
    title: '易于部署',
    description: 'Docker 容器化部署，一键安装，支持多种部署方式',
    icon: Setting,
    color: '#f56c6c'
  }
]

const stats = [
  { label: '支持协议', value: '8+' },
  { label: '代码行数', value: '10K+' },
  { label: '项目文件', value: '50+' },
  { label: '版本号', value: 'v1.0' }
]

const openGitHub = () => {
  window.open('https://github.com/guancn/clashsubsys', '_blank')
}

const openIssues = () => {
  window.open('https://github.com/guancn/clashsubsys/issues', '_blank')
}
</script>

<style lang="scss" scoped>
.about-container {
  padding: 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.about-card {
  max-width: 1200px;
  margin: 0 auto;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  text-align: center;
  
  h2 {
    margin: 0;
    color: #2c3e50;
    font-size: 24px;
    font-weight: 600;
  }
}

.about-content {
  padding: 30px;
}

.intro-section, 
.features-section, 
.tech-stack-section, 
.stats-section, 
.contact-section {
  margin-bottom: 40px;
  
  h3 {
    color: #2c3e50;
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 20px;
    border-bottom: 2px solid #409eff;
    padding-bottom: 10px;
  }
}

.intro-section p {
  font-size: 16px;
  line-height: 1.8;
  color: #606266;
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
}

.feature-item {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  background: #f8f9fa;
  margin-bottom: 20px;
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  
  .feature-icon {
    font-size: 32px;
    margin-bottom: 15px;
  }
  
  h4 {
    color: #2c3e50;
    margin: 10px 0;
    font-size: 16px;
    font-weight: 600;
  }
  
  p {
    color: #909399;
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
  }
}

.tech-categories {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.tech-category {
  h4 {
    color: #409eff;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 15px;
  }
  
  ul {
    list-style: none;
    padding: 0;
    
    li {
      padding: 8px 0;
      color: #606266;
      border-bottom: 1px solid #f0f0f0;
      
      &:last-child {
        border-bottom: none;
      }
    }
  }
}

.stat-item {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: white;
  
  .stat-number {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 8px;
  }
  
  .stat-label {
    font-size: 14px;
    opacity: 0.9;
  }
}

.links {
  text-align: center;
  
  .el-button {
    margin: 0 10px;
    padding: 12px 24px;
    font-size: 16px;
  }
}

@media (max-width: 768px) {
  .about-content {
    padding: 20px;
  }
  
  .tech-categories {
    grid-template-columns: 1fr;
  }
  
  .feature-item {
    height: auto;
    min-height: 150px;
  }
}
</style>