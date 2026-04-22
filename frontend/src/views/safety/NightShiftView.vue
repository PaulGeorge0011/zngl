<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夜班监护检查</h2>
        <p class="page-subtitle">夜班监督人员巡检与公开透明排班</p>
      </div>
      <div class="header-actions">
        <router-link to="/safety/nightshift/records" class="action-btn">检查记录</router-link>
        <router-link v-if="userStore.isSafetyOfficer" to="/safety/nightshift/admin" class="action-btn primary">管理配置</router-link>
      </div>
    </div>

    <!-- 今日排班状态 -->
    <div v-if="todayStatus" class="today-card" :class="todayCardClass">
      <div class="today-icon">
        <template v-if="!todayStatus.has_duty_today">—</template>
        <template v-else-if="todayStatus.duty?.status === 'completed'">✓</template>
        <template v-else>○</template>
      </div>
      <div class="today-body">
        <template v-if="!todayStatus.has_duty_today">
          <div class="today-title">今日无夜班检查安排</div>
        </template>
        <template v-else-if="todayStatus.duty?.status === 'completed'">
          <div class="today-title">今日夜班检查已完成</div>
          <div class="today-desc">检查人：{{ todayStatus.duty.inspector_display.display_name }}</div>
        </template>
        <template v-else>
          <div class="today-title">今日夜班检查待执行</div>
          <div class="today-desc">检查人：{{ todayStatus.duty?.inspector_display.display_name }}</div>
        </template>
      </div>
      <div class="today-action">
        <router-link
          v-if="todayStatus.is_my_duty && todayStatus.duty?.status === 'pending'"
          :to="`/safety/nightshift/inspect?duty=${todayStatus.duty.id}`"
          class="inspect-btn"
        >开始检查</router-link>
        <router-link
          v-else-if="todayStatus.duty?.record_id"
          :to="`/safety/nightshift/records/${todayStatus.duty.record_id}`"
          class="view-btn"
        >查看详情</router-link>
      </div>
    </div>

    <!-- 排班日历 -->
    <div class="section">
      <div class="section-header">
        <h3 class="section-title">排班日历</h3>
        <div class="month-nav">
          <el-button size="small" @click="changeMonth(-1)">←</el-button>
          <span class="month-label">{{ calendarMonth }}</span>
          <el-button size="small" @click="changeMonth(1)">→</el-button>
          <el-button size="small" @click="gotoToday">今天</el-button>
        </div>
      </div>
      <p class="calendar-hint">
        <span v-if="userStore.isSafetyOfficer">点击日期可分配/更换值班人员。</span>
        <span v-else>所有人均可查看排班安排，公开透明。</span>
      </p>
      <div class="calendar-wrapper">
        <el-calendar v-model="calendarDate" ref="calendarRef">
          <template #date-cell="{ data }">
            <div
              class="cell"
              :class="cellClass(data.day)"
              @click="onCellClick(data.day)"
            >
              <div class="cell-day">{{ formatDay(data.day) }}</div>
              <div v-if="dutyByDate[data.day]" class="cell-duty">
                <div class="cell-name">{{ dutyByDate[data.day].inspector_display.display_name }}</div>
                <el-tag
                  :type="dutyByDate[data.day].status === 'completed'
                    ? (dutyByDate[data.day].has_issues ? 'warning' : 'success')
                    : 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ dutyByDate[data.day].status === 'completed'
                    ? (dutyByDate[data.day].has_issues ? '有问题' : '已完成')
                    : '待检查' }}
                </el-tag>
              </div>
              <div v-else-if="userStore.isSafetyOfficer && data.type === 'current-month'" class="cell-empty">
                + 排班
              </div>
            </div>
          </template>
        </el-calendar>
      </div>
    </div>

    <!-- 监护次数统计 -->
    <div class="section">
      <div class="section-header">
        <h3 class="section-title">监护次数统计</h3>
        <el-radio-group v-model="statsScope" size="small" @change="loadStats">
          <el-radio-button value="month">本月</el-radio-button>
          <el-radio-button value="all">累计</el-radio-button>
        </el-radio-group>
      </div>
      <div v-if="statsLoading" class="loading-hint">统计加载中...</div>
      <el-table v-else-if="statsRows.length" :data="statsRows" stripe size="small">
        <el-table-column label="排名" width="70">
          <template #default="{ $index }">
            <span class="rank" :class="rankClass($index)">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="监护人员">
          <template #default="{ row }">
            <strong>{{ row.display_name }}</strong>
            <span class="stat-username">{{ row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column label="排班总数" width="100" align="center" prop="total" />
        <el-table-column label="已完成" width="100" align="center">
          <template #default="{ row }">
            <span class="stat-ok">{{ row.completed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="待执行" width="100" align="center">
          <template #default="{ row }">
            <span :class="row.pending > 0 ? 'stat-pending' : ''">{{ row.pending }}</span>
          </template>
        </el-table-column>
        <el-table-column label="发现问题次数" width="120" align="center">
          <template #default="{ row }">
            <span :class="row.with_issues > 0 ? 'stat-warn' : ''">{{ row.with_issues }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-hint">暂无监护次数统计数据</div>
    </div>

    <!-- 今日检查摘要 -->
    <div v-if="nsOverview?.today_duty?.status === 'completed' && nsOverview.check_stats.total > 0" class="section">
      <h3 class="section-title">今日检查摘要</h3>
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-value">{{ nsOverview.check_stats.total }}</div>
          <div class="summary-label">检查项</div>
        </div>
        <div class="summary-card" :class="{ warn: nsOverview.check_stats.abnormal > 0 }">
          <div class="summary-value">{{ nsOverview.check_stats.abnormal }}</div>
          <div class="summary-label">异常项</div>
        </div>
        <div class="summary-card" :class="{ warn: nsOverview.issue_stats.total > 0 }">
          <div class="summary-value">{{ nsOverview.issue_stats.total }}</div>
          <div class="summary-label">发现问题</div>
        </div>
        <div class="summary-card" :class="{ warn: nsOverview.issue_stats.unresolved > 0 }">
          <div class="summary-value">{{ nsOverview.issue_stats.unresolved }}</div>
          <div class="summary-label">未整改</div>
        </div>
      </div>
    </div>

    <!-- 问题列表 -->
    <div v-if="nsOverview?.recent_issues?.length" class="section">
      <h3 class="section-title" :class="{ 'warning-text': nsOverview.issue_stats.unresolved > 0 }">今日发现问题</h3>
      <div v-for="(issue, i) in nsOverview.recent_issues" :key="i" class="issue-row" :class="{ resolved: issue.is_resolved }">
        <span class="issue-status">{{ issue.is_resolved ? '✓' : '✗' }}</span>
        <span class="issue-desc">{{ issue.description }}</span>
        <span v-if="issue.rectification" class="issue-rect">{{ issue.rectification }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading-hint">加载中...</div>

    <!-- 排班分配对话框（仅安全员） -->
    <el-dialog v-model="dutyDialogVisible" :title="`${dutyDialogDate} 排班`" width="420px">
      <div v-if="dutyDialogCurrent" class="dialog-current">
        当前值班人员：<strong>{{ dutyDialogCurrent.inspector_display.display_name }}</strong>
        <el-tag
          :type="dutyDialogCurrent.status === 'completed' ? 'success' : 'info'"
          size="small"
          style="margin-left: 8px"
        >{{ dutyDialogCurrent.status_display }}</el-tag>
      </div>
      <el-form :model="dutyForm" label-width="80px">
        <el-form-item label="监护人员">
          <el-select v-model="dutyForm.inspector" filterable placeholder="从排班人员表选择">
            <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name" :value="u.id">
              <span>{{ u.display_name }}</span>
              <span style="color: var(--text-muted); margin-left: 8px; font-size: 0.8em">{{ u.username }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          v-if="dutyDialogCurrent && dutyDialogCurrent.status === 'pending'"
          type="danger"
          plain
          @click="removeDuty"
        >移除排班</el-button>
        <el-button @click="dutyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDutyFromCalendar">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { nightshiftApi } from '@/api/nightshift'
import type {
  NightShiftOverview, TodayStatus,
  NightShiftDuty, InspectorStatRow,
} from '@/api/nightshift'
import http from '@/api/http'

const userStore = useUserStore()
const loading = ref(true)
const todayStatus = ref<TodayStatus | null>(null)
const nsOverview = ref<NightShiftOverview | null>(null)

const todayCardClass = computed(() => {
  if (!todayStatus.value?.has_duty_today) return 'no-duty'
  if (todayStatus.value.duty?.status === 'completed') return 'completed'
  return 'pending'
})

// ── 排班日历 ────────────────────────────────────────────────────────────
const calendarDate = ref(new Date())
const duties = ref<NightShiftDuty[]>([])

const calendarMonth = computed(() => {
  const d = calendarDate.value
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
})

const dutyByDate = computed<Record<string, NightShiftDuty>>(() => {
  const map: Record<string, NightShiftDuty> = {}
  for (const d of duties.value) map[d.duty_date] = d
  return map
})

function formatDay(day: string): string {
  const parts = day.split('-')
  return parts[2] || day
}

function cellClass(day: string): string {
  const duty = dutyByDate.value[day]
  const today = new Date().toISOString().slice(0, 10)
  const classes: string[] = []
  if (day === today) classes.push('is-today')
  if (!duty) return classes.join(' ')
  if (duty.status === 'completed') {
    classes.push(duty.has_issues ? 'has-issues' : 'completed')
  } else {
    classes.push('pending')
  }
  return classes.join(' ')
}

async function loadDuties() {
  const { data } = await nightshiftApi.getDuties({ month: calendarMonth.value })
  duties.value = data
}

function changeMonth(delta: number) {
  const d = new Date(calendarDate.value)
  d.setMonth(d.getMonth() + delta)
  d.setDate(1)
  calendarDate.value = d
}

function gotoToday() {
  calendarDate.value = new Date()
}

watch(calendarMonth, () => {
  loadDuties()
  if (statsScope.value === 'month') loadStats()
})

// ── 排班对话框 ──────────────────────────────────────────────────────────
const dutyDialogVisible = ref(false)
const dutyDialogDate = ref('')
const dutyDialogCurrent = ref<NightShiftDuty | null>(null)
const dutyForm = ref<{ inspector: number | null }>({ inspector: null })
const saving = ref(false)
const allUsers = ref<{ id: number; username: string; display_name: string }[]>([])

async function loadAllUsers() {
  if (allUsers.value.length) return
  const { data } = await http.get('/api/users/list/')
  allUsers.value = data
}

function onCellClick(day: string) {
  if (!userStore.isSafetyOfficer) return
  const current = dutyByDate.value[day] || null
  if (current && current.status === 'completed') {
    ElMessage.info('该日期已完成检查，不可再修改排班')
    return
  }
  dutyDialogDate.value = day
  dutyDialogCurrent.value = current
  dutyForm.value = { inspector: current?.inspector ?? null }
  dutyDialogVisible.value = true
  loadAllUsers()
}

async function saveDutyFromCalendar() {
  if (!dutyForm.value.inspector) {
    ElMessage.warning('请选择监护人员')
    return
  }
  saving.value = true
  try {
    if (dutyDialogCurrent.value) {
      await nightshiftApi.updateDuty(dutyDialogCurrent.value.id, {
        duty_date: dutyDialogDate.value,
        inspector: dutyForm.value.inspector,
      })
    } else {
      await nightshiftApi.createDuty({
        dates: [dutyDialogDate.value],
        inspector: dutyForm.value.inspector,
      })
    }
    dutyDialogVisible.value = false
    ElMessage.success('排班保存成功')
    await Promise.all([loadDuties(), loadStats(), refreshOverview()])
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function removeDuty() {
  if (!dutyDialogCurrent.value) return
  try {
    await ElMessageBox.confirm(`确认移除 ${dutyDialogDate.value} 的排班？`, '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  saving.value = true
  try {
    await nightshiftApi.deleteDuty(dutyDialogCurrent.value.id)
    dutyDialogVisible.value = false
    ElMessage.success('已移除')
    await Promise.all([loadDuties(), loadStats(), refreshOverview()])
  } finally {
    saving.value = false
  }
}

// ── 监护次数统计 ────────────────────────────────────────────────────────
const statsScope = ref<'month' | 'all'>('month')
const statsRows = ref<InspectorStatRow[]>([])
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    const month = statsScope.value === 'month' ? calendarMonth.value : undefined
    const { data } = await nightshiftApi.getInspectorStats(month)
    statsRows.value = data.results
  } finally {
    statsLoading.value = false
  }
}

function rankClass(index: number): string {
  if (index === 0) return 'rank-1'
  if (index === 1) return 'rank-2'
  if (index === 2) return 'rank-3'
  return ''
}

// ── 概览刷新 ────────────────────────────────────────────────────────────
async function refreshOverview() {
  const [statusRes, overviewRes] = await Promise.all([
    nightshiftApi.getTodayStatus(),
    nightshiftApi.getOverview(),
  ])
  todayStatus.value = statusRes.data
  nsOverview.value = overviewRes.data
}

onMounted(async () => {
  try {
    await Promise.all([
      refreshOverview(),
      loadDuties(),
      loadStats(),
    ])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.header-actions { display: flex; gap: 8px; }
.action-btn { padding: 7px 16px; border-radius: var(--radius-md); border: 1px solid var(--border-default); color: var(--text-secondary); text-decoration: none; font-size: 0.85rem; }
.action-btn:hover { background: var(--bg-card); }
.action-btn.primary { background: var(--color-accent); color: #fff; border-color: var(--color-accent); }

.today-card {
  display: flex; align-items: center; gap: 16px; padding: 20px;
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); margin-top: 16px;
}
.today-card.completed { border-color: var(--color-healthy); }
.today-card.pending { border-color: var(--color-warning); }
.today-card.no-duty { border-color: var(--border-default); }
.today-icon { font-size: 1.5rem; width: 40px; text-align: center; }
.today-card.completed .today-icon { color: var(--color-healthy); }
.today-card.pending .today-icon { color: var(--color-warning); }
.today-card.no-duty .today-icon { color: var(--text-muted); }
.today-body { flex: 1; }
.today-title { font-weight: 600; color: var(--text-primary); }
.today-desc { font-size: 0.85rem; color: var(--text-muted); margin-top: 2px; }
.inspect-btn, .view-btn { display: inline-block; padding: 8px 20px; border-radius: var(--radius-md); font-size: 0.85rem; text-decoration: none; }
.inspect-btn { background: var(--color-accent); color: #fff; }
.inspect-btn:hover { opacity: 0.9; }
.view-btn { border: 1px solid var(--border-default); color: var(--text-secondary); }
.view-btn:hover { background: var(--bg-card); }

.section { margin-top: 24px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); }
.warning-text { color: var(--color-warning); }

.month-nav { display: flex; align-items: center; gap: 8px; }
.month-label { font-weight: 600; font-size: 0.95rem; color: var(--text-primary); min-width: 90px; text-align: center; font-family: var(--font-mono); }

.calendar-hint { font-size: 0.8rem; color: var(--text-muted); margin: 0 0 8px; }
.calendar-wrapper :deep(.el-calendar__header) { display: none; }
.calendar-wrapper :deep(.el-calendar-day) { padding: 0; min-height: 82px; }
.cell {
  height: 100%; min-height: 82px; padding: 6px 8px; cursor: pointer;
  display: flex; flex-direction: column; gap: 4px; border-radius: 4px;
  transition: background 0.15s;
}
.cell:hover { background: var(--bg-card); }
.cell-day { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); font-family: var(--font-mono); }
.cell.is-today .cell-day { color: var(--color-accent); }
.cell.is-today { outline: 2px solid var(--color-accent); outline-offset: -2px; }
.cell.completed { background: rgba(82, 196, 26, 0.08); }
.cell.has-issues { background: rgba(250, 173, 20, 0.1); }
.cell.pending { background: rgba(24, 144, 255, 0.06); }
.cell-duty { display: flex; flex-direction: column; gap: 3px; }
.cell-name { font-size: 0.82rem; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cell-empty { font-size: 0.75rem; color: var(--text-muted); opacity: 0; transition: opacity 0.15s; }
.cell:hover .cell-empty { opacity: 1; }

.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.summary-card { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; text-align: center; }
.summary-card.warn { border-color: var(--color-warning); }
.summary-value { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.summary-card.warn .summary-value { color: var(--color-warning); }
.summary-label { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }

.rank {
  display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center;
  border-radius: 50%; font-size: 0.8rem; font-weight: 600; color: var(--text-muted);
  background: var(--bg-card);
}
.rank.rank-1 { background: #ffd700; color: #5a4300; }
.rank.rank-2 { background: #c0c0c0; color: #333; }
.rank.rank-3 { background: #cd7f32; color: #fff; }
.stat-username { font-size: 0.78rem; color: var(--text-muted); margin-left: 8px; }
.stat-ok { color: var(--color-healthy); font-weight: 600; }
.stat-pending { color: var(--color-accent); font-weight: 600; }
.stat-warn { color: var(--color-warning); font-weight: 600; }

.issue-row {
  display: flex; gap: 10px; align-items: flex-start; padding: 10px 14px;
  background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: 6px;
  border-left: 3px solid var(--color-warning); font-size: 0.85rem;
}
.issue-row.resolved { border-left-color: var(--color-healthy); }
.issue-status { flex-shrink: 0; font-weight: 700; }
.issue-row.resolved .issue-status { color: var(--color-healthy); }
.issue-row:not(.resolved) .issue-status { color: var(--color-warning); }
.issue-desc { flex: 1; color: var(--text-primary); }
.issue-rect { color: var(--text-muted); font-size: 0.8rem; }

.empty-hint { text-align: center; padding: 24px 0; color: var(--text-muted); font-size: 0.85rem; }
.empty-hint a { color: var(--color-accent); }
.loading-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }

.dialog-current { padding: 10px 14px; background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: 16px; font-size: 0.88rem; }

@media (max-width: 640px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .today-card { flex-wrap: wrap; }
  .calendar-wrapper :deep(.el-calendar-day) { min-height: 60px; }
  .cell { min-height: 60px; }
}
</style>
