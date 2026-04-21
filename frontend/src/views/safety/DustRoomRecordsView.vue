<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">巡检记录</h2>
        <p class="page-subtitle">除尘房巡检历史记录查询</p>
      </div>
      <router-link to="/safety/dustroom" class="btn-back">← 返回巡检</router-link>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filters.dust_room" placeholder="除尘房" clearable size="small" @change="loadRecords">
        <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-select v-model="filters.role" placeholder="角色" clearable size="small" @change="loadRecords">
        <el-option label="电气修理工" value="electrical" />
        <el-option label="机械修理工" value="mechanical" />
        <el-option label="操作工" value="operator" />
        <el-option label="安全员" value="safety" />
      </el-select>
      <el-date-picker v-model="dateRange" type="daterange" size="small" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="onDateChange" />
      <el-checkbox v-model="filters.abnormalOnly" label="仅异常" size="small" @change="loadRecords" />
    </div>

    <!-- 记录列表 -->
    <el-table :data="records" stripe size="small" v-loading="loading">
      <el-table-column prop="inspection_date" label="日期" width="110" />
      <el-table-column prop="dust_room_name" label="除尘房" width="120" />
      <el-table-column prop="role_display" label="角色" width="110" />
      <el-table-column label="巡检人">
        <template #default="{ row }">{{ row.inspector_display.display_name }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.has_abnormal" type="warning" size="small">有异常</el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="abnormal_count" label="异常项数" width="90" />
      <el-table-column label="提交时间" width="160">
        <template #default="{ row }">{{ row.submitted_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <router-link :to="`/safety/dustroom/records/${row.id}`" class="link-btn">详情</router-link>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        small
        @current-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { dustroomApi } from '@/api/dustroom'
import type { DustRoom, InspectionRecordListItem } from '@/api/dustroom'

const loading = ref(false)
const rooms = ref<DustRoom[]>([])
const records = ref<InspectionRecordListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const dateRange = ref<[string, string] | null>(null)

const filters = reactive({
  dust_room: '' as string | number,
  role: '',
  date_from: '',
  date_to: '',
  abnormalOnly: false,
})

function onDateChange(val: [string, string] | null) {
  filters.date_from = val ? val[0] : ''
  filters.date_to = val ? val[1] : ''
  loadRecords()
}

async function loadRecords() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: pageSize }
    if (filters.dust_room) params.dust_room = filters.dust_room
    if (filters.role) params.role = filters.role
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to
    if (filters.abnormalOnly) params.has_abnormal = 'true'

    const { data } = await dustroomApi.getRecords(params)
    records.value = data.results
    total.value = data.count
  } finally { loading.value = false }
}

onMounted(async () => {
  const { data } = await dustroomApi.getRooms()
  rooms.value = data
  loadRecords()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back {
  color: var(--color-accent); text-decoration: none; font-size: 0.85rem;
  padding: 6px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-default);
}
.btn-back:hover { background: var(--bg-card); }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 16px 0; }
.link-btn { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; }
.link-btn:hover { text-decoration: underline; }
.pagination-bar { display: flex; justify-content: center; margin-top: 16px; }
</style>
