# 监控点位增删改 + 采集接口配置 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在设备详情页实现监控点位完整增删改 UI，并支持为每个监控点配置 HTTP / MQTT 采集接口（配置存储，执行逻辑不在本次范围）。

**Architecture:** 后端新增 `CollectionInterface` 模型（OneToOne MonitorPoint），通过 `@action` 挂载在 `MonitorPointViewSet` 上提供 CRUD 端点；前端新增 `MonitorPointDrawer` 组件（480px 抽屉，两个 Tab：基本信息编辑 + 采集接口配置），设备详情页监控点卡片增加「详情」按钮触发抽屉。

**Tech Stack:** Django 4.2 + DRF, Vue 3 + TypeScript + Element Plus, PostgreSQL

---

## Chunk 1: 后端 — CollectionInterface 模型 + 迁移

### Task 1: 新增 CollectionInterface 模型

**Files:**
- Modify: `backend/apps/equipment/models.py`

- [ ] **Step 1: 在 models.py 末尾追加 CollectionInterface 类**

```python
class CollectionInterface(models.Model):
    INTERFACE_TYPES = [('http', 'HTTP'), ('mqtt', 'MQTT')]

    monitor_point = models.OneToOneField(
        MonitorPoint, on_delete=models.CASCADE, related_name='collection'
    )
    interface_type = models.CharField('接口类型', max_length=10, choices=INTERFACE_TYPES)
    config = models.JSONField('配置参数', default=dict)
    polling_interval = models.IntegerField('轮询间隔(秒)', default=60)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '采集接口'
        verbose_name_plural = '采集接口'

    def __str__(self):
        return f"{self.monitor_point.name} - {self.interface_type}"
```

- [ ] **Step 2: 生成并执行迁移**

```bash
cd "F:/zs2 Management System/backend"
python manage.py makemigrations equipment
python manage.py migrate
```

期望输出：`Applying equipment.0002_collectioninterface... OK`

- [ ] **Step 3: 验证表已创建**

```bash
python manage.py shell -c "from apps.equipment.models import CollectionInterface; print('OK', CollectionInterface._meta.db_table)"
```

期望输出：`OK equipment_collectioninterface`

- [ ] **Step 4: Commit**

```bash
git add backend/apps/equipment/models.py backend/apps/equipment/migrations/
git commit -m "feat: add CollectionInterface model"
```

---

## Chunk 2: 后端 — 序列化器 + API 端点

### Task 2: 新增 CollectionInterface 序列化器

**Files:**
- Modify: `backend/apps/equipment/serializers.py`

- [ ] **Step 1: 在 serializers.py 顶部 import 新模型**

在 `from .models import Equipment, MonitorPoint` 这行改为：

```python
from .models import Equipment, MonitorPoint, CollectionInterface
```

- [ ] **Step 2: 新增 CollectionInterfaceSerializer**

在 `ThresholdRuleInlineSerializer` 之后插入：

```python
class CollectionInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionInterface
        fields = ['id', 'interface_type', 'config', 'polling_interval', 'is_active', 'updated_at']

    def validate(self, data):
        itype = data.get('interface_type', getattr(self.instance, 'interface_type', None))
        config = data.get('config', getattr(self.instance, 'config', {}))
        if itype == 'http' and not config.get('url'):
            raise serializers.ValidationError({'config': 'HTTP 接口必须填写 url'})
        if itype == 'mqtt' and (not config.get('broker') or not config.get('topic')):
            raise serializers.ValidationError({'config': 'MQTT 接口必须填写 broker 和 topic'})
        return data
```

- [ ] **Step 3: 在 MonitorPointSerializer 中嵌套 collection（只读）**

将 `MonitorPointSerializer` 改为：

```python
class MonitorPointSerializer(serializers.ModelSerializer):
    threshold = ThresholdRuleInlineSerializer(read_only=True)
    collection = CollectionInterfaceSerializer(read_only=True)

    class Meta:
        model = MonitorPoint
        fields = ['id', 'equipment', 'name', 'param_key', 'unit', 'param_type', 'threshold', 'collection']
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/equipment/serializers.py
git commit -m "feat: add CollectionInterfaceSerializer, nest collection in MonitorPointSerializer"
```

---

### Task 3: 新增采集接口 @action 端点

**Files:**
- Modify: `backend/apps/equipment/views.py`

- [ ] **Step 1: 更新 import**

`MonitorPointCreateSerializer` 已存在于 `serializers.py`（现有代码），只需追加新增的两个：

将 views.py 顶部 import 改为：

```python
from .models import Equipment, MonitorPoint, CollectionInterface
from .serializers import (
    EquipmentListSerializer,
    EquipmentDetailSerializer,
    MonitorPointSerializer,
    MonitorPointCreateSerializer,
    CollectionInterfaceSerializer,
)
```

- [ ] **Step 2: 在 MonitorPointViewSet 中新增 collection action**

在 `get_queryset` 方法之后追加：

```python
    @action(detail=True, methods=['get', 'post', 'put', 'delete'], url_path='collection')
    def collection(self, request, pk=None):
        point = self.get_object()

        if request.method == 'GET':
            try:
                serializer = CollectionInterfaceSerializer(point.collection)
                return Response(serializer.data)
            except CollectionInterface.DoesNotExist:
                return Response(None)

        if request.method == 'DELETE':
            try:
                point.collection.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except CollectionInterface.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        # POST (create) or PUT (update)
        try:
            instance = point.collection
            serializer = CollectionInterfaceSerializer(instance, data=request.data)
        except CollectionInterface.DoesNotExist:
            serializer = CollectionInterfaceSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(monitor_point=point)
        return Response(serializer.data)
```

- [ ] **Step 3: 手动测试端点可访问**

启动 daphne 后用 curl 验证（假设已有 monitor_point id=1）：

```bash
curl -s http://127.0.0.1:8000/api/equipment/monitor-points/1/collection/
```

期望：返回 `null` 或已有配置的 JSON，不报 404/500。

- [ ] **Step 4: 验证 EquipmentDetailSerializer 响应包含 collection 字段**

`EquipmentDetailSerializer` → `MonitorPointSerializer`（已在 Task 2 Step 3 更新，嵌套了 `collection`）。
验证命令：

```bash
curl -s http://127.0.0.1:8000/api/equipment/equipments/1/ | python -m json.tool | grep -A2 collection
```

期望：`monitor_points` 数组中每个对象包含 `"collection": null` 或配置对象。

- [ ] **Step 5: Commit**

```bash
git add backend/apps/equipment/views.py
git commit -m "feat: add collection @action on MonitorPointViewSet"
```

> **Note on HTTP method:** `saveCollection` in the frontend always sends PUT. The backend `@action` handles both POST and PUT identically (upsert logic), so this is intentional — no need to track create vs update state on the frontend.

---

## Chunk 3: 前端 — 类型定义 + API 客户端

### Task 4: 扩展类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 在 MonitorPoint interface 中加 collection 字段**

将：
```typescript
export interface MonitorPoint {
  id: number
  equipment: number
  name: string
  param_key: string
  unit: string
  param_type: 'temperature' | 'current' | 'vibration'
  threshold?: ThresholdRule
}
```

改为：
```typescript
export interface MonitorPoint {
  id: number
  equipment: number
  name: string
  param_key: string
  unit: string
  param_type: 'temperature' | 'current' | 'vibration'
  threshold?: ThresholdRule
  collection?: CollectionInterface | null
}
```

- [ ] **Step 2: 在文件末尾追加采集接口类型**

```typescript
export interface HttpConfig {
  url: string
  method: 'GET' | 'POST'
  headers: Record<string, string>
  data_path: string
  auth_type: 'none' | 'api_key' | 'basic'
  auth_value: string
}

export interface MqttConfig {
  broker: string
  topic: string
  username: string
  password: string
  data_path: string
}

export interface CollectionInterface {
  id?: number
  interface_type: 'http' | 'mqtt'
  config: HttpConfig | MqttConfig
  polling_interval: number
  is_active: boolean
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add CollectionInterface types"
```

---

### Task 5: 扩展 API 客户端

**Files:**
- Modify: `frontend/src/api/equipment.ts`

- [ ] **Step 1: 更新 import，加入 CollectionInterface 类型**

将第一行改为：
```typescript
import http from './http'
import type { Equipment, MonitorPoint, CollectionInterface, PaginatedResponse } from '@/types'
```

- [ ] **Step 2: 在 monitorPointApi 中追加三个方法**

```typescript
  getCollection(id: number) {
    return http.get<CollectionInterface | null>(`/api/equipment/monitor-points/${id}/collection/`)
  },
  saveCollection(id: number, data: Omit<CollectionInterface, 'id'>) {
    return http.put<CollectionInterface>(`/api/equipment/monitor-points/${id}/collection/`, data)
  },
  deleteCollection(id: number) {
    return http.delete(`/api/equipment/monitor-points/${id}/collection/`)
  },
```

注意：`saveCollection` 统一用 PUT，后端 action 已处理"有则更新，无则创建"逻辑。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/equipment.ts
git commit -m "feat: add collection API methods to monitorPointApi"
```

---

## Chunk 4: 前端 — MonitorPointDrawer 组件

### Task 6: 新建 MonitorPointDrawer 组件

**Files:**
- Create: `frontend/src/components/equipment/MonitorPointDrawer.vue`

- [ ] **Step 1: 创建组件文件，写入完整内容**

```vue
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
  }
}

async function saveInfo() {
  if (!infoForm.value.name || !infoForm.value.param_key) {
    ElMessage.warning('请填写名称和参数标识')
    return
  }
  infoSaving.value = true
  try {
    // 注意：后端 MonitorPointViewSet.update 使用 MonitorPointCreateSerializer，
    // 该序列化器的 update() 方法已处理 warning_high/low、alarm_high/low 字段，
    // 会同步更新关联的 ThresholdRule 记录。
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/equipment/MonitorPointDrawer.vue
git commit -m "feat: add MonitorPointDrawer component"
```

---

## Chunk 5: 前端 — EquipmentDetailView 集成

### Task 7: 在设备详情页集成抽屉

**Files:**
- Modify: `frontend/src/views/equipment/EquipmentDetailView.vue`

- [ ] **Step 1: 在 `<script setup>` 中 import 抽屉组件和新类型**

在现有 import 区域追加：
```typescript
import MonitorPointDrawer from '@/components/equipment/MonitorPointDrawer.vue'
import type { MonitorPoint } from '@/types'
```

- [ ] **Step 2: 新增抽屉状态变量**

在 `const showAddPoint = ref(false)` 之后追加：
```typescript
const showDrawer = ref(false)
const drawerPoint = ref<MonitorPoint | null>(null)

function openDrawer(point: MonitorPoint) {
  drawerPoint.value = point
  showDrawer.value = true
}
```

- [ ] **Step 3: 在监控点卡片 `.point-header` 中加「详情」按钮**

将：
```html
<div class="point-header">
  <div class="point-type-badge" :class="point.param_type">
    {{ paramTypeLabel(point.param_type) }}
  </div>
  <el-button link type="danger" size="small" @click="deletePoint(point.id)">删除</el-button>
</div>
```

改为：
```html
<div class="point-header">
  <div class="point-type-badge" :class="point.param_type">
    {{ paramTypeLabel(point.param_type) }}
  </div>
  <div class="point-actions">
    <el-button link size="small" @click="openDrawer(point)">详情</el-button>
    <el-button link type="danger" size="small" @click="deletePoint(point.id)">删除</el-button>
  </div>
</div>
```

- [ ] **Step 4: 在模板末尾（`</el-dialog>` 之后）加入抽屉组件**

```html
<MonitorPointDrawer
  v-model="showDrawer"
  :point="drawerPoint"
  @saved="fetchEquipment"
/>
```

- [ ] **Step 5: 在 `<style scoped>` 中加 `.point-actions` 样式**

```css
.point-actions {
  display: flex;
  gap: 4px;
}
```

- [ ] **Step 6: 验证功能**

1. 启动前端 `npm run dev`（端口 3001）
2. 进入任意设备详情页
3. 点击监控点卡片上的「详情」按钮，确认抽屉打开，Tab 1 显示当前监控点数据
4. 修改名称后点「保存基本信息」，确认成功提示且页面刷新
5. 切换到「采集接口」Tab，选择 HTTP，填写 URL，点「保存采集接口」，确认成功
6. 再次打开同一监控点抽屉，确认采集接口数据已回填
7. 点「删除采集接口」，确认删除成功

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/equipment/EquipmentDetailView.vue
git commit -m "feat: integrate MonitorPointDrawer into EquipmentDetailView"
```

---

## 完成检查清单

- [ ] `CollectionInterface` 表已创建（`python manage.py showmigrations equipment`）
- [ ] `GET /api/equipment/monitor-points/{id}/collection/` 返回 null 或配置对象
- [ ] `PUT /api/equipment/monitor-points/{id}/collection/` 创建/更新配置
- [ ] `DELETE /api/equipment/monitor-points/{id}/collection/` 删除配置
- [ ] `GET /api/equipment/equipments/{id}/` 响应中 `monitor_points[].collection` 字段存在
- [ ] 设备详情页监控点卡片有「详情」按钮
- [ ] 抽屉 Tab 1 可编辑并保存监控点基本信息 + 阈值
- [ ] 抽屉 Tab 2 可配置 HTTP / MQTT 采集接口
- [ ] 切换协议时表单正确切换
- [ ] 已有采集接口时数据正确回填
- [ ] 删除采集接口后再次打开抽屉 Tab 2 为空表单
