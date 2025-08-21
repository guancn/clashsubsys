<template>
  <div class="help-container">
    <el-card class="help-card">
      <template #header>
        <div class="card-header">
          <h2>使用帮助</h2>
        </div>
      </template>
      
      <el-scrollbar height="600px">
        <div class="help-content">
          <el-collapse v-model="activeNames" accordion>
            <el-collapse-item title="什么是订阅转换？" name="1">
              <p>订阅转换是将不同格式的代理订阅链接转换为 Clash 格式的服务。它可以帮助您：</p>
              <ul>
                <li>将机场提供的订阅链接转换为 Clash 配置</li>
                <li>自定义代理规则和分组</li>
                <li>合并多个订阅源</li>
                <li>添加自定义规则和节点过滤</li>
              </ul>
            </el-collapse-item>
            
            <el-collapse-item title="如何使用本服务？" name="2">
              <ol>
                <li><strong>输入订阅链接：</strong>在转换页面粘贴您的代理订阅地址</li>
                <li><strong>选择配置模板：</strong>根据需要选择合适的规则模板</li>
                <li><strong>自定义设置：</strong>配置节点过滤、重命名等选项</li>
                <li><strong>生成配置：</strong>点击转换按钮生成 Clash 配置</li>
                <li><strong>导入使用：</strong>将生成的链接导入到 Clash 客户端</li>
              </ol>
            </el-collapse-item>
            
            <el-collapse-item title="支持的订阅格式" name="3">
              <div class="protocol-list">
                <el-tag v-for="protocol in protocols" :key="protocol" type="info" class="protocol-tag">
                  {{ protocol }}
                </el-tag>
              </div>
            </el-collapse-item>
            
            <el-collapse-item title="常见问题" name="4">
              <div class="faq-section">
                <h4>Q: 转换失败怎么办？</h4>
                <p>A: 请检查订阅链接是否有效，确保网络连接正常。如果问题持续，请联系技术支持。</p>
                
                <h4>Q: 转换后的配置如何使用？</h4>
                <p>A: 复制生成的订阅链接，在 Clash 客户端中添加为新的配置文件即可。</p>
                
                <h4>Q: 是否支持自定义规则？</h4>
                <p>A: 是的，您可以在转换时选择不同的规则模板，或者添加自定义规则。</p>
              </div>
            </el-collapse-item>
            
            <el-collapse-item title="联系我们" name="5">
              <div class="contact-info">
                <p>如果您遇到问题或有建议，欢迎联系我们：</p>
                <ul>
                  <li>GitHub: <a href="https://github.com/guancn/clashsubsys" target="_blank">项目地址</a></li>
                  <li>Email: support@example.com</li>
                </ul>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-scrollbar>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeNames = ref(['1'])

const protocols = [
  'SS (Shadowsocks)',
  'SSR (ShadowsocksR)', 
  'V2Ray (VMess)',
  'VLESS',
  'Trojan',
  'Hysteria',
  'Hysteria2',
  'TUIC',
  'WireGuard'
]
</script>

<style lang="scss" scoped>
.help-container {
  padding: 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.help-card {
  max-width: 1000px;
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

.help-content {
  padding: 20px;
}

.protocol-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.protocol-tag {
  margin: 4px 0;
}

.faq-section {
  h4 {
    color: #409eff;
    margin: 16px 0 8px 0;
    font-weight: 600;
  }
  
  p {
    margin: 8px 0;
    line-height: 1.6;
    color: #606266;
  }
}

.contact-info {
  p {
    margin-bottom: 12px;
    color: #606266;
  }
  
  ul {
    list-style: none;
    padding: 0;
    
    li {
      margin: 8px 0;
      color: #606266;
      
      a {
        color: #409eff;
        text-decoration: none;
        
        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
}

:deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 16px;
}

:deep(.el-collapse-item__content) {
  color: #606266;
  line-height: 1.6;
}
</style>