<template>
  <el-dialog
    v-model="visible"
    title="整改中心 — 新工单短信接收人配置"
    width="720px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <p class="desc">
      在此配置的人员，当整改中心产生新工单时会收到短信通知。
      留空"来源过滤"表示所有来源都通知；选择特定来源则仅匹配时通知。
    </p>

    <div class="add-row">
      <el-select
        v-model="newForm.userId" filterable clearable
        placeholder="选择用户" style="width: 260px"
      >
        <el-option
          v-for="u in users" :key="u.id"
          :label="`${u.display_name || u.username} (${u.username})`"
          :value="u.id"
        />
      </el-select>
      <el-select
        v-model="newForm.sourceType" placeholder="来源过滤" clearable style="width: 180px"
      >
        <el-option label="全部来源" value="" />
        <el-option label="安全隐患上报" value="hazard_report" />
        <el-option label="除尘房巡检" value="dustroom_inspection" />
        <el-option label="夜班监护检查" value="nightshift_check" />
      </el-select>
      <el-button
        type="primary" :disabled="!newForm.userId" @click="onAdd"
      >添加</el-button>
    </div>

    <el-table :data="recipients" v-loading="loading" style="margin-top: 12px">
      <el-table-column label="用户" min-width="140">
        <template #default="{ row }">{{ row.user.display_name || row.user.username }}</template>
      </el-table-column>
      <el-table-column label="手机号" width="140" prop="phone">
        <template #default="{ row }">
          <span v-if="row.phone">{{ row.phone }}</span>
          <el-tag v-else type="danger" size="small">未设置</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="来源" width="130" prop="source_type_display" />
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            @change="(val: boolean) => onToggle(row, val)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" @click="onRemove(row)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { rectificationApi } from '@/api/rectification'
import type { RectNotifyRecipient, RectNotifySource } from '@/api/rectification'
import { usersApi } from '@/api/users'
import type { UserInfo } from '@/stores/user'

interface Props { modelValue: boolean }
const props = defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const recipients = ref<RectNotifyRecipient[]>([])
const users = ref<UserInfo[]>([])

const newForm = reactive({
  userId: undefined as number | undefined,
  sourceType: '' as RectNotifySource,
})

async function fetchRecipients() {
  loading.value = true
  try {
    const { data } = await rectificationApi.listNotifyRecipients()
    recipients.value = data
  } finally {
    loading.value = false
  }
}

async function fetchUsers() {
  try {
    const { data } = await usersApi.list()
    users.value = data
  } catch {
    users.value = []
  }
}

async function onOpen() {
  await Promise.all([fetchRecipients(), fetchUsers()])
}

async function onAdd() {
  if (!newForm.userId) return
  try {
    await rectificationApi.addNotifyRecipient({
      user_id: newForm.userId,
      source_type: newForm.sourceType,
    })
    newForm.userId = undefined
    newForm.sourceType = ''
    await fetchRecipients()
    ElMessage.success('已添加')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '添加失败')
  }
}

async function onToggle(row: RectNotifyRecipient, enabled: boolean) {
  try {
    await rectificationApi.toggleNotifyRecipient(row.id, enabled)
    row.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '更新失败')
  }
}

async function onRemove(row: RectNotifyRecipient) {
  try {
    await ElMessageBox.confirm(
      `确认移除 ${row.user.display_name || row.user.username} 的通知？`,
      '移除接收人',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await rectificationApi.removeNotifyRecipient(row.id)
    await fetchRecipients()
    ElMessage.success('已移除')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '移除失败')
  }
}

watch(() => props.modelValue, (v) => { if (v) onOpen() })
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

.add-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
