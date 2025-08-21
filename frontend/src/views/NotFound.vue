<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <div class="error-animation">
        <div class="number">4</div>
        <div class="illustration">
          <div class="circle"></div>
          <div class="clip">
            <div class="paper">
              <div class="face">
                <div class="eyes">
                  <div class="eye eye-left"></div>
                  <div class="eye eye-right"></div>
                </div>
                <div class="rosyCheeks rosyCheeks-left"></div>
                <div class="rosyCheeks rosyCheeks-right"></div>
                <div class="mouth"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="number">4</div>
      </div>
      
      <div class="error-text">
        <h1>页面走丢了</h1>
        <p>抱歉，您访问的页面不存在或已被移动。</p>
        <div class="suggestions">
          <h3>您可以尝试：</h3>
          <ul>
            <li>检查 URL 是否输入正确</li>
            <li>返回首页重新开始</li>
            <li>使用导航菜单查找内容</li>
            <li>如果问题持续，请联系技术支持</li>
          </ul>
        </div>
      </div>
      
      <div class="error-actions">
        <el-button type="primary" size="large" @click="goHome">
          <el-icon><House /></el-icon>
          返回首页
        </el-button>
        <el-button size="large" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回上页
        </el-button>
        <el-button size="large" @click="goConverter">
          <el-icon><Setting /></el-icon>
          开始转换
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { House, ArrowLeft, Setting } from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

const goConverter = () => {
  router.push('/converter')
}
</script>

<style lang="scss" scoped>
.not-found-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.not-found-content {
  text-align: center;
  background: white;
  border-radius: 20px;
  padding: 60px 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  width: 100%;
}

.error-animation {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 40px;
  
  .number {
    font-size: 120px;
    font-weight: bold;
    color: #409eff;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
  }
  
  .illustration {
    margin: 0 20px;
    position: relative;
    
    .circle {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: #409eff;
      position: relative;
      animation: float 3s ease-in-out infinite;
    }
    
    .clip {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: #409eff;
      position: absolute;
      top: 0;
      overflow: hidden;
      
      .paper {
        width: 60px;
        height: 60px;
        background: white;
        border-radius: 50%;
        position: absolute;
        top: 10px;
        left: 10px;
        
        .face {
          position: relative;
          width: 100%;
          height: 100%;
          
          .eyes {
            position: absolute;
            top: 15px;
            left: 50%;
            transform: translateX(-50%);
            
            .eye {
              width: 8px;
              height: 8px;
              background: #333;
              border-radius: 50%;
              display: inline-block;
              animation: blink 3s ease-in-out infinite;
              
              &.eye-left {
                margin-right: 10px;
              }
            }
          }
          
          .rosyCheeks {
            position: absolute;
            width: 10px;
            height: 8px;
            background: #ff9999;
            border-radius: 50%;
            top: 25px;
            
            &.rosyCheeks-left {
              left: 8px;
            }
            
            &.rosyCheeks-right {
              right: 8px;
            }
          }
          
          .mouth {
            position: absolute;
            bottom: 15px;
            left: 50%;
            transform: translateX(-50%);
            width: 20px;
            height: 10px;
            border: 2px solid #333;
            border-top: none;
            border-radius: 0 0 20px 20px;
          }
        }
      }
    }
  }
}

.error-text {
  margin-bottom: 40px;
  
  h1 {
    font-size: 36px;
    color: #2c3e50;
    margin-bottom: 20px;
    font-weight: 600;
  }
  
  p {
    font-size: 18px;
    color: #606266;
    margin-bottom: 30px;
    line-height: 1.6;
  }
  
  .suggestions {
    text-align: left;
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
    
    h3 {
      color: #409eff;
      font-size: 16px;
      margin-bottom: 15px;
    }
    
    ul {
      color: #606266;
      line-height: 1.8;
      padding-left: 20px;
      
      li {
        margin: 8px 0;
      }
    }
  }
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  flex-wrap: wrap;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes blink {
  0%, 90%, 100% {
    height: 8px;
  }
  95% {
    height: 2px;
  }
}

@media (max-width: 768px) {
  .not-found-content {
    padding: 40px 20px;
  }
  
  .error-animation {
    .number {
      font-size: 80px;
    }
    
    .illustration {
      margin: 0 10px;
      
      .circle,
      .clip {
        width: 60px;
        height: 60px;
      }
      
      .paper {
        width: 45px;
        height: 45px;
        top: 7.5px;
        left: 7.5px;
      }
    }
  }
  
  .error-text h1 {
    font-size: 28px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
    
    .el-button {
      width: 200px;
    }
  }
}
</style>