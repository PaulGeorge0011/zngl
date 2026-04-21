<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">夜班检查配置</h2>
        <p class="page-subtitle">管理检查分类和预置检查项</p>
      </div>
      <router-link to="/safety/nightshift" class="btn-back">← 返回</router-link>
    </div>

    <el-tabs v-model="activeTab" class="admin-tabs">
      <!-- Tab 1: 分类管理 -->
      <el-tab-pane label="检查分类" name="categories">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="showCatDialog()">新增分类</el-button>
        </div>
        <el-table :data="categories" stripe size="small">
          <el-table-column prop="name" label="分类名称" />
          <el-table-column label="允许自填" width="100">
            <template #default="{ row }">{{ row.allows_custom ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column prop="items_count" label="检查项数" width="100" />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button link size="small" @click="showCatDialog(row)">编辑</el-button>
              <el-button link size="small" type="primary" @click="manageItems(row)">检查项</el-button>
              <el-popconfirm title="确定删除？" @confirm="deleteCat(row.id)">
                <template #reference>
                  <el-button link size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 排班管理 -->
      <el-tab-pane label="排班管理" name="duties">
        <div class="tab-toolbar">
          <div class="month-nav">
            <el-button size="small" @click="changeMonth(-1)">←</el-button>
            <span class="month-label">{{ dutyMonth }}</span>
            <el-button size="small" @click="changeMonth(1)">→</el-button>
          </div>
          <el-button type="primary" size="small" @click="showDutyDialog()">新增排班</el-button>
        </div>
        <el-table :data="duties" stripe size="small">
          <el-table-column prop="duty_date" label="日期" width="120" />
          <el-table-column label="检查人">
            <template #default="{ row }">{{ row.inspector_display.display_name }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'info'" size="small">{{ row.status_display }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="有问题" width="80">
            <template #default="{ row }">
              <span v-if="row.status === 'completed'">{{ row.has_issues ? '是' : '否' }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="短信通知" width="140">
            <template #default="{ row }">
              <el-tag v-if="row.sms_sent_at" type="success" size="small">已通知</el-tag>
              <el-tag v-else-if="!row.inspector_phone" type="warning" size="small">未配置手机号</el-tag>
              <el-tag v-else type="info" size="small">待发送</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button link size="small" @click="showDutyDialog(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="deleteDuty(row.id)">
                  <template #reference>
                    <el-button link size="small" type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
              <router-link v-if="row.record_id" :to="`/safety/nightshift/records/${row.record_id}`" class="link-btn">查看记录</router-link>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 检查项 -->
      <el-tab-pane label="预置检查项" name="items">
        <div v-if="!selectedCat" class="empty-hint">请在「检查分类」标签中点击「检查项」按钮选择一个分类</div>
        <template v-else>
          <div class="tab-toolbar">
            <span class="toolbar-title">{{ selectedCat.name }} - 检查项</span>
            <el-button type="primary" size="small" @click="showItemDialog()">新增检查项</el-button>
          </div>
          <el-table :data="items" stripe size="small">
            <el-table-column prop="sort_order" label="排序" width="70" />
            <el-table-column prop="name" label="检查项名称" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link size="small" @click="showItemDialog(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="deleteItem(row.id)">
                  <template #reference>
                    <el-button link size="small" type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- 排班对话框 -->
    <el-dialog v-model="dutyDialogVisible" :title="editingDuty ? '编辑排班' : '新增排班'" width="480px">
      <el-form :model="dutyForm" label-width="80px">
        <el-form-item v-if="!editingDuty" label="日期">
          <el-date-picker v-model="dutyForm.dates" type="dates" value-format="YYYY-MM-DD" placeholder="可选多个日期" style="width: 100%" />
        </el-form-item>
        <el-form-item v-else label="日期">
          <el-date-picker v-model="dutyForm.duty_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="检查人">
          <el-select v-model="dutyForm.inspector" filterable placeholder="选择检查人">
            <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name" :value="u.id">
              <span>{{ u.display_name }}</span>
              <span style="color: var(--text-muted); margin-left: 8px; font-size: 0.8em">{{ u.username }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dutyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDuty">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分类对话框 -->
    <el-dialog v-model="catDialogVisible" :title="editingCat ? '编辑分类' : '新增分类'" width="440px">
      <el-form :model="catForm" label-width="90px">
        <el-form-item label="名称"><el-input v-model="catForm.name" /></el-form-item>
        <el-form-item label="允许自填"><el-switch v-model="catForm.allows_custom" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="catForm.sort_order" :min="0" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="catForm.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="catDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCat">保存</el-button>
      </template>
    </el-dialog>

    <!-- 检查项对话框 -->
    <el-dialog v-model="itemDialogVisible" :title="editingItem ? '编辑检查项' : '新增检查项'" width="440px">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="itemForm.name" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemForm.sort_order" :min="0" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="itemForm.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftCategoryListItem, NightShiftCheckItem, NightShiftDuty } from '@/api/nightshift'
import http from '@/api/http'

const activeTab = ref('duties')
const saving = ref(false)

const categories = ref<NightShiftCategoryListItem[]>([])
const catDialogVisible = ref(false)
const editingCat = ref<NightShiftCategoryListItem | null>(null)
const catForm = ref({ name: '', allows_custom: false, sort_order: 0, is_active: true })

async function loadCategories() {
  const { data } = await nightshiftApi.getCategories()
  categories.value = data
}
function showCatDialog(cat?: NightShiftCategoryListItem) {
  editingCat.value = cat || null
  catForm.value = cat
    ? { name: cat.name, allows_custom: cat.allows_custom, sort_order: cat.sort_order, is_active: cat.is_active }
    : { name: '', allows_custom: false, sort_order: 0, is_active: true }
  catDialogVisible.value = true
}
async function saveCat() {
  saving.value = true
  try {
    if (editingCat.value) {
      await nightshiftApi.updateCategory(editingCat.value.id, catForm.value)
    } else {
      await nightshiftApi.createCategory(catForm.value)
    }
    catDialogVisible.value = false
    ElMessage.success('保存成功')
    loadCategories()
  } finally { saving.value = false }
}
async function deleteCat(id: number) {
  await nightshiftApi.deleteCategory(id)
  ElMessage.success('已删除')
  loadCategories()
}

const selectedCat = ref<NightShiftCategoryListItem | null>(null)
const items = ref<NightShiftCheckItem[]>([])
const itemDialogVisible = ref(false)
const editingItem = ref<NightShiftCheckItem | null>(null)
const itemForm = ref({ name: '', sort_order: 0, is_active: true })

function manageItems(cat: NightShiftCategoryListItem) {
  selectedCat.value = cat
  activeTab.value = 'items'
  loadItems()
}
async function loadItems() {
  if (!selectedCat.value) return
  const { data } = await nightshiftApi.getItems(selectedCat.value.id)
  items.value = data
}
function showItemDialog(item?: NightShiftCheckItem) {
  editingItem.value = item || null
  itemForm.value = item
    ? { name: item.name, sort_order: item.sort_order, is_active: item.is_active }
    : { name: '', sort_order: 0, is_active: true }
  itemDialogVisible.value = true
}
async function saveItem() {
  if (!selectedCat.value) return
  saving.value = true
  try {
    if (editingItem.value) {
      await nightshiftApi.updateItem(selectedCat.value.id, editingItem.value.id, itemForm.value)
    } else {
      await nightshiftApi.createItem(selectedCat.value.id, itemForm.value)
    }
    itemDialogVisible.value = false
    ElMessage.success('保存成功')
    loadItems()
    loadCategories()
  } finally { saving.value = false }
}
async function deleteItem(itemId: number) {
  if (!selectedCat.value) return
  await nightshiftApi.deleteItem(selectedCat.value.id, itemId)
  ElMessage.success('已删除')
  loadItems()
  loadCategories()
}

// ── Duties ───────────────────────────────────────────────────
const duties = ref<NightShiftDuty[]>([])
const dutyMonth = ref(new Date().toISOString().slice(0, 7))
const dutyDialogVisible = ref(false)
const editingDuty = ref<NightShiftDuty | null>(null)
const dutyForm = ref<{ dates: string[]; duty_date: string; inspector: number | null }>({ dates: [], duty_date: '', inspector: null })
const allUsers = ref<{ id: number; username: string; display_name: string }[]>([])

function changeMonth(delta: number) {
  const [y, m] = dutyMonth.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  dutyMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  loadDuties()
}
async function loadDuties() {
  const { data } = await nightshiftApi.getDuties({ month: dutyMonth.value })
  duties.value = data
}
async function loadAllUsers() {
  if (allUsers.value.length) return
  const { data } = await http.get('/api/users/list/')
  allUsers.value = data
}
function showDutyDialog(duty?: NightShiftDuty) {
  editingDuty.value = duty || null
  dutyForm.value = duty
    ? { dates: [], duty_date: duty.duty_date, inspector: duty.inspector }
    : { dates: [], duty_date: '', inspector: null }
  dutyDialogVisible.value = true
  loadAllUsers()
}
async function saveDuty() {
  if (!dutyForm.value.inspector) { ElMessage.warning('请选择检查人'); return }
  saving.value = true
  try {
    if (editingDuty.value) {
      await nightshiftApi.updateDuty(editingDuty.value.id, {
        duty_date: dutyForm.value.duty_date,
        inspector: dutyForm.value.inspector,
      })
    } else {
      if (!dutyForm.value.dates.length) { ElMessage.warning('请选择日期'); saving.value = false; return }
      await nightshiftApi.createDuty({ dates: dutyForm.value.dates, inspector: dutyForm.value.inspector })
    }
    dutyDialogVisible.value = false
    ElMessage.success('保存成功')
    loadDuties()
  } finally { saving.value = false }
}
async function deleteDuty(id: number) {
  await nightshiftApi.deleteDuty(id)
  ElMessage.success('已删除')
  loadDuties()
}

onMounted(() => {
  loadCategories()
  loadDuties()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; padding: 6px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-default); }
.btn-back:hover { background: var(--bg-card); }
.admin-tabs { margin-top: 16px; }
.tab-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.toolbar-title { font-weight: 600; font-size: 0.95rem; color: var(--text-primary); }
.empty-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }
.month-nav { display: flex; align-items: center; gap: 8px; }
.month-label { font-weight: 600; font-size: 0.95rem; color: var(--text-primary); min-width: 80px; text-align: center; }
.link-btn { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; }
.link-btn:hover { text-decoration: underline; }
</style>
