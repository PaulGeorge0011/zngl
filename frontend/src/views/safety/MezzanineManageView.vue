<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夹层施工管理</h2>
        <p class="page-subtitle">施工人员入离场记录查询</p>
      </div>
      <el-button v-if="userStore.isSafetyOfficer" type="primary" @click="openDialog(null)">
        + 手动添加
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.today_count }}</div>
        <div class="stat-label">今日入场人次</div>
      </div>
      <div class="stat-card stat-card--accent">
        <div class="stat-value">{{ stats.onsite_count }}</div>
        <div class="stat-label">当前在场人数</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-card">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="姓名 / 手机号"
          clearable
          style="width: 200px"
          @keyup.enter="fetchData"
          @clear="fetchData"
        />
        <el-input
          v-model="filters.project"
          placeholder="施工项目"
          clearable
          style="width: 180px"
          @keyup.enter="fetchData"
          @clear="fetchData"
        />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="fetchData">
          <el-option label="在场中" value="onsite" />
          <el-option label="已离场" value="left" />
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
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table :data="records" v-loading="loading" style="width: 100%">
        <el-table-column label="姓名" width="100" prop="name" />
        <el-table-column label="手机号" width="130" prop="phone" />
        <el-table-column label="施工单位" min-width="140" prop="company">
          <template #default="{ row }">{{ row.company || '—' }}</template>
        </el-table-column>
        <el-table-column label="施工项目" min-width="180" prop="project" />
        <el-table-column label="人数" width="70" prop="count" />
        <el-table-column label="入场时间" width="160" prop="check_in_at" />
        <el-table-column label="离场时间" width="160">
          <template #default="{ row }">{{ row.check_out_at || '—' }}</template>
        </el-table-column>
        <el-table-column label="在场时长" width="100" prop="duration" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-tag" :class="row.status === 'onsite' ? 'status-onsite' : 'status-left'">
              {{ row.status === 'onsite' ? '在场中' : '已离场' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.isSafetyOfficer" label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingRecord ? '编辑记录' : '手动添加'" width="480px">
      <el-form :model="dialogForm" label-position="top">
        <el-form-item label="姓名" required>
          <el-input v-model="dialogForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" required>
          <el-input v-model="dialogForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="施工单位">
          <el-input v-model="dialogForm.company" placeholder="选填" />
        </el-form-item>
        <el-form-item label="施工项目" required>
          <el-input v-model="dialogForm.project" placeholder="请输入施工项目" />
        </el-form-item>
        <el-form-item label="人数">
          <el-input-number v-model="dialogForm.count" :min="1" :max="99" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogSaving" @click="handleSave">
          {{ editingRecord ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mezzanineApi, type MezzanineRecord } from '@/api/mezzanine'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)
const records = ref<MezzanineRecord[]>([])
const total = ref(0)
const currentPage = ref(1)
const dateRange = ref<[string, string] | null>(null)
const stats = reactive({ today_count: 0, onsite_count: 0 })

const filters = reactive({
  search: '',
  project: '',
  status: '' as '' | 'onsite' | 'left',
  date_from: '',
  date_to: '',
})

// Dialog state
const dialogVisible = ref(false)
const dialogSaving = ref(false)
const editingRecord = ref<MezzanineRecord | null>(null)
const dialogForm = reactive({
  name: '',
  phone: '',
  company: '',
  project: '',
  count: 1,
})

onMounted(fetchData)

async function fetchData() {
  loading.value = true
  try {
    const { data } = await mezzanineApi.history({
      search: filters.search || undefined,
      project: filters.project || undefined,
      status: filters.status || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: currentPage.value,
    })
    records.value = data.results
    total.value = data.count
    stats.today_count = data.stats.today_count
    stats.onsite_count = data.stats.onsite_count
  } finally {
    loading.value = false
  }
}

function onDateChange(val: [string, string] | null) {
  filters.date_from = val?.[0] || ''
  filters.date_to = val?.[1] || ''
  fetchData()
}

function resetFilters() {
  Object.assign(filters, { search: '', project: '', status: '', date_from: '', date_to: '' })
  dateRange.value = null
  currentPage.value = 1
  fetchData()
}

function openDialog(record: MezzanineRecord | null) {
  editingRecord.value = record
  if (record) {
    dialogForm.name = record.name
    dialogForm.phone = record.phone
    dialogForm.company = record.company
    dialogForm.project = record.project
    dialogForm.count = record.count
  } else {
    Object.assign(dialogForm, { name: '', phone: '', company: '', project: '', count: 1 })
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!dialogForm.name.trim() || !dialogForm.phone.trim() || !dialogForm.project.trim()) {
    ElMessage.warning('请填写必填项')
    return
  }
  dialogSaving.value = true
  try {
    const payload = {
      name: dialogForm.name.trim(),
      phone: dialogForm.phone.trim(),
      company: dialogForm.company.trim(),
      project: dialogForm.project.trim(),
      count: dialogForm.count,
    }
    if (editingRecord.value) {
      await mezzanineApi.update(editingRecord.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await mezzanineApi.create(payload)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch {
    // error shown by interceptor
  } finally {
    dialogSaving.value = false
  }
}

async function handleDelete(record: MezzanineRecord) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${record.name}」的施工记录吗？`,
      '确认删除',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await mezzanineApi.remove(record.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // error shown by interceptor
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(2, 200px);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  text-align: center;
}

.stat-card--accent { border-color: var(--color-accent); }

.stat-value {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
  margin-bottom: 6px;
}

.stat-label { font-size: 0.85rem; color: var(--text-muted); }

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
  overflow: hidden;
}

.status-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-onsite {
  background: var(--color-healthy-dim);
  color: var(--color-healthy);
}

.status-left {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}

@media (max-width: 960px) {
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }

  .filter-card {
    padding: 14px;
  }

  .filter-row > * {
    width: 100% !important;
  }

  .table-card :deep(.el-table) {
    min-width: 1020px;
  }
}

@media (max-width: 640px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 16px;
  }

  .pagination-row {
    justify-content: center;
    padding: 12px;
  }
}
</style>
