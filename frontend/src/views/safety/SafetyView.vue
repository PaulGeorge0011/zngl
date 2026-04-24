<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">安全管理</h2>
        <p class="page-subtitle">车间安全监控与隐患排查</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <router-link to="/safety/dustroom" class="stat-card clickable">
        <div class="stat-icon dustroom">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="6" width="18" height="12" rx="2"/><path d="M6 6V4a2 2 0 012-2h6a2 2 0 012 2v2"/><circle cx="11" cy="12" r="2.5"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value" :class="dustRoomStatusClass">
            {{ dustRoomStatusText }}
          </div>
          <div class="stat-label">除尘房巡检</div>
          <div class="stat-detail" v-if="overview">
            {{ completedRooms }}/{{ totalExpected }} 完成
          </div>
        </div>
      </router-link>

      <router-link to="/safety/dustroom" class="stat-card clickable" v-if="overview && overview.abnormal_count > 0">
        <div class="stat-icon warning">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M11 2L1 20h20L11 2z"/><path d="M11 9v4M11 16v.5"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value warning">{{ overview.abnormal_count }}</div>
          <div class="stat-label">今日异常项</div>
          <div class="stat-detail">需要关注</div>
        </div>
      </router-link>

      <router-link to="/safety/hazard" class="stat-card clickable">
        <div class="stat-icon hazard">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="9" r="5"/><path d="M4 20c0-3.9 3.1-7 7-7s7 3.1 7 7"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value">{{ hazardStats.pending }}</div>
          <div class="stat-label">待处理隐患</div>
          <div class="stat-detail">随手拍上报</div>
        </div>
      </router-link>

      <router-link to="/safety/rectification" class="stat-card clickable">
        <div class="stat-icon rectification">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 6h16M3 11h16M3 16h10"/><path d="M16 14l3 3-3 3"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value" :class="{ warning: rectStats.overdue > 0 }">{{ rectStats.pending + rectStats.fixing + rectStats.verifying }}</div>
          <div class="stat-label">整改中心</div>
          <div class="stat-detail">
            待分派 {{ rectStats.pending }} · 整改中 {{ rectStats.fixing }} · 待验证 {{ rectStats.verifying }}
            <span v-if="rectStats.overdue > 0" class="warning-text">· 逾期 {{ rectStats.overdue }}</span>
          </div>
        </div>
      </router-link>

      <router-link to="/safety/nightshift" class="stat-card clickable">
        <div class="stat-icon nightshift">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/><path d="M11 6v5l3.5 2"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value" :class="nsStatusClass">{{ nsStatusText }}</div>
          <div class="stat-label">夜班监护检查</div>
          <div class="stat-detail" v-if="nsOverview?.today_duty">
            {{ nsOverview.today_duty.inspector_display.display_name }} · {{ nsOverview.today_duty.status_display }}
          </div>
          <div class="stat-detail" v-if="nsOverview?.stats_30d">
            近30天 {{ nsOverview.stats_30d.completed }}/{{ nsOverview.stats_30d.total }}
          </div>
        </div>
      </router-link>

      <router-link to="/safety/mezzanine" class="stat-card clickable">
        <div class="stat-icon mezzanine">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="5" width="18" height="14" rx="2"/><path d="M7 5V3a1 1 0 011-1h6a1 1 0 011 1v2"/><path d="M7 11h8M7 14h5"/>
          </svg>
        </div>
        <div class="stat-body">
          <div class="stat-value data-value">{{ mezzanineStats.onsite }}</div>
          <div class="stat-label">夹层在场人数</div>
          <div class="stat-detail">今日入场 {{ mezzanineStats.today }}</div>
        </div>
      </router-link>
    </div>

    <!-- 除尘房巡检进度 -->
    <div class="section" v-if="overview && overview.completion_by_role.length">
      <div class="section-header">
        <h3 class="section-title">除尘房巡检进度</h3>
        <router-link to="/safety/dustroom" class="section-link">查看详情 →</router-link>
      </div>
      <div class="progress-grid">
        <div v-for="c in overview.completion_by_role" :key="c.role" class="progress-item">
          <div class="progress-role">{{ c.role_display }}</div>
          <div class="progress-bar-wrap">
            <div class="progress-bar" :style="{ width: progressPercent(c) + '%' }" :class="{ full: c.completed >= c.expected }"></div>
          </div>
          <div class="progress-nums">{{ c.completed }}/{{ c.expected }}</div>
        </div>
      </div>
    </div>

    <!-- 夜班检查问题 -->
    <div class="section" v-if="nsOverview?.today_duty?.status === 'completed' && nsOverview.issue_stats.total > 0">
      <div class="section-header">
        <h3 class="section-title" :class="{ 'warning-text': nsOverview.issue_stats.unresolved > 0 }">夜班检查问题 ({{ nsOverview.issue_stats.unresolved }} 未整改)</h3>
        <router-link to="/safety/nightshift" class="section-link">查看详情 →</router-link>
      </div>
      <div class="abnormal-list">
        <div v-for="(issue, i) in nsOverview.recent_issues" :key="i" class="abnormal-row" :class="{ resolved: issue.is_resolved }">
          <span class="abnormal-room">{{ issue.is_resolved ? '✓ 已整改' : '✗ 未整改' }}</span>
          <span class="abnormal-item-name">{{ issue.description }}</span>
          <span v-if="issue.rectification" class="abnormal-remark">{{ issue.rectification }}</span>
        </div>
      </div>
    </div>

    <!-- 今日异常 -->
    <div class="section" v-if="overview && overview.recent_abnormals.length">
      <div class="section-header">
        <h3 class="section-title warning-text">今日异常项</h3>
      </div>
      <div class="abnormal-list">
        <div v-for="(a, i) in overview.recent_abnormals" :key="i" class="abnormal-row">
          <span class="abnormal-room">{{ a.room_name }}</span>
          <span class="abnormal-item-name">{{ a.item_name }}</span>
          <span class="abnormal-meta">{{ a.inspector }} · {{ a.time }}</span>
          <span v-if="a.remark" class="abnormal-remark">{{ a.remark }}</span>
        </div>
      </div>
    </div>

    <!-- 无数据提示 -->
    <div v-if="!loading && !overview" class="empty-state">
      <p>暂无除尘房巡检数据</p>
      <router-link to="/safety/dustroom/admin" class="setup-link">前往配置除尘房巡检 →</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { dustroomApi } from '@/api/dustroom'
import type { OverviewData } from '@/api/dustroom'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftOverview } from '@/api/nightshift'
import http from '@/api/http'

const loading = ref(true)
const overview = ref<OverviewData | null>(null)
const nsOverview = ref<NightShiftOverview | null>(null)

const hazardStats = ref({ pending: 0 })
const mezzanineStats = ref({ onsite: 0, today: 0 })
const rectStats = ref({ pending: 0, fixing: 0, verifying: 0, overdue: 0 })

const nsStatusText = computed(() => {
  if (!nsOverview.value) return '-'
  const duty = nsOverview.value.today_duty
  if (!duty) return '今日无排班'
  if (duty.status === 'completed') {
    return nsOverview.value.issue_stats.unresolved > 0 ? '有问题' : '已完成'
  }
  return '待检查'
})
const nsStatusClass = computed(() => {
  if (!nsOverview.value?.today_duty) return ''
  if (nsOverview.value.today_duty.status !== 'completed') return ''
  if (nsOverview.value.issue_stats.unresolved > 0) return 'warning'
  return 'good'
})

const completedRooms = computed(() => {
  if (!overview.value) return 0
  return overview.value.completion_by_role.reduce((sum, c) => sum + c.completed, 0)
})
const totalExpected = computed(() => {
  if (!overview.value) return 0
  return overview.value.completion_by_role.reduce((sum, c) => sum + c.expected, 0)
})
const dustRoomStatusText = computed(() => {
  if (!overview.value) return '-'
  if (overview.value.abnormal_count > 0) return '有异常'
  if (completedRooms.value >= totalExpected.value && totalExpected.value > 0) return '已完成'
  return '进行中'
})
const dustRoomStatusClass = computed(() => {
  if (!overview.value) return ''
  if (overview.value.abnormal_count > 0) return 'warning'
  if (completedRooms.value >= totalExpected.value && totalExpected.value > 0) return 'good'
  return ''
})

function progressPercent(c: { completed: number; expected: number }) {
  return c.expected ? Math.round(c.completed / c.expected * 100) : 0
}

onMounted(async () => {
  try {
    const [overviewRes, nsRes, hazardRes, mezzRes, rectRes] = await Promise.allSettled([
      dustroomApi.getOverview(),
      nightshiftApi.getOverview(),
      http.get('/api/safety/hazards/', { params: { status: 'pending', page_size: 1 } }),
      http.get('/api/safety/mezzanine/history/', { params: { status: 'onsite', page_size: 1 } }),
      http.get('/api/safety/rectifications/stats/'),
    ])
    if (overviewRes.status === 'fulfilled') {
      overview.value = overviewRes.value.data
    }
    if (nsRes.status === 'fulfilled') {
      nsOverview.value = nsRes.value.data
    }
    if (hazardRes.status === 'fulfilled') {
      hazardStats.value.pending = hazardRes.value.data.count || 0
    }
    if (mezzRes.status === 'fulfilled') {
      const d = mezzRes.value.data
      mezzanineStats.value.onsite = d.stats?.onsite_count || 0
      mezzanineStats.value.today = d.stats?.today_count || 0
    }
    if (rectRes.status === 'fulfilled') {
      const s = rectRes.value.data.by_status || {}
      rectStats.value = {
        pending: s.pending || 0,
        fixing: s.fixing || 0,
        verifying: s.verifying || 0,
        overdue: rectRes.value.data.overdue || 0,
      }
    }
  } finally { loading.value = false }
})
</script>

<style scoped>
.stat-cards {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px; margin-top: 16px;
}
.stat-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 18px; display: flex; gap: 14px; align-items: flex-start; text-decoration: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.stat-card.clickable:hover { border-color: var(--color-accent); box-shadow: 0 2px 12px rgba(74,158,255,0.08); }
.stat-icon {
  width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-icon.dustroom { background: rgba(74,158,255,0.12); color: var(--color-accent); }
.stat-icon.warning { background: rgba(255,170,0,0.12); color: var(--color-warning); }
.stat-icon.hazard { background: rgba(0,212,170,0.12); color: var(--color-healthy); }
.stat-icon.nightshift { background: rgba(52,73,94,0.15); color: #5dade2; }
.stat-icon.mezzanine { background: rgba(155,89,255,0.12); color: #9b59ff; }
.stat-icon.rectification { background: rgba(255, 138, 76, 0.12); color: #ff8a4c; }
.abnormal-row.resolved { border-left-color: var(--color-healthy); }
.stat-body { flex: 1; }
.stat-value { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.stat-value.warning { color: var(--color-warning); }
.stat-value.good { color: var(--color-healthy); }
.stat-label { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
.stat-detail { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; font-family: var(--font-mono); }

.section { margin-top: 28px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); }
.section-link { color: var(--color-accent); font-size: 0.85rem; text-decoration: none; }
.section-link:hover { text-decoration: underline; }
.warning-text { color: var(--color-warning); }

.progress-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.progress-item {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 12px 14px; display: flex; align-items: center; gap: 10px;
}
.progress-role { font-size: 0.85rem; color: var(--text-secondary); min-width: 70px; }
.progress-bar-wrap { flex: 1; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
.progress-bar { height: 100%; background: var(--color-accent); border-radius: 3px; transition: width 0.3s; }
.progress-bar.full { background: var(--color-healthy); }
.progress-nums { font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono); min-width: 36px; text-align: right; }

.abnormal-list { display: flex; flex-direction: column; gap: 6px; }
.abnormal-row {
  display: flex; gap: 12px; align-items: center; padding: 10px 14px;
  background: var(--bg-card); border-radius: var(--radius-md);
  border-left: 3px solid var(--color-warning); font-size: 0.85rem;
}
.abnormal-room { font-weight: 600; color: var(--text-primary); min-width: 80px; }
.abnormal-item-name { color: var(--text-secondary); flex: 1; }
.abnormal-meta { color: var(--text-muted); font-size: 0.8rem; white-space: nowrap; }
.abnormal-remark { color: var(--text-muted); font-size: 0.8rem; font-style: italic; }

.empty-state { text-align: center; padding: 48px 0; color: var(--text-muted); }
.setup-link { color: var(--color-accent); text-decoration: none; }
.setup-link:hover { text-decoration: underline; }

@media (max-width: 640px) {
  .stat-cards { grid-template-columns: 1fr 1fr; }
  .progress-grid { grid-template-columns: 1fr; }
  .abnormal-row { flex-wrap: wrap; }
}
</style>
