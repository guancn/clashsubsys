<template>
  <div class="result-container">
    <el-card class="result-card">
      <template #header>
        <div class="card-header">
          <h2>转换结果</h2>
          <el-button type="text" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
        </div>
      </template>
      
      <div class="result-content" v-loading="loading">
        <div v-if="!loading && result">
          <!-- 转换成功 -->
          <div v-if="result.success" class="success-result">
            <div class="result-info">
              <el-alert
                title="转换成功"
                :description="`成功转换 ${result.nodeCount} 个节点`"
                type="success"
                :closable="false"
                show-icon
              />
            </div>
            
            <div class="result-actions">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-card class="action-card">
                    <h3>订阅链接</h3>
                    <div class="url-display">
                      <el-input
                        v-model="result.subscriptionUrl"
                        readonly
                        type="textarea"
                        :rows="3"
                      />
                    </div>
                    <div class="action-buttons">
                      <el-button type="primary" @click="copyUrl">
                        <el-icon><DocumentCopy /></el-icon>
                        复制链接
                      </el-button>
                      <el-button @click="downloadConfig">
                        <el-icon><Download /></el-icon>
                        下载配置
                      </el-button>
                    </div>
                  </el-card>
                </el-col>
                
                <el-col :span="12">
                  <el-card class="action-card">
                    <h3>使用说明</h3>
                    <div class="instructions">
                      <ol>
                        <li>复制上方的订阅链接</li>
                        <li>打开 Clash 客户端</li>
                        <li>添加新的配置文件</li>
                        <li>粘贴订阅链接并更新</li>
                        <li>选择代理节点开始使用</li>
                      </ol>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
            
            <!-- 节点列表 -->
            <div class="nodes-section">
              <h3>节点列表 ({{ result.nodes?.length || 0 }} 个)</h3>
              <el-table :data="result.nodes" stripe style="width: 100%" max-height="400">
                <el-table-column prop="name" label="节点名称" min-width="200" />
                <el-table-column prop="type" label="类型" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getProtocolType(row.type)">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="server" label="服务器" width="150" />
                <el-table-column prop="port" label="端口" width="80" />
                <el-table-column prop="country" label="地区" width="100">
                  <template #default="{ row }">
                    <span v-if="row.country">{{ row.country }}</span>
                    <span v-else class="text-muted">未知</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          
          <!-- 转换失败 -->
          <div v-else class="error-result">
            <el-alert
              title="转换失败"
              :description="result.error || '未知错误'"
              type="error"
              :closable="false"
              show-icon
            />
            
            <div class="error-actions">
              <el-button type="primary" @click="goBack">重新转换</el-button>
              <el-button @click="contactSupport">联系支持</el-button>
            </div>
          </div>
        </div>
        
        <!-- 加载状态 -->
        <div v-else-if="loading" class="loading-state">
          <el-skeleton :rows="5" animated />
        </div>
        
        <!-- 无数据 -->
        <div v-else class="empty-state">
          <el-empty description="没有找到转换结果">
            <el-button type="primary" @click="goBack">返回转换</el-button>
          </el-empty>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, DocumentCopy, Download } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const result = ref<any>(null)

const getProtocolType = (type: string) => {
  const typeMap: Record<string, string> = {
    'ss': 'info',
    'ssr': 'warning', 
    'vmess': 'success',
    'vless': 'success',
    'trojan': 'danger'
  }
  return typeMap[type] || 'info'
}

const copyUrl = async () => {
  try {
    await navigator.clipboard.writeText(result.value.subscriptionUrl)
    ElMessage.success('链接已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const downloadConfig = () => {
  const blob = new Blob([result.value.config], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'clash-config.yaml'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('配置文件下载成功')
}

const goBack = () => {
  router.push('/converter')
}

const contactSupport = () => {
  window.open('https://github.com/guancn/clashsubsys/issues', '_blank')
}

// 模拟获取转换结果
const fetchResult = async () => {
  try {
    loading.value = true
    
    // 这里应该根据 route.params.id 从 API 获取实际结果
    // 现在使用模拟数据
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    result.value = {
      success: true,
      nodeCount: 15,
      subscriptionUrl: `https://sub.guancn.me/clash/api/convert?id=${route.params.id}`,
      config: '# Clash 配置文件\n# 生成时间: ' + new Date().toLocaleString(),
      nodes: [
        { name: '香港 01', type: 'ss', server: 'hk01.example.com', port: 443, country: '香港' },
        { name: '美国 01', type: 'vmess', server: 'us01.example.com', port: 443, country: '美国' },
        { name: '日本 01', type: 'trojan', server: 'jp01.example.com', port: 443, country: '日本' },
        { name: '新加坡 01', type: 'ss', server: 'sg01.example.com', port: 443, country: '新加坡' },
        { name: '台湾 01', type: 'ssr', server: 'tw01.example.com', port: 443, country: '台湾' }
      ]
    }
  } catch (error) {
    result.value = {
      success: false,
      error: '获取转换结果失败'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchResult()
})
</script>

<style lang="scss" scoped>
.result-container {
  padding: 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.result-card {
  max-width: 1200px;
  margin: 0 auto;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  h2 {
    margin: 0;
    color: #2c3e50;
    font-size: 24px;
    font-weight: 600;
  }
}

.result-content {
  padding: 30px;
  min-height: 400px;
}

.result-info {
  margin-bottom: 30px;
}

.result-actions {
  margin-bottom: 40px;
}

.action-card {
  h3 {
    color: #2c3e50;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
  }
}

.url-display {
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.instructions {
  ol {
    color: #606266;
    line-height: 1.8;
    padding-left: 20px;
    
    li {
      margin: 8px 0;
    }
  }
}

.nodes-section {
  h3 {
    color: #2c3e50;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
    border-bottom: 2px solid #409eff;
    padding-bottom: 10px;
  }
}

.error-result {
  text-align: center;
}

.error-actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 15px;
}

.loading-state {
  padding: 40px;
}

.empty-state {
  padding: 60px 20px;
}

.text-muted {
  color: #c0c4cc;
}

@media (max-width: 768px) {
  .result-content {
    padding: 20px;
  }
  
  .result-actions {
    .el-col {
      margin-bottom: 20px;
    }
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>