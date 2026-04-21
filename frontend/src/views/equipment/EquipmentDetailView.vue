<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ equipment?.name || '设备详情' }}</h2>
        <p class="page-subtitle">{{ equipment?.code }} &middot; {{ equipment?.location }}</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push(`/equipment/${equipmentId}/edit`)">编辑设备</el-button>
        <el-button @click="$router.push('/equipment')">返回列表</el-button>
      </div>
    </div>

    <!-- Equipment Info -->
    <div class="info-card" v-if="equipment">
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">设备编号</span>
          <span class="info-value data-value">{{ equipment.code }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">安装地点</span>
          <span class="info-value">{{ equipment.location }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">当前状态</span>
          <el-tag :type="statusTagType(equipment.status)" effect="dark" size="small" round>
            {{ statusLabel(equipment.status) }}
          </el-tag>
        </div>
        <div class="info-item" v-if="equipment.description">
          <span class="info-label">描述</span>
          <span class="info-value">{{ equipment.description }}</span>
        </div>
      </div>
    </div>

    <!-- Monitor Points -->
    <div class="section-header">
      <h3 class="section-title">监控点配置</h3>
      <el-button size="small" type="primary" @click="showAddPoint = true">添加监控点</el-button>
    </div>

    <div class="points-grid" v-if="equipment?.monitor_points?.length">
      <div v-for="point in equipment.monitor_points" :key="point.id" class="point-card">
        <div class="point-header">
          <div class="point-type-badge" :class="point.param_type">
            {{ paramTypeLabel(point.param_type) }}
          </div>
          <div class="point-actions">
            <el-button link size="small" @click="openDrawer(point)">详情</el-button>
            <el-button link type="danger" size="small" @click="deletePoint(point.id)">删除</el-button>
          </div>
        </div>
        <div class="point-name">{{ point.name }}</div>
        <div class="point-meta">
          <span>标识: <code>{{ point.param_key }}</code></span>
          <span>单位: {{ point.unit }}</span>
        </div>
        <div class="point-thresholds" v-if="point.threshold">
          <div class="th-row">
            <span class="th-label warning">预警</span>
            <span class="th-values data-value">
              {{ point.threshold.warning_low ?? '--' }} ~ {{ point.threshold.warning_high ?? '--' }}
            </span>
          </div>
          <div class="th-row">
            <span class="th-label alarm">报警</span>
            <span class="th-values data-value">
              {{ point.threshold.alarm_low ?? '--' }} ~ {{ point.threshold.alarm_high ?? '--' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>暂无监控点，请添加</p>
    </div>

    <!-- Add Monitor Point Dialog -->
    <el-dialog v-model="showAddPoint" title="添加监控点" width="520px" :close-on-click-modal="false">
      <el-form :model="pointForm" label-width="90px" label-position="left">
        <el-form-item label="名称" required>
          <el-input v-model="pointForm.name" placeholder="如：主轴温度" />
        </el-form-item>
        <el-form-item label="参数标识" required>
          <el-input v-model="pointForm.param_key" placeholder="如：temperature_main" />
        </el-form-item>
        <el-form-item label="参数类型" required>
          <el-select v-model="pointForm.param_type" style="width: 100%">
            <el-option label="温度" value="temperature" />
            <el-option label="电流" value="current" />
            <el-option label="振动" value="vibration" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位" required>
          <el-input v-model="pointForm.unit" placeholder="如：℃、A、mm/s" />
        </el-form-item>
        <el-divider content-position="left">阈值配置</el-divider>
        <div class="threshold-form-grid">
          <el-form-item label="预警下限">
            <el-input-number v-model="pointForm.warning_low" :precision="1" controls-position="right" style="width:100%" />
          </el-form-item>
          <el-form-item label="预警上限">
            <el-input-number v-model="pointForm.warning_high" :precision="1" controls-position="right" style="width:100%" />
          </el-form-item>
          <el-form-item label="报警下限">
            <el-input-number v-model="pointForm.alarm_low" :precision="1" controls-position="right" style="width:100%" />
          </el-form-item>
          <el-form-item label="报警上限">
            <el-input-number v-model="pointForm.alarm_high" :precision="1" controls-position="right" style="width:100%" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAddPoint = false">取消</el-button>
        <el-button type="primary" :loading="pointSubmitting" @click="submitPoint">添加</el-button>
      </template>
    </el-dialog>

  <MonitorPointDrawer
    v-model="showDrawer"
    :point="drawerPoint"
    @saved="fetchEquipment"
  />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { equipmentApi, monitorPointApi } from '@/api/equipment'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Equipment } from '@/types'
import MonitorPointDrawer from '@/components/equipment/MonitorPointDrawer.vue'
import type { MonitorPoint } from '@/types'

const route = useRoute()
const router = useRouter()
const equipmentId = Number(route.params.id)
const equipment = ref<Equipment | null>(null)
const showAddPoint = ref(false)
const showDrawer = ref(false)
const drawerPoint = ref<MonitorPoint | null>(null)

function openDrawer(point: MonitorPoint) {
  drawerPoint.value = point
  showDrawer.value = true
}
const pointSubmitting = ref(false)

const pointForm = ref({
  name: '',
  param_key: '',
  param_type: 'temperature',
  unit: '℃',
  warning_high: null as number | null,
  warning_low: null as number | null,
  alarm_high: null as number | null,
  alarm_low: null as number | null,
})

function statusTagType(s: string) {
  return { running: 'success', stopped: 'info', fault: 'danger' }[s] || 'info'
}

function statusLabel(s: string) {
  return { running: '运行中', stopped: '停机', fault: '故障' }[s] || s
}

function paramTypeLabel(t: string) {
  return { temperature: '温度', current: '电流', vibration: '振动' }[t] || t
}

async function fetchEquipment() {
  try {
    const { data } = await equipmentApi.get(equipmentId)
    equipment.value = data
  } catch {
    ElMessage.error('加载失败')
    router.push('/equipment')
  }
}

async function submitPoint() {
  if (!pointForm.value.name || !pointForm.value.param_key) {
    ElMessage.warning('请填写必填项')
    return
  }
  pointSubmitting.value = true
  try {
    await monitorPointApi.create({
      equipment: equipmentId,
      ...pointForm.value,
    })
    ElMessage.success('监控点添加成功')
    showAddPoint.value = false
    pointForm.value = { name: '', param_key: '', param_type: 'temperature', unit: '℃', warning_high: null, warning_low: null, alarm_high: null, alarm_low: null }
    fetchEquipment()
  } catch (err: any) {
    const msg = err.response?.data?.param_key?.[0] || err.response?.data?.detail || '添加失败'
    ElMessage.error(msg)
  } finally {
    pointSubmitting.value = false
  }
}

async function deletePoint(pointId: number) {
  try {
    await ElMessageBox.confirm('确定删除该监控点？', '确认', { type: 'warning' })
  } catch {
    return // 用户取消
  }
  try {
    await monitorPointApi.delete(pointId)
    ElMessage.success('已删除')
    fetchEquipment()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchEquipment)
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 8px;
}

.info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 24px;
  margin-bottom: 28px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.info-value {
  color: var(--text-primary);
  font-size: 0.95rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.points-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.point-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px;
  transition: border-color var(--transition-fast);
}

.point-card:hover {
  border-color: var(--border-default);
}

.point-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.point-type-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.point-type-badge.temperature { background: var(--color-warning-dim); color: var(--color-warning); }
.point-type-badge.current { background: var(--color-info-dim); color: var(--color-info); }
.point-type-badge.vibration { background: var(--color-healthy-dim); color: var(--color-healthy); }

.point-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.point-meta {
  display: flex;
  gap: 16px;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.point-meta code {
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.point-thresholds {
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.th-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.th-label {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  min-width: 36px;
  text-align: center;
}

.th-label.warning { background: var(--color-warning-dim); color: var(--color-warning); }
.th-label.alarm { background: var(--color-alarm-dim); color: var(--color-alarm); }

.th-values {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--text-muted);
  background: var(--bg-card);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
}

.threshold-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.point-actions {
  display: flex;
  gap: 4px;
}

@media (max-width: 960px) {
  .header-actions,
  .section-header {
    flex-wrap: wrap;
  }

  .info-card {
    padding: 18px;
    margin-bottom: 20px;
  }

  .info-grid {
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .points-grid {
    grid-template-columns: 1fr;
  }

  .threshold-form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

@media (max-width: 640px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .point-header,
  .point-meta,
  .th-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .point-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .empty-state {
    padding: 28px 16px;
  }
}
</style>
