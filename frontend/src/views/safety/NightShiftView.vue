<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夜班监护检查</h2>
        <p class="page-subtitle">夜班监督人员巡检与排班</p>
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

    <!-- 排班表 -->
    <div class="section">
      <div class="section-header">
        <h3 class="section-title">排班计划</h3>
      </div>

      <!-- 近期待执行 -->
      <div v-if="nsOverview && nsOverview.upcoming.length" class="schedule-block">
        <h4 class="schedule-subtitle">即将到来</h4>
        <div v-for="d in nsOverview.upcoming" :key="d.id" class="schedule-row pending">
          <span class="schedule-date">{{ d.duty_date }}</span>
          <span class="schedule-name">{{ d.inspector_display.display_name }}</span>
          <el-tag type="info" size="small">待检查</el-tag>
        </div>
      </div>

      <!-- 最近完成 -->
      <div v-if="nsOverview && nsOverview.recent_completed.length" class="schedule-block">
        <h4 class="schedule-subtitle">最近完成</h4>
        <div v-for="d in nsOverview.recent_completed" :key="d.id" class="schedule-row completed">
          <span class="schedule-date">{{ d.duty_date }}</span>
          <span class="schedule-name">{{ d.inspector_display.display_name }}</span>
          <el-tag :type="d.has_issues ? 'warning' : 'success'" size="small">{{ d.has_issues ? '有问题' : '正常' }}</el-tag>
          <router-link v-if="d.record_id" :to="`/safety/nightshift/records/${d.record_id}`" class="link-btn">详情</router-link>
        </div>
      </div>

      <div v-if="nsOverview && !nsOverview.upcoming.length && !nsOverview.recent_completed.length" class="empty-hint">
        暂无排班记录。<span v-if="userStore.isSafetyOfficer">请前往 <router-link to="/safety/nightshift/admin">管理配置</router-link> 创建排班。</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftOverview, TodayStatus } from '@/api/nightshift'

const userStore = useUserStore()
const loading = ref(true)
const todayStatus = ref<TodayStatus | null>(null)
const nsOverview = ref<NightShiftOverview | null>(null)

const todayCardClass = computed(() => {
  if (!todayStatus.value?.has_duty_today) return 'no-duty'
  if (todayStatus.value.duty?.status === 'completed') return 'completed'
  return 'pending'
})

onMounted(async () => {
  try {
    const [statusRes, overviewRes] = await Promise.all([
      nightshiftApi.getTodayStatus(),
      nightshiftApi.getOverview(),
    ])
    todayStatus.value = statusRes.data
    nsOverview.value = overviewRes.data
  } finally { loading.value = false }
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

.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.summary-card { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; text-align: center; }
.summary-card.warn { border-color: var(--color-warning); }
.summary-value { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.summary-card.warn .summary-value { color: var(--color-warning); }
.summary-label { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }

.schedule-block { margin-bottom: 16px; }
.schedule-subtitle { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }
.schedule-row {
  display: flex; align-items: center; gap: 12px; padding: 10px 14px;
  background: var(--bg-card); border-radius: var(--radius-md); margin-bottom: 6px;
  border-left: 3px solid var(--border-default); font-size: 0.85rem;
}
.schedule-row.completed { border-left-color: var(--color-healthy); }
.schedule-row.pending { border-left-color: var(--color-accent); }
.schedule-date { font-weight: 600; color: var(--text-primary); min-width: 90px; font-family: var(--font-mono); }
.schedule-name { flex: 1; color: var(--text-secondary); }
.link-btn { color: var(--color-accent); text-decoration: none; font-size: 0.8rem; margin-left: 8px; }
.link-btn:hover { text-decoration: underline; }

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

@media (max-width: 640px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .today-card { flex-wrap: wrap; }
}
</style>
