<template>
  <el-drawer
    v-model="visible"
    :title="point?.name || '监控点详情'"
    size="480px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-tabs v-model="activeTab">
      <!-- Tab 1: 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <el-form :model="infoForm" label-width="90px" label-position="left" style="margin-top:8px">
          <el-form-item label="名称" required>
            <el-input v-model="infoForm.name" />
          </el-form-item>
          <el-form-item label="参数标识" required>
            <el-input v-model="infoForm.param_key" />
          </el-form-item>
          <el-form-item label="参数类型" required>
            <el-select v-model="infoForm.param_type" style="width:100%">
              <el-option label="温度" value="temperature" />
              <el-option label="电流" value="current" />
              <el-option label="振动" value="vibration" />
            </el-select>
          </el-form-item>
          <el-form-item label="单位" required>
            <el-input v-model="infoForm.unit" />
          </el-form-item>
          <el-divider content-position="left">阈值配置</el-divider>
          <div class="threshold-grid">
            <el-form-item label="预警下限">
              <el-input-number v-model="infoForm.warning_low" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item label="预警上限">
              <el-input-number v-model="infoForm.warning_high" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item label="报警下限">
              <el-input-number v-model="infoForm.alarm_low" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item label="报警上限">
              <el-input-number v-model="infoForm.alarm_high" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </div>
          <div class="drawer-footer">
            <el-button type="primary" :loading="infoSaving" @click="saveInfo">保存基本信息</el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <!-- Tab 2: 采集接口 -->
      <el-tab-pane label="采集接口" name="collection">
        <div style="margin-top:8px">
          <div class="collection-header">
            <span class="collection-status-label">接口状态</span>
            <el-switch v-model="collectionForm.is_active" active-text="启用" inactive-text="停用" />
          </div>

          <el-form :model="collectionForm" label-width="90px" label-position="left" style="margin-top:16px">
            <el-form-item label="协议类型">
              <el-radio-group v-model="collectionForm.interface_type">
                <el-radio-button value="http">HTTP</el-radio-button>
                <el-radio-button value="mqtt">MQTT</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <!-- HTTP 表单 -->
            <template v-if="collectionForm.interface_type === 'http'">
              <el-form-item label="请求 URL" required>
                <el-input v-model="httpConfig.url" placeholder="http://..." />
              </el-form-item>
              <el-form-item label="请求方法">
                <el-select v-model="httpConfig.method" style="width:100%">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                </el-select>
              </el-form-item>
              <el-form-item label="数据路径">
                <el-input v-model="httpConfig.data_path" placeholder="如：data.value" />
              </el-form-item>
              <el-form-item label="认证类型">
                <el-select v-model="httpConfig.auth_type" style="width:100%">
                  <el-option label="无认证" value="none" />
                  <el-option label="API Key" value="api_key" />
                  <el-option label="Basic Auth" value="basic" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="httpConfig.auth_type !== 'none'" label="认证值">
                <el-input v-model="httpConfig.auth_value" placeholder="Token 或 user:password" />
              </el-form-item>
              <el-form-item label="轮询间隔">
                <el-input-number v-model="collectionForm.polling_interval" :min="5" :max="3600" controls-position="right" style="width:100%" />
                <span style="margin-left:8px;font-size:0.8rem;color:var(--text-muted)">秒</span>
              </el-form-item>
            </template>

            <!-- MQTT 表单 -->
            <template v-if="collectionForm.interface_type === 'mqtt'">
              <el-form-item label="Broker" required>
                <el-input v-model="mqttConfig.broker" placeholder="mqtt://192.168.1.100:1883" />
              </el-form-item>
              <el-form-item label="Topic" required>
                <el-input v-model="mqttConfig.topic" placeholder="sensors/device/value" />
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="mqttConfig.username" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="mqttConfig.password" type="password" show-password />
              </el-form-item>
              <el-form-item label="数据路径">
                <el-input v-model="mqttConfig.data_path" placeholder="如：value" />
              </el-form-item>
            </template>

            <div class="drawer-footer">
              <el-button
                v-if="hasCollection"
                type="danger"
                plain
                :loading="collectionDeleting"
                @click="deleteCollection"
              >删除采集接口</el-button>
              <el-button type="primary" :loading="collectionSaving" @click="saveCollection">保存采集接口</el-button>
            </div>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { monitorPointApi } from '@/api/equipment'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { MonitorPoint, HttpConfig, MqttConfig } from '@/types'

const props = defineProps<{ modelValue: boolean; point: MonitorPoint | null }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; saved: [] }>()

const visible = ref(false)
const activeTab = ref('info')
const infoSaving = ref(false)
const collectionSaving = ref(false)
const collectionDeleting = ref(false)
const hasCollection = ref(false)

const infoForm = ref({
  name: '',
  param_key: '',
  param_type: 'temperature' as 'temperature' | 'current' | 'vibration',
  unit: '',
  warning_high: null as number | null,
  warning_low: null as number | null,
  alarm_high: null as number | null,
  alarm_low: null as number | null,
})

const collectionForm = ref({
  interface_type: 'http' as 'http' | 'mqtt',
  polling_interval: 60,
  is_active: true,
})

const httpConfig = ref<HttpConfig>({
  url: '', method: 'GET', headers: {}, data_path: '', auth_type: 'none', auth_value: '',
})

const mqttConfig = ref<MqttConfig>({
  broker: '', topic: '', username: '', password: '', data_path: '',
})

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.point) loadPoint()
})

watch(() => props.point, (val) => {
  if (val && visible.value) loadPoint()
})

watch(visible, (val) => {
  if (!val) emit('update:modelValue', false)
})

function loadPoint() {
  const p = props.point!
  infoForm.value = {
    name: p.name,
    param_key: p.param_key,
    param_type: p.param_type,
    unit: p.unit,
    warning_high: p.threshold?.warning_high ?? null,
    warning_low: p.threshold?.warning_low ?? null,
    alarm_high: p.threshold?.alarm_high ?? null,
    alarm_low: p.threshold?.alarm_low ?? null,
  }
  if (p.collection) {
    hasCollection.value = true
    collectionForm.value.interface_type = p.collection.interface_type
    collectionForm.value.polling_interval = p.collection.polling_interval
    collectionForm.value.is_active = p.collection.is_active
    if (p.collection.interface_type === 'http') {
      httpConfig.value = { ...{ url: '', method: 'GET', headers: {}, data_path: '', auth_type: 'none', auth_value: '' }, ...(p.collection.config as HttpConfig) }
    } else {
      mqttConfig.value = { ...{ broker: '', topic: '', username: '', password: '', data_path: '' }, ...(p.collection.config as MqttConfig) }
    }
  } else {
    hasCollection.value = false
    httpConfig.value = { url: '', method: 'GET', headers: {}, data_path: '', auth_type: 'none', auth_value: '' }
    mqttConfig.value = { broker: '', topic: '', username: '', password: '', data_path: '' }
  }
}

async function saveInfo() {
  if (!infoForm.value.name || !infoForm.value.param_key) {
    ElMessage.warning('请填写名称和参数标识')
    return
  }
  infoSaving.value = true
  try {
    // 后端 MonitorPointViewSet.update 使用 MonitorPointCreateSerializer，
    // 其 update() 方法已处理 warning_high/low、alarm_high/low，会同步更新 ThresholdRule。
    await monitorPointApi.update(props.point!.id, {
      equipment: props.point!.equipment,
      ...infoForm.value,
    })
    ElMessage.success('保存成功')
    emit('saved')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    infoSaving.value = false
  }
}

async function saveCollection() {
  const config = collectionForm.value.interface_type === 'http' ? httpConfig.value : mqttConfig.value
  collectionSaving.value = true
  try {
    await monitorPointApi.saveCollection(props.point!.id, {
      ...collectionForm.value,
      config,
    })
    hasCollection.value = true
    ElMessage.success('采集接口已保存')
    emit('saved')
  } catch (err: any) {
    const msg = err.response?.data?.config || err.response?.data?.detail || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    collectionSaving.value = false
  }
}

async function deleteCollection() {
  try {
    await ElMessageBox.confirm('确定删除采集接口配置？', '确认', { type: 'warning' })
  } catch {
    return // 用户取消
  }
  collectionDeleting.value = true
  try {
    await monitorPointApi.deleteCollection(props.point!.id)
    hasCollection.value = false
    ElMessage.success('已删除')
    emit('saved')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    collectionDeleting.value = false
  }
}

function handleClose() {
  activeTab.value = 'info'
}
</script>

<style scoped>
.threshold-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.collection-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 4px;
}

.collection-status-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}
</style>
