<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夜班检查记录</h2>
        <p class="page-subtitle">历史巡检记录查询</p>
      </div>
      <router-link to="/safety/nightshift" class="btn-back">← 返回</router-link>
    </div>

    <div class="filter-bar">
      <el-date-picker v-model="dateRange" type="daterange" size="small" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="onDateChange" />
      <el-checkbox v-model="issuesOnly" label="仅有问题" size="small" @change="loadRecords" />
    </div>

    <el-table :data="records" stripe size="small" v-loading="loading">
      <el-table-column prop="inspection_date" label="日期" width="110" />
      <el-table-column label="巡检人">
        <template #default="{ row }">{{ row.inspector_display.display_name }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.has_issues" type="warning" size="small">有问题</el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="abnormal_count" label="异常项" width="80" />
      <el-table-column prop="issue_count" label="问题数" width="80" />
      <el-table-column prop="unresolved_count" label="未整改" width="80" />
      <el-table-column label="提交时间" width="160">
        <template #default="{ row }">{{ row.submitted_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <router-link :to="`/safety/nightshift/records/${row.id}`" class="link-btn">详情</router-link>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next" small @current-change="loadRecords" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftRecordListItem } from '@/api/nightshift'

const loading = ref(false)
const records = ref<NightShiftRecordListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const dateRange = ref<[string, string] | null>(null)
const issuesOnly = ref(false)

function onDateChange() { loadRecords() }

async function loadRecords() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: pageSize }
    if (dateRange.value) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    if (issuesOnly.value) params.has_issues = 'true'
    const { data } = await nightshiftApi.getRecords(params)
    records.value = data.results
    total.value = data.count
  } finally { loading.value = false }
}

onMounted(loadRecords)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; padding: 6px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-default); }
.btn-back:hover { background: var(--bg-card); }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 16px 0; }
.link-btn { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; }
.link-btn:hover { text-decoration: underline; }
.pagination-bar { display: flex; justify-content: center; margin-top: 16px; }
</style>
