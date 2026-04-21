// 设备相关类型
export interface Equipment {
  id: number
  name: string
  code: string
  location: string
  description: string
  status: 'running' | 'stopped' | 'fault'
  monitor_points_count?: number
  active_alarms_count?: number
  monitor_points?: MonitorPoint[]
  created_at: string
  updated_at: string
}

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

export interface ThresholdRule {
  id?: number
  monitor_point?: number
  warning_high: number | null
  warning_low: number | null
  alarm_high: number | null
  alarm_low: number | null
  is_active?: boolean
}

// 监控相关类型
export interface SensorReading {
  id?: number
  monitor_point: number
  value: number
  recorded_at: string
}

export interface LatestReading {
  monitor_point_id: number
  name: string
  param_key: string
  param_type: string
  unit: string
  value: number | null
  recorded_at: string | null
  threshold: ThresholdRule | null
}

export interface AlarmRecord {
  id: number
  monitor_point: number
  equipment_name: string
  equipment_id: number
  point_name: string
  param_type: string
  unit: string
  level: 'warning' | 'alarm'
  status: 'active' | 'acknowledged' | 'resolved'
  triggered_value: number
  threshold_value: number
  triggered_at: string
  resolved_at: string | null
  note: string
  has_repair_advice: boolean
}

export interface RepairAdvice {
  id: number
  alarm: number
  alarm_info: AlarmRecord
  ai_response: string
  ragflow_context: string
  created_at: string
}

// Dashboard
export interface DashboardStats {
  equipment_total: number
  equipment_running: number
  equipment_fault: number
  alarms_active: number
  alarms_today: number
  readings_today: number
}

// WebSocket 消息
export interface WSMessage {
  type: 'sensor' | 'alarm'
  data: WSSensorData | WSAlarmData
}

export interface WSSensorData {
  monitor_point_id: number
  equipment_id: number
  value: number
  recorded_at: string
  point_name: string
  unit: string
  param_type: string
}

export interface WSAlarmData {
  id: number
  level: string
  status: string
  triggered_value: number
  threshold_value: number
  monitor_point_id: number
  equipment_name: string
  point_name: string
  unit: string
  triggered_at: string
}

// API 分页响应
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

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
