<template>
  <div class="converter-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="container">
        <h1 class="page-title">订阅转换</h1>
        <p class="page-description">将您的代理订阅转换为 Clash 配置文件</p>
      </div>
    </div>

    <!-- 主要内容 -->
    <div class="page-content">
      <div class="container">
        <div class="converter-layout">
          <!-- 左侧表单 -->
          <div class="form-section">
            <el-card class="converter-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Connection /></el-icon>
                  <span>转换配置</span>
                </div>
              </template>

              <el-form 
                :model="converterStore.form" 
                label-width="120px"
                size="large"
              >
                <!-- 订阅链接 -->
                <el-form-item label="订阅链接" required>
                  <div class="url-inputs">
                    <div 
                      v-for="(url, index) in converterStore.form.url" 
                      :key="index"
                      class="url-input-group"
                    >
                      <el-input
                        v-model="converterStore.form.url[index]"
                        placeholder="请输入订阅链接，如: https://example.com/subscribe"
                        clearable
                        :prefix-icon="Link"
                      >
                        <template #suffix>
                          <el-button
                            v-if="converterStore.form.url.length > 1"
                            link
                            type="danger"
                            @click="converterStore.removeUrl(index)"
                          >
                            <el-icon><Close /></el-icon>
                          </el-button>
                        </template>
                      </el-input>
                    </div>
                    <el-button
                      type="primary"
                      @click="converterStore.addUrl"
                      :disabled="converterStore.form.url.length >= 10"
                      class="add-url-btn"
                    >
                      <el-icon><Plus /></el-icon>
                      添加订阅链接
                    </el-button>
                  </div>
                </el-form-item>

                <!-- 目标格式 -->
                <el-form-item label="目标格式">
                  <el-select 
                    v-model="converterStore.form.target" 
                    style="width: 100%"
                  >
                    <el-option label="Clash" value="clash" />
                    <el-option label="Surge" value="surge" />
                    <el-option label="Quantumult X" value="quantumult-x" />
                    <el-option label="Loon" value="loon" />
                    <el-option label="Surfboard" value="surfboard" />
                  </el-select>
                </el-form-item>

                <!-- 远程配置 -->
                <el-form-item label="远程配置">
                  <el-input
                    v-model="converterStore.form.remote_config"
                    placeholder="可选：远程配置规则文件地址 (ini 格式)"
                    clearable
                    :prefix-icon="Document"
                  />
                  <div class="form-tip">
                    支持 ACL4SSR、Subconverter 等规则配置文件
                  </div>
                </el-form-item>

                <!-- 节点过滤 -->
                <el-collapse accordion class="filter-collapse">
                  <el-collapse-item name="filter" title="节点过滤设置">
                    <el-form-item label="包含关键词">
                      <el-input
                        v-model="converterStore.form.include"
                        placeholder="支持正则表达式，如: 香港|新加坡|美国"
                        clearable
                      />
                      <div class="form-tip">
                        只保留包含指定关键词的节点
                      </div>
                    </el-form-item>

                    <el-form-item label="排除关键词">
                      <el-input
                        v-model="converterStore.form.exclude"
                        placeholder="支持正则表达式，如: 过期|到期|剩余"
                        clearable
                      />
                      <div class="form-tip">
                        排除包含指定关键词的节点
                      </div>
                    </el-form-item>

                  </el-collapse-item>
                </el-collapse>

                <!-- 高级选项 -->
                <el-collapse accordion class="advanced-collapse">
                  <el-collapse-item name="advanced" title="高级选项">
                    <div class="options-grid">
                      <el-checkbox 
                        v-model="converterStore.form.emoji"
                        label="启用 Emoji"
                        size="large"
                      />
                      <el-checkbox 
                        v-model="converterStore.form.udp"
                        label="启用 UDP"
                        size="large"
                      />
                      <el-checkbox 
                        v-model="converterStore.form.tfo"
                        label="启用 TFO"
                        size="large"
                      />
                      <el-checkbox 
                        v-model="converterStore.form.scv"
                        label="跳过证书验证"
                        size="large"
                      />
                      <el-checkbox 
                        v-model="converterStore.form.fdn"
                        label="过滤非默认端口"
                        size="large"
                      />
                      <el-checkbox 
                        v-model="converterStore.form.sort"
                        label="节点排序"
                        size="large"
                      />
                    </div>
                  </el-collapse-item>
                </el-collapse>

                <!-- 配置文件名 -->
                <el-form-item label="配置文件名">
                  <el-input
                    v-model="converterStore.form.filename"
                    placeholder="请输入文件名，如: tt (将生成 tt.yml)"
                    clearable
                    :prefix-icon="Document"
                  />
                  <div class="form-tip">
                    自定义生成的YAML配置文件名称，不填写将使用默认名称
                  </div>
                </el-form-item>

                <!-- 预设配置 -->
                <el-form-item label="预设配置">
                  <el-select
                    v-model="selectedPreset"
                    placeholder="选择预设配置"
                    @change="applyPreset"
                    clearable
                    style="width: 100%"
                  >
                    <el-option
                      v-for="(preset, index) in converterStore.presets"
                      :key="index"
                      :label="preset.name"
                      :value="index"
                    >
                      <div class="preset-option">
                        <div class="preset-name">{{ preset.name }}</div>
                        <div class="preset-desc">{{ preset.description }}</div>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>

                <!-- 操作按钮 -->
                <div class="action-buttons">
                  <el-button
                    type="primary"
                    size="large"
                    :loading="converterStore.converting"
                    @click="handleConvert"
                    class="convert-btn"
                  >
                    <el-icon><Upload /></el-icon>
                    {{ converterStore.converting ? '转换中...' : '开始转换' }}
                  </el-button>
                  <el-button
                    size="large"
                    @click="handleReset"
                    :disabled="converterStore.converting"
                  >
                    <el-icon><Refresh /></el-icon>
                    重置
                  </el-button>
                  <el-dropdown @command="handleExport">
                    <el-button size="large">
                      <el-icon><Download /></el-icon>
                      导出配置
                      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="export">导出当前配置</el-dropdown-item>
                        <el-dropdown-item command="import" divided>导入配置文件</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </el-form>
            </el-card>
          </div>

          <!-- 右侧结果 -->
          <div class="result-section">
            <!-- 转换结果 -->
            <el-card v-if="converterStore.hasResult" class="result-card">
              <template #header>
                <div class="card-header">
                  <el-icon><SuccessFilled v-if="converterStore.isConversionSuccess" /><Warning v-else /></el-icon>
                  <span>转换结果</span>
                </div>
              </template>

              <div v-if="converterStore.isConversionSuccess" class="success-result">
                <el-result
                  icon="success"
                  title="转换成功！"
                  :sub-title="`成功转换 ${converterStore.currentResult?.nodes_count} 个节点`"
                >
                  <template #extra>
                    <div class="result-actions">
                      <el-button
                        type="primary"
                        @click="downloadConfig"
                        :loading="downloading"
                      >
                        <el-icon><Download /></el-icon>
                        下载配置
                      </el-button>
                      <el-button @click="copyConfig">
                        <el-icon><CopyDocument /></el-icon>
                        复制配置
                      </el-button>
                      <el-button @click="previewConfig">
                        <el-icon><View /></el-icon>
                        预览配置
                      </el-button>
                    </div>
                  </template>
                </el-result>

                <!-- 生成的订阅链接 -->
                <div v-if="subscriptionUrl" class="subscription-url">
                  <h4>订阅链接</h4>
                  <el-input
                    :value="subscriptionUrl"
                    readonly
                    class="url-input"
                  >
                    <template #append>
                      <el-button @click="copySubscriptionUrl">
                        <el-icon><CopyDocument /></el-icon>
                      </el-button>
                    </template>
                  </el-input>
                  <div class="url-tip">
                    可将此链接添加到 Clash 客户端作为订阅源
                  </div>
                </div>
              </div>

              <div v-else class="error-result">
                <el-result
                  icon="error"
                  title="转换失败"
                  :sub-title="converterStore.currentResult?.message"
                >
                  <template #extra>
                    <el-button type="primary" @click="handleConvert">
                      <el-icon><Refresh /></el-icon>
                      重新转换
                    </el-button>
                  </template>
                </el-result>
              </div>
            </el-card>

            <!-- 转换历史 -->
            <el-card v-if="converterStore.recentHistory.length > 0" class="history-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Clock /></el-icon>
                  <span>转换历史</span>
                  <el-button
                    text
                    @click="converterStore.clearHistory"
                    class="clear-history-btn"
                  >
                    清空历史
                  </el-button>
                </div>
              </template>

              <div class="history-list">
                <div
                  v-for="(item, index) in converterStore.recentHistory"
                  :key="index"
                  class="history-item"
                >
                  <div class="history-info">
                    <div class="history-status">
                      <el-icon class="success" v-if="item.success"><SuccessFilled /></el-icon>
                      <el-icon class="error" v-else><CircleCloseFilled /></el-icon>
                    </div>
                    <div class="history-details">
                      <div class="history-nodes">{{ item.nodes_count }} 个节点</div>
                      <div class="history-time">{{ formatTime((item as any).timestamp) }}</div>
                    </div>
                  </div>
                  <div class="history-actions">
                    <el-button
                      text
                      @click="restoreFromHistory(index)"
                      :disabled="converterStore.converting"
                    >
                      恢复配置
                    </el-button>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 使用提示 -->
            <el-card class="tips-card">
              <template #header>
                <div class="card-header">
                  <el-icon><InfoFilled /></el-icon>
                  <span>使用提示</span>
                </div>
              </template>

              <div class="tips-content">
                <ul class="tips-list">
                  <li>支持同时添加多个订阅链接进行合并转换</li>
                  <li>可通过正则表达式精确过滤和重命名节点</li>
                  <li>远程配置文件支持 ACL4SSR、Subconverter 等规则</li>
                  <li>转换后的配置文件可直接导入 Clash 客户端</li>
                  <li>支持生成长期有效的订阅链接，便于自动更新</li>
                </ul>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </div>

    <!-- 配置预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      title="配置预览"
      width="80%"
      :before-close="handleClosePreview"
    >
      <el-tabs v-model="previewTab" class="preview-tabs">
        <el-tab-pane label="YAML 格式" name="yaml">
          <pre class="config-preview"><code>{{ previewContent }}</code></pre>
        </el-tab-pane>
        <el-tab-pane label="JSON 格式" name="json">
          <pre class="config-preview"><code>{{ previewJsonContent }}</code></pre>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPreviewDialog = false">关闭</el-button>
          <el-button type="primary" @click="copyPreviewContent">复制内容</el-button>
          <el-button type="success" @click="downloadPreviewConfig">下载文件</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 导入配置文件对话框 -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".json"
      style="display: none"
      @change="handleFileImport"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection, Link, Close, Plus, Document, Upload, Refresh, Download,
  ArrowDown, SuccessFilled, Warning, CopyDocument, View, Clock,
  CircleCloseFilled, InfoFilled
} from '@element-plus/icons-vue'
import { useConverterStore } from '@/stores/converter'
import { converterApi, copySubscriptionUrl as copyUrlToClipboard } from '@/api/converter'
import { formatTime } from '@/utils/time'
import yaml from 'js-yaml'

// 存储和状态
const converterStore = useConverterStore()

// 响应式数据
const downloading = ref(false)
const selectedPreset = ref<number | null>(null)
const showPreviewDialog = ref(false)
const previewTab = ref('yaml')
const previewContent = ref('')
const previewJsonContent = ref('')
const fileInputRef = ref()

// 计算属性
const subscriptionUrl = computed(() => {
  if (converterStore.currentResult?.download_url) {
    const baseUrl = window.location.origin
    return `${baseUrl}${converterStore.currentResult.download_url}`
  }
  return null
})

// 转换处理
const handleConvert = async () => {
  const validation = converterStore.validateForm()
  if (!validation.valid) {
    ElMessage.error(validation.errors[0])
    return
  }

  try {
    converterStore.setConverting(true)
    const result = await converterApi.convert(converterStore.form)
    converterStore.setResult(result)
    
    if (result.success) {
      ElMessage.success('转换成功！')
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    console.error('转换失败:', error)
    ElMessage.error('转换失败，请检查网络连接或联系管理员')
  } finally {
    converterStore.setConverting(false)
  }
}

// 重置表单
const handleReset = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重置所有配置吗？此操作不可恢复。',
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    converterStore.resetForm()
    selectedPreset.value = null
    ElMessage.success('已重置配置')
  } catch {
    // 用户取消
  }
}

// 应用预设配置
const applyPreset = (index: number) => {
  if (index !== null && index !== undefined) {
    converterStore.applyPreset(index)
    ElMessage.success('已应用预设配置')
  }
}


// 下载配置
const downloadConfig = async () => {
  if (!converterStore.currentResult?.download_url) {
    ElMessage.error('没有可下载的配置')
    return
  }

  try {
    downloading.value = true
    const configId = converterStore.currentResult.download_url.split('/').pop()!
    await converterApi.downloadConfig(configId, 'yaml', `clash_config_${Date.now()}.yaml`)
    ElMessage.success('配置文件下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请稍后重试')
  } finally {
    downloading.value = false
  }
}

// 复制配置
const copyConfig = async () => {
  if (!converterStore.currentResult?.config) {
    ElMessage.error('没有可复制的配置')
    return
  }

  try {
    await navigator.clipboard.writeText(converterStore.currentResult.config)
    ElMessage.success('配置已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败，请手动选择复制')
  }
}

// 预览配置
const previewConfig = () => {
  if (!converterStore.currentResult?.config) {
    ElMessage.error('没有可预览的配置')
    return
  }

  previewContent.value = converterStore.currentResult.config
  
  // 转换为 JSON 格式
  try {
    const yamlData = yaml.load(converterStore.currentResult.config)
    previewJsonContent.value = JSON.stringify(yamlData, null, 2)
  } catch (error) {
    previewJsonContent.value = '无法转换为 JSON 格式'
  }
  
  showPreviewDialog.value = true
}

// 复制订阅链接
const copySubscriptionUrl = async () => {
  if (!subscriptionUrl.value) {
    ElMessage.error('没有可复制的订阅链接')
    return
  }

  const success = await copyUrlToClipboard(subscriptionUrl.value)
  if (success) {
    ElMessage.success('订阅链接已复制到剪贴板')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 导出/导入配置
const handleExport = (command: string) => {
  if (command === 'export') {
    converterStore.exportConfig()
    ElMessage.success('配置文件已导出')
  } else if (command === 'import') {
    fileInputRef.value?.click()
  }
}

const handleFileImport = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  try {
    await converterStore.importConfig(file)
    ElMessage.success('配置文件导入成功')
    selectedPreset.value = null
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查文件格式')
  }
  
  // 清空文件输入
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// 从历史记录恢复配置
const restoreFromHistory = (index: number) => {
  converterStore.restoreFromHistory(index)
  ElMessage.success('配置已恢复')
  selectedPreset.value = null
}

// 预览对话框相关
const handleClosePreview = () => {
  showPreviewDialog.value = false
}

const copyPreviewContent = async () => {
  const content = previewTab.value === 'yaml' ? previewContent.value : previewJsonContent.value
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const downloadPreviewConfig = () => {
  const content = previewTab.value === 'yaml' ? previewContent.value : previewJsonContent.value
  const filename = `clash_config_${Date.now()}.${previewTab.value === 'yaml' ? 'yaml' : 'json'}`
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('文件下载成功')
}

// 初始化
onMounted(() => {
  converterStore.loadHistoryFromLocal()
})
</script>

<style lang="scss" scoped>
.converter-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-attachment: fixed;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding: 40px 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  
  .page-title {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 12px;
    text-align: center;
  }
  
  .page-description {
    color: #6b7280;
    font-size: 1.2rem;
    text-align: center;
    font-weight: 500;
  }
}

.page-content {
  padding: 40px 0;
}

.converter-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 40px;
  align-items: start;
}

.form-section {
  .converter-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border-radius: 16px;
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: #667eea;
    }
  }
  
  .url-inputs {
    .url-input-group {
      margin-bottom: 16px;
    }
    
    .add-url-btn {
      width: 100%;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      font-weight: 600;
      
      &:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
      }
      
      &:disabled {
        background: #e5e7eb;
        color: #9ca3af;
        box-shadow: none;
        transform: none;
      }
    }
  }
  
  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    line-height: 1.4;
  }
  
  .filter-collapse,
  .advanced-collapse,
  .rules-collapse {
    margin: 24px 0;
    
    :deep(.el-collapse-item__header) {
      font-weight: 500;
      color: #2c3e50;
    }
  }
  
  .options-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  
  
  .preset-option {
    .preset-name {
      font-weight: 500;
      color: #2c3e50;
    }
    
    .preset-desc {
      font-size: 12px;
      color: #909399;
      margin-top: 2px;
    }
  }
  
  .action-buttons {
    display: flex;
    gap: 12px;
    margin-top: 32px;
    
    .convert-btn {
      flex: 1;
      min-width: 140px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      font-weight: 600;
      height: 48px;
      font-size: 16px;
      
      &:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        transform: translateY(-2px);
      }
    }
  }
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  
  .result-card,
  .history-card,
  .tips-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border-radius: 16px;
    
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      color: #667eea;
      
      .clear-history-btn {
        margin-left: auto;
        color: #f56c6c;
      }
    }
  }
  
  .success-result {
    .result-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
      flex-wrap: wrap;
    }
    
    .subscription-url {
      margin-top: 24px;
      padding: 20px;
      background: #f8f9fa;
      border-radius: 8px;
      
      h4 {
        margin-bottom: 12px;
        color: #2c3e50;
      }
      
      .url-input {
        margin-bottom: 8px;
      }
      
      .url-tip {
        font-size: 12px;
        color: #909399;
      }
    }
  }
  
  .history-list {
    .history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid #f0f2f5;
      
      &:last-child {
        border-bottom: none;
      }
      
      .history-info {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .history-status {
          .success {
            color: #67c23a;
          }
          
          .error {
            color: #f56c6c;
          }
        }
        
        .history-details {
          .history-nodes {
            font-weight: 500;
            color: #2c3e50;
            font-size: 14px;
          }
          
          .history-time {
            font-size: 12px;
            color: #909399;
          }
        }
      }
    }
  }
  
  .tips-content {
    .tips-list {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 8px;
        color: #64748b;
        line-height: 1.5;
        
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }
}

// 预览对话框样式
.preview-tabs {
  .config-preview {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 16px;
    max-height: 500px;
    overflow-y: auto;
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    
    code {
      background: transparent;
      padding: 0;
      color: #2c3e50;
    }
  }
}

// 响应式设计
@media (max-width: 1200px) {
  .converter-layout {
    grid-template-columns: 1fr;
    
    .result-section {
      order: -1;
    }
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 24px 0;
    
    .page-title {
      font-size: 1.5rem;
    }
    
    .page-description {
      font-size: 1rem;
    }
  }
  
  .page-content {
    padding: 24px 0;
  }
  
  .action-buttons {
    flex-direction: column;
    
    .convert-btn {
      flex: none;
    }
  }
  
  .options-grid {
    grid-template-columns: 1fr;
  }
}
</style>