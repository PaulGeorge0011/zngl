<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">报警历史</h2>
        <p class="page-subtitle">设备预警与报警记录</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-select v-model="filters.status" placeholder="全部状态" clearable @change="fetchAlarms">
        <el-option label="未处理" value="active" />
        <el-option label="已确认" value="acknowledged" />
        <el-option label="已解决" value="resolved" />
      </el-select>
      <el-select v-model="filters.level" placeholder="全部级别" clearable @change="fetchAlarms">
        <el-option label="预警" value="warning" />
        <el-option label="报警" value="alarm" />
      </el-select>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <el-table :data="alarms" v-loading="loading" stripe>
        <el-table-column label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.level === 'alarm' ? 'danger' : 'warning'"
              effect="dark"
              size="small"
              round
            >
              {{ row.level === 'alarm' ? '报警' : '预警' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="equipment_name" label="设备" min-width="120" />
        <el-table-column prop="point_name" label="监控点" min-width="110" />
        <el-table-column label="触发值" width="120">
          <template #default="{ row }">
            <span class="data-value" :class="row.level === 'alarm' ? 'status-fault' : 'status-running'">
              {{ row.triggered_value }}
            </span>
            <span class="unit-text">{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="阈值" width="100">
          <template #default="{ row }">
            <span class="data-value">{{ row.threshold_value }}</span>
            <span class="unit-text">{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="alarmStatusType(row.status)" size="small" effect="plain">
              {{ alarmStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="triggered_at" label="触发时间" width="165">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.triggered_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              link type="primary"
              @click="acknowledgeAlarm(row)"
            >确认</el-button>
            <el-button
              v-if="row.status !== 'resolved'"
              link type="success"
              @click="resolveAlarm(row)"
            >解决</el-button>
            <el-button
              link type="primary"
              @click="$router.push(`/ai/repair/${row.id}`)"
            >维修建议</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchAlarms"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { monitoringApi } from '@/api/monitoring'
import { useAlarmStore } from '@/stores/alarm'
import type { AlarmRecord } from '@/types'
import { ElMessage } from 'element-plus'

const alarmStore = useAlarmStore()
const alarms = ref<AlarmRecord[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const filters = ref({ status: '', level: '' })

function alarmStatusType(s: string) {
  return { active: 'danger', acknowledged: 'warning', resolved: 'success' }[s] || 'info'
}

function alarmStatusLabel(s: string) {
  return { active: '未处理', acknowledged: '已确认', resolved: '已解决' }[s] || s
}

function formatTime(t: string) {
  if (!t) return '--'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

async function fetchAlarms() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.level) params.level = filters.value.level
    const { data } = await monitoringApi.alarms(params)
    alarms.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
  alarmStore.clearUnread()
}

async function acknowledgeAlarm(row: AlarmRecord) {
  try {
    await monitoringApi.acknowledgeAlarm(row.id)
    ElMessage.success('已确认')
    fetchAlarms()
  } catch { /* handled by interceptor */ }
}

async function resolveAlarm(row: AlarmRecord) {
  try {
    await monitoringApi.resolveAlarm(row.id)
    ElMessage.success('已解决')
    fetchAlarms()
  } catch { /* handled by interceptor */ }
}

onMounted(fetchAlarms)
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.table-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid var(--border-subtle);
}

.unit-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-left: 2px;
}

.time-text {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-secondary);
}
</style>
