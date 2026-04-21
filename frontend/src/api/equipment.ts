import http from './http'
import type { Equipment, MonitorPoint, CollectionInterface, PaginatedResponse } from '@/types'

export const equipmentApi = {
  list(params?: Record<string, any>) {
    return http.get<PaginatedResponse<Equipment>>('/api/equipment/equipments/', { params })
  },
  get(id: number) {
    return http.get<Equipment>(`/api/equipment/equipments/${id}/`)
  },
  create(data: Partial<Equipment>) {
    return http.post<Equipment>('/api/equipment/equipments/', data)
  },
  update(id: number, data: Partial<Equipment>) {
    return http.put<Equipment>(`/api/equipment/equipments/${id}/`, data)
  },
  delete(id: number) {
    return http.delete(`/api/equipment/equipments/${id}/`)
  },
}

export const monitorPointApi = {
  list(params?: Record<string, any>) {
    return http.get<PaginatedResponse<MonitorPoint>>('/api/equipment/monitor-points/', { params })
  },
  create(data: Record<string, any>) {
    return http.post<MonitorPoint>('/api/equipment/monitor-points/', data)
  },
  update(id: number, data: Record<string, any>) {
    return http.put<MonitorPoint>(`/api/equipment/monitor-points/${id}/`, data)
  },
  delete(id: number) {
    return http.delete(`/api/equipment/monitor-points/${id}/`)
  },
  getCollection(id: number) {
    return http.get<CollectionInterface | null>(`/api/equipment/monitor-points/${id}/collection/`)
  },
  saveCollection(id: number, data: Omit<CollectionInterface, 'id'>) {
    return http.put<CollectionInterface>(`/api/equipment/monitor-points/${id}/collection/`, data)
  },
  deleteCollection(id: number) {
    return http.delete(`/api/equipment/monitor-points/${id}/collection/`)
  },
}
