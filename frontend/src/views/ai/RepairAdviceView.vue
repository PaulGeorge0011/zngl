<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">AI 维修建议</h2>
        <p class="page-subtitle">基于知识库与 AI 分析的智能维修方案</p>
      </div>
      <el-button @click="$router.back()">返回</el-button>
    </div>

    <!-- Alarm Info Card -->
    <div class="alarm-info-card" v-if="alarmInfo">
      <div class="alarm-header-row">
        <div class="alarm-level-badge" :class="alarmInfo.level">
          {{ alarmInfo.level === 'alarm' ? '报警' : '预警' }}
        </div>
        <span class="alarm-time">{{ formatTime(alarmInfo.triggered_at) }}</span>
      </div>
      <div class="alarm-details-grid">
        <div class="detail-item">
          <span class="detail-label">设备</span>
          <span class="detail-value">{{ alarmInfo.equipment_name }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">监控点</span>
          <span class="detail-value">{{ alarmInfo.point_name }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">触发值</span>
          <span class="detail-value data-value status-fault">
            {{ alarmInfo.triggered_value }} {{ alarmInfo.unit }}
          </span>
        </div>
        <div class="detail-item">
          <span class="detail-label">阈值</span>
          <span class="detail-value data-value">
            {{ alarmInfo.threshold_value }} {{ alarmInfo.unit }}
          </span>
        </div>
      </div>
    </div>

    <!-- AI Response -->
    <div class="ai-response-card">
      <div class="ai-card-header">
        <div class="ai-icon">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="10" cy="10" r="8"/>
            <path d="M7 8.5c0-1.1.9-2 2-2h2c1.1 0 2 .9 2 2 0 1.3-1 1.8-2 2.2v1"/>
            <circle cx="10" cy="14.5" r="0.5" fill="currentColor"/>
          </svg>
        </div>
        <span class="ai-title">AI 维修建议</span>
        <div v-if="isStreaming" class="streaming-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>

      <div class="ai-content">
        <div v-if="responseText" class="response-text" v-html="renderMarkdown(responseText)"></div>
        <div v-else-if="error" class="error-text">{{ error }}</div>
        <div v-else-if="!isStreaming" class="generating-prompt">
          <el-button type="primary" :loading="isGenerating" @click="generateAdvice">
            生成维修建议
          </el-button>
        </div>
      </div>

      <div v-if="isStreaming" class="cursor-blink"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { aiApi } from '@/api/ai'
import { monitoringApi } from '@/api/monitoring'
import type { AlarmRecord } from '@/types'

const route = useRoute()
const alarmId = Number(route.params.alarmId)

const alarmInfo = ref<AlarmRecord | null>(null)
const responseText = ref('')
const isStreaming = ref(false)
const isGenerating = ref(false)
const error = ref('')

function formatTime(t: string) {
  if (!t) return '--'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

function renderMarkdown(text: string): string {
  // Simple markdown rendering
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^(\d+\.\s)/gm, '<span class="list-num">$1</span>')
}

async function loadAlarmInfo() {
  try {
    const { data } = await monitoringApi.alarms({ page: 1 })
    alarmInfo.value = data.results.find((a: AlarmRecord) => a.id === alarmId) || null
  } catch { /* skip */ }
}

async function generateAdvice() {
  isGenerating.value = true
  isStreaming.value = true
  error.value = ''
  responseText.value = ''

  await aiApi.streamRepairAdvice(
    alarmId,
    (chunk) => {
      responseText.value += chunk
    },
    () => {
      isStreaming.value = false
      isGenerating.value = false
    },
    (err) => {
      error.value = err
      isStreaming.value = false
      isGenerating.value = false
    }
  )
}

// Try loading existing advice first
async function tryLoadExisting() {
  try {
    const { data } = await aiApi.getRepairAdvice(alarmId)
    responseText.value = data.ai_response
  } catch {
    // No existing advice
  }
}

onMounted(async () => {
  await loadAlarmInfo()
  await tryLoadExisting()
})
</script>

<style scoped>
.alarm-info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 20px;
}

.alarm-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.alarm-level-badge {
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.alarm-level-badge.alarm {
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
  border: 1px solid rgba(230, 57, 70, 0.3);
}

.alarm-level-badge.warning {
  background: var(--color-warning-dim);
  color: var(--color-warning);
  border: 1px solid rgba(240, 165, 0, 0.3);
}

.alarm-time {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-muted);
}

.alarm-details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.detail-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.detail-value {
  font-size: 0.95rem;
  color: var(--text-primary);
}

/* AI Response Card */
.ai-response-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.ai-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
}

.ai-icon {
  color: var(--color-accent);
}

.ai-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.streaming-indicator {
  display: flex;
  gap: 3px;
  margin-left: 8px;
}

.streaming-indicator .dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dot-pulse 1.4s ease-in-out infinite;
}

.streaming-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.streaming-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1.2); }
}

.ai-content {
  padding: 24px;
  min-height: 200px;
}

.response-text {
  font-size: 0.95rem;
  line-height: 1.8;
  color: var(--text-primary);
}

.response-text :deep(strong) {
  color: var(--color-accent);
  font-weight: 600;
}

.response-text :deep(.list-num) {
  font-family: var(--font-mono);
  color: var(--color-accent);
  font-weight: 600;
}

.error-text {
  color: var(--color-alarm);
  padding: 20px 0;
}

.generating-prompt {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

.cursor-blink {
  width: 8px;
  height: 2px;
  background: var(--color-accent);
  margin: 0 24px 24px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
