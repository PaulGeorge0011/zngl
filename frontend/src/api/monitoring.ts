import http from './http'
import type {
  DashboardStats,
  LatestReading,
  SensorReading,
  AlarmRecord,
  PaginatedResponse,
} from '@/types'

export const monitoringApi = {
  dashboard() {
    return http.get<DashboardStats>('/api/monitoring/dashboard/')
  },
  latest(equipmentId: number) {
    return http.get<LatestReading[]>('/api/monitoring/latest/', {
      params: { equipment_id: equipmentId },
    })
  },
  readingsHistory(pointId: number, minutes: number = 60) {
    return http.get<SensorReading[]>('/api/monitoring/readings/history/', {
      params: { point_id: pointId, minutes },
    })
  },
  alarms(params?: Record<string, any>) {
    return http.get<PaginatedResponse<AlarmRecord>>('/api/monitoring/alarms/', { params })
  },
  acknowledgeAlarm(id: number) {
    return http.patch<AlarmRecord>(`/api/monitoring/alarms/${id}/acknowledge/`)
  },
  resolveAlarm(id: number, note: string = '') {
    return http.patch<AlarmRecord>(`/api/monitoring/alarms/${id}/resolve/`, { note })
  },
}
