# 监控点位增删改 + 采集接口配置 设计文档

**日期**: 2026-03-19
**项目**: ZS2 制丝车间智能管理系统
**范围**: 设备监控点位 UI 增删改 + 采集接口配置存储（HTTP / MQTT）

---

## 1. 背景

现有系统中，监控点位（MonitorPoint）的增删改已有基础实现，但：
- 编辑功能不完整（只有新增对话框，无编辑入口）
- 没有采集接口（CollectionInterface）模型和配置 UI
- 采集数据目前依赖外部系统 POST 到 `/api/monitoring/readings/`

本次目标：在设备详情页提供完整的监控点位增删改 UI，并支持为每个监控点配置 HTTP 或 MQTT 采集接口（配置存储，执行逻辑后期实现）。

---

## 2. 后端数据模型

### 新增：CollectionInterface

位置：`backend/apps/equipment/models.py`

```python
class CollectionInterface(models.Model):
    INTERFACE_TYPES = [('http', 'HTTP'), ('mqtt', 'MQTT')]

    monitor_point = models.OneToOneField(
        MonitorPoint, on_delete=models.CASCADE, related_name='collection'
    )
    interface_type = models.CharField(max_length=10, choices=INTERFACE_TYPES)
    config = models.JSONField(default=dict)
    polling_interval = models.IntegerField(default=60)  # 秒，仅 HTTP 有效
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### config JSON 结构

**HTTP 协议：**
```json
{
  "url": "http://...",
  "method": "GET",
  "headers": {},
  "data_path": "data.value",
  "auth_type": "none",
  "auth_value": ""
}
```

**MQTT 协议：**
```json
{
  "broker": "mqtt://...",
  "topic": "sensors/xxx",
  "username": "",
  "password": "",
  "data_path": "value"
}
```

`data_path` 为 JSONPath 表达式，供后期采集执行逻辑提取数值使用。

### 现有模型不变

- `MonitorPoint`：不修改字段
- `ThresholdRule`：不修改
- `SensorReading`、`AlarmRecord`：不修改

---

## 3. 后端 API

### 现有端点改动（最小）

- `GET /api/equipment/equipments/{id}/` 响应中，`monitor_points` 嵌套数据新增 `collection` 字段（只读，null 表示未配置）
- `GET /api/equipment/monitor-points/` 列表响应同样嵌套 `collection`

### 新增：采集接口端点

挂载在 `MonitorPointViewSet` 的 `@action` 上：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/equipment/monitor-points/{id}/collection/` | 获取采集接口配置 |
| POST | `/api/equipment/monitor-points/{id}/collection/` | 创建采集接口配置 |
| PUT | `/api/equipment/monitor-points/{id}/collection/` | 更新采集接口配置 |
| DELETE | `/api/equipment/monitor-points/{id}/collection/` | 删除采集接口配置 |

### 序列化器校验规则

- `interface_type = http`：`config.url` 必填
- `interface_type = mqtt`：`config.broker` 和 `config.topic` 必填
- 其余字段可选

---

## 4. 前端 UI

### 4.1 监控点卡片改动（EquipmentDetailView）

每张监控点卡片右上角操作区：
- 新增「详情」按钮 → 打开 MonitorPointDrawer（编辑模式）
- 保留「删除」按钮（现有逻辑不变）

新增监控点仍使用现有 `el-dialog` 对话框（只填基本信息 + 阈值），提交后如需配置采集接口，点卡片「详情」进入抽屉。

### 4.2 MonitorPointDrawer 组件

**文件**：`frontend/src/components/equipment/MonitorPointDrawer.vue`

- 宽度：480px
- 两个 Tab：

**Tab 1 — 基本信息**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | 文本 | 监控点名称 |
| param_key | 文本 | 参数标识（唯一） |
| param_type | 下拉 | temperature / current / vibration |
| unit | 文本 | 单位 |
| warning_high / warning_low | 数字 | 预警阈值 |
| alarm_high / alarm_low | 数字 | 报警阈值 |

**Tab 2 — 采集接口**

- 顶部：`is_active` 开关
- 协议选择：HTTP / MQTT（切换时表单动态切换，两套数据独立保存）
- HTTP 表单：URL、请求方法（GET/POST）、数据路径、认证类型（无/API Key/Basic）、认证值、轮询间隔（秒）
- MQTT 表单：Broker 地址、Topic、用户名、密码、数据路径
- 操作按钮：保存采集接口 / 删除采集接口（已配置时显示）

### 4.3 API 客户端扩展

文件：`frontend/src/api/equipment.ts`，在 `monitorPointApi` 下新增：

```typescript
monitorPointApi.getCollection(id)      // GET  /api/equipment/monitor-points/{id}/collection/
monitorPointApi.saveCollection(id, data) // POST/PUT（有则更新，无则创建）
monitorPointApi.deleteCollection(id)   // DELETE
```

### 4.4 类型定义扩展

文件：`frontend/src/types/index.ts`

```typescript
interface CollectionInterface {
  id?: number
  interface_type: 'http' | 'mqtt'
  config: HttpConfig | MqttConfig
  polling_interval: number
  is_active: boolean
}

interface HttpConfig {
  url: string
  method: 'GET' | 'POST'
  headers: Record<string, string>
  data_path: string
  auth_type: 'none' | 'api_key' | 'basic'
  auth_value: string
}

interface MqttConfig {
  broker: string
  topic: string
  username: string
  password: string
  data_path: string
}
```

---

## 5. 数据流

```
用户点击「详情」
  → MonitorPointDrawer 打开
  → 加载 MonitorPoint 基本信息（已在卡片数据中）
  → 加载 collection 配置（GET /collection/）
  → 用户编辑 Tab 1 → 保存 → PUT /monitor-points/{id}/
  → 用户编辑 Tab 2 → 保存 → POST/PUT /monitor-points/{id}/collection/
  → 抽屉关闭，父组件刷新监控点列表
```

---

## 6. 不在本次范围内

- 采集执行逻辑（HTTP 定时拉取、MQTT 订阅）
- Modbus / OPC-UA 协议支持
- 采集接口连通性测试按钮
- 采集日志 / 错误记录展示

---

## 7. 迁移

新增一张 `equipment_collectioninterface` 表，运行 `python manage.py makemigrations && python manage.py migrate` 即可，不影响现有数据。
