<template>
  <div class="mobile-page">
    <!-- 成功状态 -->
    <div v-if="success" class="success-card">
      <div class="success-icon">✓</div>
      <h2>签到成功</h2>
      <p class="success-name">{{ successData.name }}</p>
      <p class="success-time">入场时间：{{ successData.check_in_at }}</p>
      <button class="btn-secondary" @click="resetForm">继续签到</button>
    </div>

    <!-- 表单状态 -->
    <template v-else>
      <div class="page-header">
        <div class="header-icon">🏗</div>
        <h1>夹层施工入场登记</h1>
        <p>请填写以下信息完成入场登记</p>
      </div>

      <div class="form-card">
        <div class="form-item" :class="{ error: errors.name }">
          <label>姓名 <span class="required">*</span></label>
          <input v-model="form.name" type="text" placeholder="请输入姓名" maxlength="50" />
          <span class="error-msg" v-if="errors.name">{{ errors.name }}</span>
        </div>

        <div class="form-item" :class="{ error: errors.phone }">
          <label>手机号 <span class="required">*</span></label>
          <input v-model="form.phone" type="tel" placeholder="请输入手机号" maxlength="20" />
          <span class="error-msg" v-if="errors.phone">{{ errors.phone }}</span>
        </div>

        <div class="form-item">
          <label>施工单位</label>
          <input v-model="form.company" type="text" placeholder="选填" maxlength="100" />
        </div>

        <div class="form-item" :class="{ error: errors.project }">
          <label>施工项目 <span class="required">*</span></label>
          <input v-model="form.project" type="text" placeholder="请输入施工项目名称" maxlength="200" />
          <span class="error-msg" v-if="errors.project">{{ errors.project }}</span>
        </div>

        <div class="form-item">
          <label>人数</label>
          <div class="count-row">
            <button type="button" class="count-btn" @click="form.count = Math.max(1, form.count - 1)">−</button>
            <input v-model.number="form.count" type="number" min="1" max="99" class="count-input" />
            <button type="button" class="count-btn" @click="form.count = Math.min(99, form.count + 1)">+</button>
          </div>
          <p class="count-hint">如多人同行，可由一人统一填写登记</p>
        </div>

        <button class="btn-primary" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '提交中...' : '确认签到' }}
        </button>

        <p v-if="submitError" class="submit-error">{{ submitError }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { mezzanineApi } from '@/api/mezzanine'

const form = reactive({ name: '', phone: '', company: '', project: '', count: 1 })
const errors = reactive({ name: '', phone: '', project: '' })
const submitting = ref(false)
const submitError = ref('')
const success = ref(false)
const successData = reactive({ name: '', check_in_at: '' })

function validate() {
  errors.name = form.name.trim() ? '' : '请填写姓名'
  errors.phone = form.phone.trim() ? '' : '请填写手机号'
  errors.project = form.project.trim() ? '' : '请填写施工项目'
  return !errors.name && !errors.phone && !errors.project
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  submitError.value = ''
  try {
    const { data } = await mezzanineApi.checkin({
      name: form.name.trim(),
      phone: form.phone.trim(),
      company: form.company.trim(),
      project: form.project.trim(),
      count: form.count,
    })
    successData.name = data.name
    successData.check_in_at = data.check_in_at
    success.value = true
  } catch (err: any) {
    submitError.value = err.response?.data?.error || '提交失败，请重试'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, { name: '', phone: '', company: '', project: '', count: 1 })
  Object.assign(errors, { name: '', phone: '', project: '' })
  submitError.value = ''
  success.value = false
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

.form-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item { display: flex; flex-direction: column; gap: 6px; }

.count-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-btn {
  width: 36px;
  height: 36px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.count-input {
  width: 60px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 8px;
  font-size: 1.1rem;
  text-align: center;
  color: var(--text-primary);
  outline: none;
}

.count-hint {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0;
}

.form-item label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.required { color: var(--color-alarm); }

.form-item input {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 1rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition-fast);
  width: 100%;
  box-sizing: border-box;
}

.form-item input:focus { border-color: var(--color-accent); }
.form-item.error input { border-color: var(--color-alarm); }

.error-msg { font-size: 0.8rem; color: var(--color-alarm); }

.btn-primary {
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 14px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  margin-top: 8px;
  transition: opacity var(--transition-fast);
}

.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary:active { opacity: 0.85; }

.submit-error { color: var(--color-alarm); font-size: 0.875rem; text-align: center; margin: 0; }

.success-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--color-healthy);
  border-radius: var(--radius-lg);
  padding: 40px 24px;
  text-align: center;
  margin-top: 40px;
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
  margin-bottom: 8px;
}

.success-card h2 { font-size: 1.4rem; color: var(--color-healthy); margin: 0; }
.success-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; }
.success-time { font-size: 0.875rem; color: var(--text-muted); margin: 0; }

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 10px 24px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  margin-top: 8px;
}
</style>
