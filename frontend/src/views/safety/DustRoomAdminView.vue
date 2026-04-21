<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">除尘房管理</h2>
        <p class="page-subtitle">配置除尘房、巡检模板、检查项和巡检人员</p>
      </div>
      <router-link to="/safety/dustroom" class="btn-back">← 返回巡检</router-link>
    </div>

    <el-tabs v-model="activeTab" class="admin-tabs">
      <!-- Tab 1: 除尘房管理 -->
      <el-tab-pane label="除尘房" name="rooms">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="showRoomDialog()">新增除尘房</el-button>
        </div>
        <el-table :data="rooms" stripe size="small">
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="code" label="编号" width="120" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button link size="small" @click="showRoomDialog(row)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="deleteRoom(row.id)">
                <template #reference>
                  <el-button link size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 巡检模板 -->
      <el-tab-pane label="巡检模板" name="templates">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="showTemplateDialog()">新增模板</el-button>
        </div>
        <el-table :data="templates" stripe size="small">
          <el-table-column prop="name" label="模板名称" />
          <el-table-column prop="role_display" label="角色" width="120" />
          <el-table-column label="频次" width="100">
            <template #default="{ row }">{{ freqMap[row.frequency] || row.frequency }}</template>
          </el-table-column>
          <el-table-column prop="items_count" label="检查项数" width="100" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button link size="small" @click="showTemplateDialog(row)">编辑</el-button>
              <el-button link size="small" type="primary" @click="manageItems(row)">检查项</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 检查项（选中模板后展示） -->
      <el-tab-pane label="检查项配置" name="items">
        <div v-if="!selectedTemplate" class="empty-hint">
          请先在「巡检模板」标签中点击「检查项」按钮选择一个模板
        </div>
        <template v-else>
          <div class="tab-toolbar">
            <span class="toolbar-title">{{ selectedTemplate.name }} - 检查项</span>
            <el-button type="primary" size="small" @click="showItemDialog()">新增检查项</el-button>
          </div>
          <el-table :data="items" stripe size="small">
            <el-table-column prop="sort_order" label="排序" width="70" />
            <el-table-column prop="name" label="检查项名称" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">{{ typeMap[row.item_type] || row.item_type }}</template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column label="必填" width="70">
              <template #default="{ row }">{{ row.required ? '是' : '否' }}</template>
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

      <!-- Tab 4: 巡检人员 -->
      <el-tab-pane label="巡检人员" name="inspectors">
        <div class="tab-toolbar">
          <el-button type="primary" size="small" @click="showInspectorDialog()">分配人员</el-button>
        </div>
        <el-table :data="inspectors" stripe size="small">
          <el-table-column label="姓名">
            <template #default="{ row }">{{ row.user_display.display_name }}</template>
          </el-table-column>
          <el-table-column label="用户名" width="120">
            <template #default="{ row }">{{ row.user_display.username }}</template>
          </el-table-column>
          <el-table-column prop="role_display" label="巡检角色" width="120" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-popconfirm title="确定移除？" @confirm="removeInspector(row.id)">
                <template #reference>
                  <el-button link size="small" type="danger">移除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 除尘房对话框 -->
    <el-dialog v-model="roomDialogVisible" :title="editingRoom ? '编辑除尘房' : '新增除尘房'" width="480px">
      <el-form :model="roomForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="roomForm.name" /></el-form-item>
        <el-form-item label="编号"><el-input v-model="roomForm.code" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="roomForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="roomForm.sort_order" :min="0" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="roomForm.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roomDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRoom">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模板对话框 -->
    <el-dialog v-model="templateDialogVisible" :title="editingTemplate ? '编辑模板' : '新增模板'" width="480px">
      <el-form :model="templateForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="templateForm.name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="templateForm.role" :disabled="!!editingTemplate">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="频次">
          <el-select v-model="templateForm.frequency">
            <el-option v-for="f in freqOptions" :key="f.value" :label="f.label" :value="f.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="templateForm.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="templateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 检查项对话框 -->
    <el-dialog v-model="itemDialogVisible" :title="editingItem ? '编辑检查项' : '新增检查项'" width="520px">
      <el-form :model="itemForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="itemForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="itemForm.item_type">
            <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="itemForm.item_type === 'number'" label="单位">
          <el-input v-model="itemForm.unit" placeholder="如 ℃、mm/s" />
        </el-form-item>
        <el-form-item v-if="itemForm.item_type === 'select'" label="选项">
          <el-input v-model="itemForm.optionsText" type="textarea" :rows="2" placeholder="每行一个选项" />
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemForm.sort_order" :min="0" /></el-form-item>
        <el-form-item label="必填"><el-switch v-model="itemForm.required" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配人员对话框 -->
    <el-dialog v-model="inspectorDialogVisible" title="分配巡检人员" width="480px">
      <el-form :model="inspectorForm" label-width="80px">
        <el-form-item label="用户">
          <el-select v-model="inspectorForm.user" filterable placeholder="搜索用户">
            <el-option v-for="u in allUsers" :key="u.id" :label="u.display_name" :value="u.id">
              <span>{{ u.display_name }}</span>
              <span style="color: var(--text-muted); margin-left: 8px; font-size: 0.8em">{{ u.username }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="inspectorForm.role">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inspectorDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveInspector">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dustroomApi } from '@/api/dustroom'
import type { DustRoom, InspectionTemplateListItem, InspectionItem, DustRoomInspector as InspectorType } from '@/api/dustroom'
import http from '@/api/http'

const activeTab = ref('rooms')
const saving = ref(false)

const roleOptions = [
  { value: 'electrical', label: '电气修理工' },
  { value: 'mechanical', label: '机械修理工' },
  { value: 'operator', label: '操作工' },
  { value: 'safety', label: '安全员' },
]
const freqOptions = [
  { value: 'daily', label: '每天' },
  { value: 'per_shift', label: '每班次' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
]
const freqMap: Record<string, string> = { daily: '每天', per_shift: '每班次', weekly: '每周', monthly: '每月' }
const typeOptions = [
  { value: 'checkbox', label: '正常/异常' },
  { value: 'number', label: '数值' },
  { value: 'text', label: '文本' },
  { value: 'select', label: '选择' },
]
const typeMap: Record<string, string> = { checkbox: '正常/异常', number: '数值', text: '文本', select: '选择' }

// ── Rooms ────────────────────────────────────────────────────
const rooms = ref<DustRoom[]>([])
const roomDialogVisible = ref(false)
const editingRoom = ref<DustRoom | null>(null)
const roomForm = ref({ name: '', code: '', description: '', sort_order: 0, is_active: true })

async function loadRooms() {
  const { data } = await dustroomApi.getRooms()
  rooms.value = data
}
function showRoomDialog(room?: DustRoom) {
  editingRoom.value = room || null
  roomForm.value = room
    ? { ...room }
    : { name: '', code: '', description: '', sort_order: 0, is_active: true }
  roomDialogVisible.value = true
}
async function saveRoom() {
  saving.value = true
  try {
    if (editingRoom.value) {
      await dustroomApi.updateRoom(editingRoom.value.id, roomForm.value)
    } else {
      await dustroomApi.createRoom(roomForm.value)
    }
    roomDialogVisible.value = false
    ElMessage.success('保存成功')
    loadRooms()
  } finally { saving.value = false }
}
async function deleteRoom(id: number) {
  await dustroomApi.deleteRoom(id)
  ElMessage.success('已删除')
  loadRooms()
}

// ── Templates ────────────────────────────────────────────────
const templates = ref<InspectionTemplateListItem[]>([])
const templateDialogVisible = ref(false)
const editingTemplate = ref<InspectionTemplateListItem | null>(null)
const templateForm = ref({ name: '', role: 'electrical', frequency: 'daily', is_active: true })

async function loadTemplates() {
  const { data } = await dustroomApi.getTemplates()
  templates.value = data
}
function showTemplateDialog(tpl?: InspectionTemplateListItem) {
  editingTemplate.value = tpl || null
  templateForm.value = tpl
    ? { name: tpl.name, role: tpl.role, frequency: tpl.frequency, is_active: tpl.is_active }
    : { name: '', role: 'electrical', frequency: 'daily', is_active: true }
  templateDialogVisible.value = true
}
async function saveTemplate() {
  saving.value = true
  try {
    if (editingTemplate.value) {
      await dustroomApi.updateTemplate(editingTemplate.value.id, templateForm.value)
    } else {
      await dustroomApi.createTemplate(templateForm.value)
    }
    templateDialogVisible.value = false
    ElMessage.success('保存成功')
    loadTemplates()
  } finally { saving.value = false }
}

// ── Items ────────────────────────────────────────────────────
const selectedTemplate = ref<InspectionTemplateListItem | null>(null)
const items = ref<InspectionItem[]>([])
const itemDialogVisible = ref(false)
const editingItem = ref<InspectionItem | null>(null)
const itemForm = ref({ name: '', item_type: 'checkbox', unit: '', optionsText: '', sort_order: 0, required: true })

function manageItems(tpl: InspectionTemplateListItem) {
  selectedTemplate.value = tpl
  activeTab.value = 'items'
  loadItems()
}
async function loadItems() {
  if (!selectedTemplate.value) return
  const { data } = await dustroomApi.getItems(selectedTemplate.value.id)
  items.value = data
}
function showItemDialog(item?: InspectionItem) {
  editingItem.value = item || null
  itemForm.value = item
    ? { name: item.name, item_type: item.item_type, unit: item.unit, optionsText: (item.options || []).join('\n'), sort_order: item.sort_order, required: item.required }
    : { name: '', item_type: 'checkbox', unit: '', optionsText: '', sort_order: 0, required: true }
  itemDialogVisible.value = true
}
async function saveItem() {
  if (!selectedTemplate.value) return
  saving.value = true
  const payload: any = {
    name: itemForm.value.name,
    item_type: itemForm.value.item_type,
    unit: itemForm.value.unit,
    options: itemForm.value.item_type === 'select'
      ? itemForm.value.optionsText.split('\n').map(s => s.trim()).filter(Boolean)
      : [],
    sort_order: itemForm.value.sort_order,
    required: itemForm.value.required,
  }
  try {
    if (editingItem.value) {
      await dustroomApi.updateItem(selectedTemplate.value.id, editingItem.value.id, payload)
    } else {
      await dustroomApi.createItem(selectedTemplate.value.id, payload)
    }
    itemDialogVisible.value = false
    ElMessage.success('保存成功')
    loadItems()
    loadTemplates()
  } finally { saving.value = false }
}
async function deleteItem(itemId: number) {
  if (!selectedTemplate.value) return
  await dustroomApi.deleteItem(selectedTemplate.value.id, itemId)
  ElMessage.success('已删除')
  loadItems()
  loadTemplates()
}

// ── Inspectors ───────────────────────────────────────────────
const inspectors = ref<InspectorType[]>([])
const inspectorDialogVisible = ref(false)
const inspectorForm = ref({ user: null as number | null, role: 'electrical' })
const allUsers = ref<{ id: number; username: string; display_name: string }[]>([])

async function loadInspectors() {
  const { data } = await dustroomApi.getInspectors()
  inspectors.value = data
}
async function loadAllUsers() {
  const { data } = await http.get('/api/users/list/')
  allUsers.value = data
}
function showInspectorDialog() {
  inspectorForm.value = { user: null, role: 'electrical' }
  inspectorDialogVisible.value = true
  if (!allUsers.value.length) loadAllUsers()
}
async function saveInspector() {
  if (!inspectorForm.value.user) {
    ElMessage.warning('请选择用户')
    return
  }
  saving.value = true
  try {
    await dustroomApi.addInspector({ user: inspectorForm.value.user, role: inspectorForm.value.role })
    inspectorDialogVisible.value = false
    ElMessage.success('分配成功')
    loadInspectors()
  } finally { saving.value = false }
}
async function removeInspector(id: number) {
  await dustroomApi.removeInspector(id)
  ElMessage.success('已移除')
  loadInspectors()
}

onMounted(() => {
  loadRooms()
  loadTemplates()
  loadInspectors()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.btn-back {
  color: var(--color-accent);
  text-decoration: none;
  font-size: 0.85rem;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}
.btn-back:hover { background: var(--bg-card); }
.admin-tabs { margin-top: 16px; }
.tab-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.toolbar-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-primary);
}
.empty-hint {
  text-align: center;
  padding: 48px 0;
  color: var(--text-muted);
}
</style>
