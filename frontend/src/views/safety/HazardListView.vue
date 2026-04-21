<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">随手拍 · 找隐患</h2>
        <p class="page-subtitle">安全隐患上报与处理跟踪</p>
      </div>
      <el-button type="primary" @click="router.push('/safety/hazard/report')">
        + 上报隐患
      </el-button>
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
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="fetchList">
          <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="filters.level" placeholder="等级" clearable style="width: 120px" @change="fetchList">
          <el-option label="一般隐患" value="general" />
          <el-option label="重大隐患" value="major" />
        </el-select>
        <el-select v-model="filters.location" placeholder="区域" clearable style="width: 130px" @change="fetchList">
          <el-option v-for="loc in locations" :key="loc.id" :label="loc.name" :value="loc.id" />
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
        :data="hazards"
        v-loading="loading"
        row-class-name="table-row-hover"
        @row-click="(row: any) => router.push(`/safety/hazard/${row.id}`)"
        style="width: 100%"
      >
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <span class="hazard-title">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'major' ? 'danger' : 'info'" size="small">
              {{ row.level_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="区域" width="110" prop="location_name" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-tag" :class="`status-${row.status}`">
              {{ row.status_display }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="上报人" width="100">
          <template #default="{ row }">{{ row.reporter.display_name }}</template>
        </el-table-column>
        <el-table-column label="整改人" width="100">
          <template #default="{ row }">{{ row.assignee?.display_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="上报时间" width="160" prop="created_at" />
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchList"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { safetyApi } from '@/api/safety'
import type { HazardListItem, Location } from '@/api/safety'

const router = useRouter()
const loading = ref(false)
const hazards = ref<HazardListItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const locations = ref<Location[]>([])
const dateRange = ref<[string, string] | null>(null)

const filters = reactive({
  search: '',
  status: '',
  level: '',
  location: null as number | null,
  date_from: '',
  date_to: '',
})

const STATUS_OPTIONS = [
  { value: 'pending', label: '待分派' },
  { value: 'fixing', label: '整改中' },
  { value: 'verifying', label: '待验证' },
  { value: 'closed', label: '已关闭' },
  { value: 'rejected', label: '驳回' },
]

onMounted(async () => {
  const [, locs] = await Promise.allSettled([
    fetchList(),
    safetyApi.getLocations(),
  ])
  if (locs.status === 'fulfilled') locations.value = locs.value.data
})

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    if (filters.level) params.level = filters.level
    if (filters.location) params.location = filters.location
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to

    const { data } = await safetyApi.listHazards(params)
    hazards.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

function onDateChange(val: [string, string] | null) {
  filters.date_from = val?.[0] || ''
  filters.date_to = val?.[1] || ''
  fetchList()
}

function resetFilters() {
  Object.assign(filters, { search: '', status: '', level: '', location: null, date_from: '', date_to: '' })
  dateRange.value = null
  currentPage.value = 1
  fetchList()
}
</script>

<style scoped>
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

.hazard-title {
  font-weight: 500;
  color: var(--text-primary);
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
.status-rejected { background: var(--color-alarm-dim); color: var(--color-alarm); }

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
  .filter-card {
    padding: 14px;
  }

  .filter-row > * {
    width: 100% !important;
  }

  .table-card :deep(.el-table) {
    min-width: 920px;
  }
}

@media (max-width: 640px) {
  .pagination-row {
    justify-content: center;
    padding: 12px;
  }
}
</style>
