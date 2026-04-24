<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">整改中心</h2>
        <p class="page-subtitle">所有安全管理模块发现的问题，统一在这里跟踪闭环</p>
      </div>
      <div class="header-stats" v-if="stats">
        <span class="stat-pill stat-pill--total">总数 {{ stats.total }}</span>
        <span class="stat-pill stat-pill--pending">待分派 {{ stats.by_status.pending || 0 }}</span>
        <span class="stat-pill stat-pill--fixing">整改中 {{ stats.by_status.fixing || 0 }}</span>
        <span class="stat-pill stat-pill--verifying">待验证 {{ stats.by_status.verifying || 0 }}</span>
        <span class="stat-pill stat-pill--overdue" v-if="stats.overdue > 0">逾期 {{ stats.overdue }}</span>
      </div>
    </div>

    <!-- 我的工作台四象限 -->
    <div class="tab-cards">
      <div
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-card"
        :class="{ active: activeScope === tab.value }"
        @click="switchScope(tab.value)"
      >
        <div class="tab-card-num">{{ countOf(tab.value) }}</div>
        <div class="tab-card-label">{{ tab.label }}</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="搜索标题/描述"
          clearable
          style="width: 220px"
          @keyup.enter="fetchList"
          @clear="fetchList"
        />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="fetchList">
          <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.source_type" placeholder="来源" clearable style="width: 140px" @change="fetchList">
          <el-option v-for="s in SOURCE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.severity" placeholder="严重等级" clearable style="width: 120px" @change="fetchList">
          <el-option v-for="s in SEVERITY_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.overdue" placeholder="逾期" clearable style="width: 100px" @change="fetchList">
          <el-option label="仅看逾期" value="true" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="~"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="onDateChange"
        />
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table
        :data="orders"
        v-loading="loading"
        row-class-name="table-row-hover"
        @row-click="(row: RectListItem) => router.push(`/safety/rectification/${row.id}`)"
        style="width: 100%"
      >
        <el-table-column label="标题" min-width="220">
          <template #default="{ row }">
            <span class="rect-title">{{ row.title }}</span>
            <span v-if="row.overdue" class="overdue-badge">逾期</span>
            <span v-if="row.reject_count > 0" class="reject-badge">驳回 {{ row.reject_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="120" prop="source_type_display" />
        <el-table-column label="严重" width="80">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)" size="small">{{ row.severity_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="位置" min-width="120" prop="location_text" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-tag" :class="`status-${row.status}`">{{ row.status_display }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提交人" width="100">
          <template #default="{ row }">{{ row.submitter.display_name }}</template>
        </el-table-column>
        <el-table-column label="责任人" width="100">
          <template #default="{ row }">{{ row.assignee?.display_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="期限" width="160">
          <template #default="{ row }">
            <span :class="{ 'overdue-text': row.overdue }">{{ formatDateTime(row.deadline) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-row" v-if="total > pageSize">
        <el-pagination
          background
          layout="prev, pager, next, total"
          :total="total"
          :page-size="pageSize"
          v-model:current-page="currentPage"
          @current-change="fetchList"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { rectificationApi } from '@/api/rectification'
import type {
  RectListItem,
  RectMyCounts,
  RectStats,
  RectFilters,
} from '@/api/rectification'

const router = useRouter()

const orders = ref<RectListItem[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const dateRange = ref<[string, string] | null>(null)
const stats = ref<RectStats | null>(null)
const myCounts = ref<RectMyCounts | null>(null)
const activeScope = ref<RectFilters['scope']>('')

const filters = reactive<RectFilters>({
  search: '',
  status: undefined,
  source_type: undefined,
  severity: undefined,
  overdue: undefined,
  date_from: '',
  date_to: '',
  scope: '',
})

const STATUS_OPTIONS = [
  { value: 'pending', label: '待分派' },
  { value: 'fixing', label: '整改中' },
  { value: 'verifying', label: '待验证' },
  { value: 'closed', label: '已闭环' },
  { value: 'cancelled', label: '已取消' },
]

const SOURCE_OPTIONS = [
  { value: 'hazard_report', label: '安全隐患上报' },
  { value: 'dustroom_inspection', label: '除尘房巡检' },
  { value: 'nightshift_check', label: '夜班监护检查' },
]

const SEVERITY_OPTIONS = [
  { value: 'general', label: '一般' },
  { value: 'major', label: '重要' },
  { value: 'critical', label: '严重' },
]

const tabs = [
  { value: '' as const, label: '全部' },
  { value: 'assigned' as const, label: '待我整改' },
  { value: 'to_verify' as const, label: '待我验证' },
  { value: 'to_assign' as const, label: '待我分派' },
  { value: 'submitted' as const, label: '我提交的' },
]

onMounted(async () => {
  await Promise.allSettled([
    fetchList(),
    fetchStats(),
    fetchMyCounts(),
  ])
})

function countOf(scope: RectFilters['scope']): number {
  if (!myCounts.value) return 0
  switch (scope) {
    case 'assigned': return myCounts.value.to_fix
    case 'to_verify': return myCounts.value.to_verify
    case 'to_assign': return myCounts.value.to_assign
    case 'submitted': return myCounts.value.submitted
    default: return stats.value?.total ?? 0
  }
}

async function fetchList() {
  loading.value = true
  try {
    const params: RectFilters = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    if (filters.source_type) params.source_type = filters.source_type
    if (filters.severity) params.severity = filters.severity
    if (filters.overdue) params.overdue = filters.overdue
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to
    if (activeScope.value) params.scope = activeScope.value

    const { data } = await rectificationApi.list(params)
    orders.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const { data } = await rectificationApi.stats()
    stats.value = data
  } catch {
    stats.value = null
  }
}

async function fetchMyCounts() {
  try {
    const { data } = await rectificationApi.myCounts()
    myCounts.value = data
  } catch {
    myCounts.value = null
  }
}

function switchScope(scope: RectFilters['scope']) {
  activeScope.value = scope
  currentPage.value = 1
  fetchList()
}

function onDateChange(val: [string, string] | null) {
  filters.date_from = val?.[0] || ''
  filters.date_to = val?.[1] || ''
  fetchList()
}

function resetFilters() {
  Object.assign(filters, {
    search: '', status: undefined, source_type: undefined,
    severity: undefined, overdue: undefined,
    date_from: '', date_to: '', scope: '',
  })
  dateRange.value = null
  activeScope.value = ''
  currentPage.value = 1
  fetchList()
}

function severityTagType(s: string): 'info' | 'warning' | 'danger' {
  if (s === 'critical') return 'danger'
  if (s === 'major') return 'warning'
  return 'info'
}

function formatDateTime(s: string | null): string {
  if (!s) return '—'
  return s.replace('T', ' ').slice(0, 16)
}
</script>

<style scoped>
.header-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-pill {
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg-card-elevated, #f5f5f5);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.stat-pill--pending  { background: var(--color-info-dim); color: var(--color-accent); border-color: transparent; }
.stat-pill--fixing   { background: var(--color-warning-dim); color: var(--color-warning); border-color: transparent; }
.stat-pill--verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; border-color: transparent; }
.stat-pill--overdue  { background: var(--color-alarm-dim); color: var(--color-alarm); border-color: transparent; font-weight: 600; }

.tab-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.tab-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s;
  text-align: center;
}

.tab-card:hover {
  border-color: var(--color-accent);
}

.tab-card.active {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-info-dim);
}

.tab-card-num {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
}

.tab-card-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 4px;
}

.filter-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 0;
  overflow: hidden;
}

.rect-title {
  font-weight: 500;
  color: var(--text-primary);
}

.overdue-badge {
  margin-left: 6px;
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
}

.reject-badge {
  margin-left: 6px;
  background: rgba(160, 100, 255, 0.15);
  color: #a064ff;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 3px;
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-pending  { background: var(--color-info-dim); color: var(--color-accent); }
.status-fixing   { background: var(--color-warning-dim); color: var(--color-warning); }
.status-verifying { background: rgba(160, 100, 255, 0.15); color: #a064ff; }
.status-closed   { background: var(--color-healthy-dim); color: var(--color-healthy); }
.status-cancelled { background: #f0f0f0; color: #999; }

.overdue-text { color: var(--color-alarm); font-weight: 600; }

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}

:deep(.table-row-hover) {
  cursor: pointer;
}

@media (max-width: 960px) {
  .tab-cards { grid-template-columns: repeat(2, 1fr); }
  .filter-card { padding: 14px; }
  .filter-row > * { width: 100% !important; }
  .table-card :deep(.el-table) { min-width: 920px; }
}
</style>
