<template>
  <div class="mobile-page">
    <div class="page-header">
      <div class="header-icon">🚪</div>
      <h1>夹层施工离场签退</h1>
      <p>请选择您的姓名完成离场签退</p>
    </div>

    <div v-if="loading" class="loading-state">
      <p>加载中...</p>
    </div>

    <div v-else-if="success" class="success-card">
      <div class="success-icon">✓</div>
      <h2>签退成功</h2>
      <p class="success-name">{{ successName }}</p>
      <p class="success-time">离场时间：{{ successTime }}</p>
    </div>

    <div v-else-if="onsite.length === 0" class="empty-state">
      <div class="empty-icon">🏗</div>
      <p>当前无人在夹层作业</p>
    </div>

    <template v-else>
      <div class="person-list">
        <div
          v-for="person in onsite"
          :key="person.id"
          class="person-card"
          @click="selectPerson(person)"
        >
          <div class="person-name">{{ person.name }}</div>
          <div v-if="person.count > 1" class="person-count">共 {{ person.count }} 人</div>
          <div class="person-info">{{ person.project }}</div>
          <div class="person-time">入场：{{ person.check_in_at }}</div>
        </div>
      </div>

      <div v-if="selected" class="confirm-overlay" @click.self="selected = null">
        <div class="confirm-card">
          <h3>确认签退</h3>
          <p>{{ selected.name }}，请输入手机号后四位验证身份</p>
          <input
            v-model="phoneLast4"
            type="tel"
            placeholder="手机号后四位"
            maxlength="4"
            class="phone-input"
            @keyup.enter="handleCheckout"
          />
          <p v-if="checkoutError" class="error-msg">{{ checkoutError }}</p>
          <div class="confirm-actions">
            <button class="btn-secondary" @click="selected = null">取消</button>
            <button
              class="btn-primary"
              :disabled="checkingOut || phoneLast4.length !== 4"
              @click="handleCheckout"
            >
              {{ checkingOut ? '签退中...' : '确认签退' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { mezzanineApi, type MezzanineOnsite } from '@/api/mezzanine'

const onsite = ref<MezzanineOnsite[]>([])
const loading = ref(true)
const selected = ref<MezzanineOnsite | null>(null)
const phoneLast4 = ref('')
const checkingOut = ref(false)
const checkoutError = ref('')
const success = ref(false)
const successName = ref('')
const successTime = ref('')

onMounted(async () => {
  try {
    const { data } = await mezzanineApi.onsite()
    onsite.value = data
  } catch {
    // silent
  } finally {
    loading.value = false
  }
})

function selectPerson(person: MezzanineOnsite) {
  selected.value = person
  phoneLast4.value = ''
  checkoutError.value = ''
}

async function handleCheckout() {
  if (!selected.value || phoneLast4.value.length !== 4) return
  checkingOut.value = true
  checkoutError.value = ''
  try {
    const { data } = await mezzanineApi.checkout({
      record_id: selected.value.id,
      phone_last4: phoneLast4.value,
    })
    successName.value = data.name
    successTime.value = data.check_out_at
    selected.value = null
    success.value = true
  } catch (err: any) {
    checkoutError.value = err.response?.data?.error || '签退失败，请重试'
  } finally {
    checkingOut.value = false
  }
}
</script>

<style scoped>
.mobile-page {
  min-height: 100vh;
  background: var(--bg-root);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
  padding-top: 16px;
}

.header-icon { font-size: 2.5rem; margin-bottom: 8px; }

.page-header h1 {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.page-header p { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.person-list {
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.person-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.person-card:active { background: var(--bg-elevated); border-color: var(--color-accent); }

.person-name { font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.person-count {
  font-size: 0.875rem;
  color: var(--color-warning);
  font-weight: 600;
}
.person-info { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 2px; }
.person-time { font-size: 0.8rem; color: var(--text-muted); }

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon { font-size: 3rem; margin-bottom: 12px; }

.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}

.confirm-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.confirm-card h3 { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.confirm-card p { font-size: 0.9rem; color: var(--text-secondary); margin: 0; }

.phone-input {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 1.2rem;
  text-align: center;
  letter-spacing: 0.3em;
  color: var(--text-primary);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.phone-input:focus { border-color: var(--color-accent); }

.error-msg { color: var(--color-alarm); font-size: 0.85rem; margin: 0; }

.confirm-actions { display: flex; gap: 10px; margin-top: 4px; }

.btn-primary {
  flex: 1;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  flex: 1;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 12px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
}

.success-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--color-healthy);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.success-icon {
  width: 64px;
  height: 64px;
  background: var(--color-healthy);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: #fff;
}

.success-card h2 { font-size: 1.4rem; color: var(--color-healthy); margin: 0; }
.success-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.success-time { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.loading-state { color: var(--text-muted); margin-top: 60px; }
</style>
