<template>
  <el-dialog
    v-model="visible"
    title="分派人管理"
    width="600px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <el-tabs v-model="activeTab">
      <el-tab-pane label="已授权用户" name="authorized">
        <el-table
          :data="assigners"
          v-loading="loading"
          style="width: 100%"
        >
          <el-table-column label="用户名" width="140" prop="username" />
          <el-table-column label="姓名" min-width="120">
            <template #default="{ row }">
              {{ row.display_name || row.username }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center">
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                @click="onRevoke(row)"
              >
                撤销
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!loading && assigners.length === 0"
          description="暂无已授权用户"
          :image-size="80"
        />
      </el-tab-pane>

      <el-tab-pane label="授予权限" name="grant">
        <div class="grant-section">
          <p class="desc">
            选择用户并授予分派权限，被授权的用户可以在整改中心分派整改工单。
          </p>

          <div class="grant-row">
            <el-select
              v-model="selectedUserId"
              filterable
              clearable
              placeholder="选择用户"
              style="width: 320px"
            >
              <el-option
                v-for="u in candidates"
                :key="u.id"
                :label="`${u.display_name || u.username} (${u.username})`"
                :value="u.id"
              />
            </el-select>
            <el-button
              type="primary"
              :disabled="!selectedUserId"
              @click="onGrant"
            >
              授予权限
            </el-button>
          </div>

          <el-empty
            v-if="!loadingCandidates && candidates.length === 0"
            description="暂无可授权用户"
            :image-size="80"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'
import type { UserBrief } from '@/api/safety'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const visible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const activeTab = ref<'authorized' | 'grant'>('authorized')
const loading = ref(false)
const loadingCandidates = ref(false)
const assigners = ref<UserBrief[]>([])
const candidates = ref<UserBrief[]>([])
const selectedUserId = ref<number | undefined>(undefined)

async function fetchAssigners() {
  loading.value = true
  try {
    const { data } = await http.get<{ assigners: UserBrief[] }>(
      '/api/safety/rectifications/assigners/'
    )
    assigners.value = data.assigners
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '获取已授权用户失败')
  } finally {
    loading.value = false
  }
}

async function fetchCandidates() {
  loadingCandidates.value = true
  try {
    const { data } = await http.get<{ candidates: UserBrief[] }>(
      '/api/safety/rectifications/assigners/candidates/'
    )
    candidates.value = data.candidates
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '获取候选用户失败')
  } finally {
    loadingCandidates.value = false
  }
}

async function onOpen() {
  await Promise.all([fetchAssigners(), fetchCandidates()])
}

async function onGrant() {
  if (!selectedUserId.value) return

  try {
    await http.post('/api/safety/rectifications/assigners/grant/', {
      user_id: selectedUserId.value,
    })
    ElMessage.success('授权成功')
    selectedUserId.value = undefined
    await Promise.all([fetchAssigners(), fetchCandidates()])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '授权失败')
  }
}

async function onRevoke(user: UserBrief) {
  try {
    await ElMessageBox.confirm(
      `确认撤销 ${user.display_name || user.username} 的分派权限？`,
      '撤销权限',
      { type: 'warning' }
    )
  } catch {
    return
  }

  try {
    await http.post('/api/safety/rectifications/assigners/revoke/', {
      user_id: user.id,
    })
    ElMessage.success('撤销成功')
    await Promise.all([fetchAssigners(), fetchCandidates()])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '撤销失败')
  }
}
</script>

<style scoped>
.desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  background: var(--bg-card-elevated, #fafafa);
  padding: 10px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.grant-section {
  min-height: 200px;
}

.grant-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
</style>

