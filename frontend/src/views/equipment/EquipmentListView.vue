<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">设备管理</h2>
        <p class="page-subtitle">制丝车间设备信息管理与维护</p>
      </div>
      <el-button type="primary" @click="$router.push('/equipment/new')">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px">
          <line x1="7" y1="2" x2="7" y2="12"/><line x1="2" y1="7" x2="12" y2="7"/>
        </svg>
        新增设备
      </el-button>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索设备名称、编号、地点..."
        clearable
        style="width: 280px"
        @input="handleSearch"
      >
        <template #prefix>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="6" cy="6" r="4.5"/><line x1="9.5" y1="9.5" x2="13" y2="13"/>
          </svg>
        </template>
      </el-input>
      <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="fetchData">
        <el-option label="运行中" value="running" />
        <el-option label="停机" value="stopped" />
        <el-option label="故障" value="fault" />
      </el-select>
    </div>

    <!-- Table -->
    <div class="table-wrapper">
      <el-table :data="equipments" v-loading="loading" stripe>
        <el-table-column prop="code" label="编号" width="120">
          <template #default="{ row }">
            <span class="data-value">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="location" label="安装地点" min-width="140" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusTagType(row.status)"
              effect="dark"
              size="small"
              round
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="monitor_points_count" label="监控点" width="80" align="center">
          <template #default="{ row }">
            <span class="data-value">{{ row.monitor_points_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="active_alarms_count" label="活跃报警" width="90" align="center">
          <template #default="{ row }">
            <span
              class="data-value"
              :class="{ 'status-fault': row.active_alarms_count > 0 }"
            >
              {{ row.active_alarms_count || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/equipment/${row.id}`)">
              详情
            </el-button>
            <el-button link type="primary" @click="$router.push(`/equipment/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { equipmentApi } from '@/api/equipment'
import type { Equipment } from '@/types'
import { ElMessageBox, ElMessage } from 'element-plus'

const equipments = ref<Equipment[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const searchQuery = ref('')
const statusFilter = ref('')

let searchTimer: ReturnType<typeof setTimeout>

function statusTagType(status: string) {
  return { running: 'success', stopped: 'info', fault: 'danger' }[status] || 'info'
}

function statusLabel(status: string) {
  return { running: '运行中', stopped: '停机', fault: '故障' }[status] || status
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchData()
  }, 300)
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value }
    if (searchQuery.value) params.search = searchQuery.value
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await equipmentApi.list(params)
    equipments.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

async function handleDelete(row: Equipment) {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备「${row.name}」吗？相关监控点和报警记录也会被删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await equipmentApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // cancelled
  }
}

onMounted(fetchData)
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

@media (max-width: 960px) {
  .filter-bar {
    flex-wrap: wrap;
  }

  .filter-bar :deep(.el-input),
  .filter-bar :deep(.el-select) {
    width: 100% !important;
  }

  .table-wrapper :deep(.el-table) {
    min-width: 860px;
  }
}

@media (max-width: 640px) {
  .table-footer {
    justify-content: center;
    padding: 12px;
  }

  .table-footer :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
