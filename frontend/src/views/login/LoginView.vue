<template>
  <div class="login-page">
    <div class="theme-switcher">
      <button class="theme-toggle" type="button" @click="toggleTheme">
        <span class="theme-toggle__dot" />
        <span class="theme-toggle__label">{{ isDark ? 'Dark Mode' : 'Light Mode' }}</span>
      </button>
    </div>

    <section class="login-shell">
      <div class="login-hero">
        <div class="hero-copy">
          <p class="hero-kicker">ZS2 Management System</p>
          <h1 class="hero-title">制丝车间智能管理中枢</h1>
          <p class="hero-description">
            把设备、监测、质量与安全数据汇聚到同一张控制界面里，让值守、排障和协同都更直接。
          </p>
        </div>

        <div class="hero-metrics">
          <div class="metric-item card-stagger">
            <span class="metric-label">System Status</span>
            <strong class="metric-value">Online</strong>
          </div>
          <div class="metric-item card-stagger">
            <span class="metric-label">SSO Access</span>
            <strong class="metric-value">Ready</strong>
          </div>
          <div class="metric-item card-stagger">
            <span class="metric-label">Response Flow</span>
            <strong class="metric-value">Realtime</strong>
          </div>
        </div>

        <div class="hero-panel">
          <div class="signal-grid">
            <div class="signal-card">
              <span class="signal-card__title">设备监测</span>
              <span class="signal-card__value">稳定巡航</span>
            </div>
            <div class="signal-card">
              <span class="signal-card__title">质量知识库</span>
              <span class="signal-card__value">快速检索</span>
            </div>
            <div class="signal-card">
              <span class="signal-card__title">安全隐患</span>
              <span class="signal-card__value">闭环追踪</span>
            </div>
            <div class="signal-card">
              <span class="signal-card__title">统一认证</span>
              <span class="signal-card__value">单点接入</span>
            </div>
          </div>
        </div>
      </div>

      <div class="login-card">
        <div class="login-card__header">
          <div class="login-brand">
            <div class="brand-icon">ZS</div>
            <div class="brand-text">
              <div class="brand-title">制丝车间</div>
              <div class="brand-sub">统一入口</div>
            </div>
          </div>

          <div class="login-caption">
            <h2 class="login-heading">登录系统</h2>
            <p class="login-subtitle">支持账号密码与云南中烟统一认证双入口</p>
          </div>
        </div>

        <el-alert
          v-if="ssoErrorMessage"
          :title="ssoErrorMessage"
          type="error"
          show-icon
          :closable="false"
          class="login-alert"
        />

        <el-form :model="form" class="login-form" @submit.prevent="handleLogin">
          <el-form-item>
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              autocomplete="username"
              :disabled="loading"
            >
              <template #prefix>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="7" cy="5" r="3"/>
                  <path d="M1 13c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
                </svg>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              autocomplete="current-password"
              show-password
              :disabled="loading"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="6" width="10" height="7" rx="1.5"/>
                  <path d="M4.5 6V4a2.5 2.5 0 015 0v2"/>
                </svg>
              </template>
            </el-input>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-submit"
            @click="handleLogin"
          >
            进入工作台
          </el-button>
        </el-form>

        <div class="sso-divider">
          <span class="sso-divider-line" />
          <span class="sso-divider-text">或使用统一认证</span>
          <span class="sso-divider-line" />
        </div>

        <el-button
          size="large"
          class="sso-btn"
          @click="handleSsoLogin"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
            <polyline points="10 17 15 12 10 7"/>
            <line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          云南中烟登录
        </el-button>

        <div class="login-footer">
          <span>统一认证成功后将直接建立本系统会话</span>
          <span>建议使用登记后的外网域名访问</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usersApi } from '@/api/users'
import { useUserStore } from '@/stores/user'
import { buildSsoLoginUrl, getSsoErrorMessage } from '@/utils/appBase'
import { useTheme } from '@/composables/useTheme'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { isDark, toggleTheme } = useTheme()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

const ssoErrorMessage = computed(() =>
  getSsoErrorMessage((route.query.sso_error as string) || null)
)

async function handleLogin() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await usersApi.login(form.username.trim(), form.password)
    userStore.setUser(data)
    router.push('/dashboard')
  } catch (err: any) {
    const msg = err.response?.data?.error || '用户名或密码错误'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function handleSsoLogin() {
  window.location.href = buildSsoLoginUrl('/dashboard')
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(30, 124, 242, 0.18), transparent 34%),
    radial-gradient(circle at bottom right, rgba(15, 157, 115, 0.12), transparent 24%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.66), transparent 38%),
    var(--bg-root);
}

:global(html.dark) .login-page {
  background:
    radial-gradient(circle at top left, rgba(74, 158, 255, 0.24), transparent 32%),
    radial-gradient(circle at bottom right, rgba(0, 212, 170, 0.12), transparent 24%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.03), transparent 36%),
    var(--bg-root);
}

.login-page::before,
.login-page::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  filter: blur(24px);
  pointer-events: none;
}

.login-page::before {
  width: 280px;
  height: 280px;
  top: 9%;
  right: 11%;
  background: rgba(30, 124, 242, 0.16);
}

.login-page::after {
  width: 220px;
  height: 220px;
  bottom: 8%;
  left: 10%;
  background: rgba(15, 157, 115, 0.12);
}

.theme-switcher {
  position: absolute;
  top: 28px;
  right: 28px;
  z-index: 3;
}

.login-shell {
  position: relative;
  z-index: 2;
  width: min(1180px, 100%);
  min-height: 720px;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  border-radius: 32px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  background: rgba(255, 255, 255, 0.28);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(18px);
}

:global(html.dark) .login-shell {
  background: rgba(13, 17, 24, 0.5);
}

.login-hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 28px;
  padding: 56px 52px;
  background:
    linear-gradient(145deg, rgba(17, 31, 49, 0.86), rgba(11, 18, 28, 0.78)),
    radial-gradient(circle at 20% 18%, rgba(74, 158, 255, 0.26), transparent 32%);
  color: #f4f7fb;
}

.hero-kicker {
  font-size: 0.76rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(233, 240, 248, 0.66);
  margin-bottom: 16px;
}

.hero-title {
  max-width: 7ch;
  font-family: var(--font-display);
  font-size: clamp(2.8rem, 5vw, 4.9rem);
  line-height: 0.96;
  letter-spacing: 0.01em;
}

.hero-description {
  max-width: 34rem;
  margin-top: 20px;
  font-size: 1rem;
  line-height: 1.85;
  color: rgba(233, 240, 248, 0.74);
}

.hero-metrics {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.metric-item {
  min-width: 150px;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(10px);
}

.metric-label {
  display: block;
  font-size: 0.72rem;
  color: rgba(233, 240, 248, 0.54);
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.metric-value {
  display: block;
  margin-top: 8px;
  font-size: 1.05rem;
  font-family: var(--font-display);
  color: #fff;
}

.hero-panel {
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(255, 255, 255, 0.04);
}

.signal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.signal-card {
  padding: 18px;
  border-radius: 18px;
  background: rgba(6, 12, 20, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.signal-card__title {
  display: block;
  font-size: 0.82rem;
  color: rgba(233, 240, 248, 0.62);
}

.signal-card__value {
  display: block;
  margin-top: 8px;
  font-size: 1.08rem;
  color: #fff;
}

.login-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 52px 42px;
  background: rgba(255, 255, 255, 0.76);
}

:global(html.dark) .login-card {
  background: rgba(17, 24, 34, 0.82);
}

.login-card__header {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: white;
  background: linear-gradient(140deg, var(--color-accent), #15b28f);
  box-shadow: 0 14px 34px rgba(30, 124, 242, 0.24);
}

.brand-title {
  font-family: var(--font-display);
  font-size: 1.05rem;
  color: var(--text-primary);
}

.brand-sub {
  margin-top: 4px;
  color: var(--text-muted);
}

.login-heading {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
}

.login-subtitle {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.login-alert {
  margin-top: 24px;
}

.login-form {
  margin-top: 26px;
}

.login-submit {
  width: 100%;
  height: 48px;
  margin-top: 8px;
  border: none;
  background: linear-gradient(135deg, var(--color-accent), #2aa88e) !important;
  box-shadow: 0 18px 30px rgba(30, 124, 242, 0.22);
}

.sso-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 28px 0 18px;
}

.sso-divider-line {
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}

.sso-divider-text {
  font-size: 0.78rem;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.sso-btn {
  width: 100%;
  height: 50px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-primary) !important;
  border-color: var(--border-default) !important;
  background: var(--bg-elevated) !important;
}

.sso-btn:hover {
  border-color: var(--color-accent) !important;
  color: var(--color-accent) !important;
}

.login-footer {
  display: grid;
  gap: 6px;
  margin-top: 18px;
  font-size: 0.82rem;
  color: var(--text-muted);
}

@media (max-width: 980px) {
  .login-page {
    display: block;
    overflow-y: auto;
    padding: 88px 18px 18px;
  }

  .login-shell {
    width: 100%;
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .login-hero {
    order: 2;
    padding: 28px 28px 24px;
  }

  .hero-title {
    max-width: none;
    font-size: clamp(2.4rem, 11vw, 4rem);
  }

  .login-card {
    order: 1;
    padding: 36px 28px 32px;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 84px 12px 12px;
  }

  .theme-switcher {
    position: fixed;
    top: 12px;
    right: 12px;
  }

  .login-shell {
    border-radius: 24px;
    background: var(--bg-card);
  }

  .login-hero {
    padding: 20px 18px 18px;
    gap: 18px;
  }

  .signal-grid {
    grid-template-columns: 1fr;
  }

  .login-card {
    padding: 22px 18px 20px;
  }

  .hero-kicker {
    margin-bottom: 10px;
  }

  .hero-title {
    font-size: 2rem;
  }

  .hero-description {
    margin-top: 14px;
    font-size: 0.92rem;
    line-height: 1.7;
  }

  .hero-metrics {
    gap: 10px;
  }

  .metric-item {
    min-width: calc(50% - 5px);
    padding: 12px;
  }

  .hero-panel {
    padding: 12px;
  }

  .login-heading {
    font-size: 1.7rem;
  }

  .login-subtitle {
    margin-top: 8px;
    line-height: 1.7;
  }

  .login-form {
    margin-top: 20px;
  }

  .sso-divider {
    margin: 22px 0 14px;
  }

  .login-footer {
    margin-top: 14px;
  }
}
</style>
