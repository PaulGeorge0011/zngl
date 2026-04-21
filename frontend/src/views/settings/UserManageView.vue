<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">用户管理</h2>
        <p class="page-subtitle">管理系统账号与角色权限</p>
      </div>
      <el-button
        v-if="userStore.isSafetyOfficer"
        type="primary"
        @click="openDrawer(null)"
      >
        + 新建用户
      </el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="filter-card">
      <el-input
        v-model="searchText"
        placeholder="搜索姓名 / 用户名 / 工号"
        clearable
        style="width: 280px"
        @keyup.enter="fetchUsers"
        @clear="fetchUsers"
      />
      <el-button @click="fetchUsers">搜索</el-button>
    </div>

    <!-- 表格 -->
    <div class="table-card">
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column label="姓名" min-width="100">
          <template #default="{ row }">
            <span :class="{ 'text-muted': !row.is_active }">{{ row.name || row.username }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用户名" width="130" prop="username" />
        <el-table-column label="工号" width="120" prop="employee_id">
          <template #default="{ row }">{{ row.employee_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="联系电话" width="140" prop="phone">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-dot" :class="row.is_active ? 'active' : 'inactive'">
              {{ row.is_active ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.isSafetyOfficer" label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openDrawer(row)">编辑</el-button>
            <el-button
              text
              size="small"
              :type="row.is_active ? 'danger' : 'success'"
              @click="handleToggle(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 抽屉 -->
    <UserDrawer v-model="drawerVisible" :user="drawerUser" @saved="fetchUsers" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userManageApi, type ManagedUser } from '@/api/users'
import { useUserStore } from '@/stores/user'
import UserDrawer from '@/components/users/UserDrawer.vue'

const userStore = useUserStore()
const loading = ref(false)
const users = ref<ManagedUser[]>([])
const searchText = ref('')
const drawerVisible = ref(false)
const drawerUser = ref<ManagedUser | null>(null)

onMounted(fetchUsers)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await userManageApi.list(searchText.value || undefined)
    users.value = data
  } finally {
    loading.value = false
  }
}

function openDrawer(user: ManagedUser | null) {
  drawerUser.value = user
  drawerVisible.value = true
}

async function handleToggle(user: ManagedUser) {
  const action = user.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${user.name || user.username}」吗？`,
      '确认操作',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await userManageApi.toggle(user.id)
    ElMessage.success(`已${action}`)
    fetchUsers()
  } catch {
    // 错误由拦截器展示
  }
}

const ROLE_LABELS: Record<string, string> = {
  safety_officer: '安全员',
  team_leader: '班组长',
  worker: '员工',
}

const ROLE_TAG_TYPES: Record<string, string> = {
  safety_officer: 'danger',
  team_leader: 'warning',
  worker: 'info',
}

function roleLabel(role: string) { return ROLE_LABELS[role] || role }
function roleTagType(role: string) { return ROLE_TAG_TYPES[role] || 'info' }
</script>

<style scoped>
.filter-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.text-muted {
  opacity: 0.45;
}

.status-dot {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.status-dot.active {
  background: var(--color-healthy-dim);
  color: var(--color-healthy);
}

.status-dot.inactive {
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
}

@media (max-width: 960px) {
  .filter-card {
    padding: 14px;
    flex-wrap: wrap;
    align-items: stretch;
  }

  .filter-card :deep(.el-input) {
    width: 100% !important;
  }

  .table-card :deep(.el-table) {
    min-width: 760px;
  }
}
</style>
