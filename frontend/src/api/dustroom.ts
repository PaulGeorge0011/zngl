import http from './http'

// ── Types ───────────────────────────────────────────────────────────────────

export interface DustRoom {
  id: number
  name: string
  code: string
  description: string
  is_active: boolean
  sort_order: number
}

export interface InspectionItem {
  id: number
  template: number
  name: string
  item_type: 'checkbox' | 'number' | 'text' | 'select'
  options: string[]
  unit: string
  required: boolean
  sort_order: number
}

export interface InspectionTemplate {
  id: number
  role: string
  role_display: string
  name: string
  frequency: string
  is_active: boolean
  items: InspectionItem[]
  items_count: number
}

export interface InspectionTemplateListItem {
  id: number
  role: string
  role_display: string
  name: string
  frequency: string
  is_active: boolean
  items_count: number
}

export interface UserBrief {
  id: number
  username: string
  display_name: string
}

export interface DustRoomInspector {
  id: number
  user: number
  role: string
  user_display: UserBrief
  role_display: string
}

export interface TaskItem {
  dust_room: DustRoom
  template_id: number
  role: string
  role_display: string
  completed: boolean
  record_id: number | null
  has_abnormal: boolean
}

export interface MyTasksResponse {
  roles: { role: string; role_display: string }[]
  tasks: TaskItem[]
}

export interface InspectionRecordListItem {
  id: number
  dust_room: number
  dust_room_name: string
  template: number
  role_display: string
  inspector_display: UserBrief
  inspection_date: string
  status: string
  has_abnormal: boolean
  abnormal_count: number
  created_at: string
  submitted_at: string
}

export interface ItemResultDetail {
  id: number
  item: number
  item_name: string
  item_type: string
  item_unit: string
  value: string
  is_normal: boolean
  remark: string
}

export interface InspectionRecordDetail {
  id: number
  dust_room: number
  dust_room_name: string
  template: number
  role_display: string
  inspector_display: UserBrief
  inspection_date: string
  status: string
  has_abnormal: boolean
  remark: string
  results: ItemResultDetail[]
  created_at: string
  submitted_at: string
}

export interface OverviewRoleCompletion {
  role: string
  role_display: string
  expected: number
  completed: number
}

export interface OverviewAbnormal {
  room_name: string
  item_name: string
  inspector: string
  time: string
  remark: string
}

export interface OverviewData {
  today: string
  rooms_total: number
  completion_by_role: OverviewRoleCompletion[]
  abnormal_count: number
  recent_abnormals: OverviewAbnormal[]
}

export interface RecordListResponse {
  count: number
  page: number
  page_size: number
  results: InspectionRecordListItem[]
}

// ── API ─────────────────────────────────────────────────────────────────────

const BASE = '/api/safety/dustroom'

export const dustroomApi = {
  // Rooms
  getRooms(activeOnly = false) {
    const params = activeOnly ? { active: 'true' } : {}
    return http.get<DustRoom[]>(`${BASE}/rooms/`, { params })
  },
  createRoom(data: Partial<DustRoom>) {
    return http.post<DustRoom>(`${BASE}/rooms/`, data)
  },
  updateRoom(id: number, data: Partial<DustRoom>) {
    return http.put<DustRoom>(`${BASE}/rooms/${id}/`, data)
  },
  deleteRoom(id: number) {
    return http.delete(`${BASE}/rooms/${id}/`)
  },

  // Templates
  getTemplates() {
    return http.get<InspectionTemplateListItem[]>(`${BASE}/templates/`)
  },
  getTemplate(id: number) {
    return http.get<InspectionTemplate>(`${BASE}/templates/${id}/`)
  },
  createTemplate(data: Partial<InspectionTemplate>) {
    return http.post<InspectionTemplate>(`${BASE}/templates/`, data)
  },
  updateTemplate(id: number, data: Partial<InspectionTemplate>) {
    return http.put<InspectionTemplate>(`${BASE}/templates/${id}/`, data)
  },

  // Items
  getItems(templateId: number) {
    return http.get<InspectionItem[]>(`${BASE}/templates/${templateId}/items/`)
  },
  createItem(templateId: number, data: Partial<InspectionItem>) {
    return http.post<InspectionItem>(`${BASE}/templates/${templateId}/items/`, data)
  },
  updateItem(templateId: number, itemId: number, data: Partial<InspectionItem>) {
    return http.put<InspectionItem>(`${BASE}/templates/${templateId}/items/${itemId}/`, data)
  },
  deleteItem(templateId: number, itemId: number) {
    return http.delete(`${BASE}/templates/${templateId}/items/${itemId}/`)
  },

  // Inspectors
  getInspectors(role?: string) {
    const params = role ? { role } : {}
    return http.get<DustRoomInspector[]>(`${BASE}/inspectors/`, { params })
  },
  addInspector(data: { user: number; role: string }) {
    return http.post<DustRoomInspector>(`${BASE}/inspectors/`, data)
  },
  removeInspector(id: number) {
    return http.delete(`${BASE}/inspectors/${id}/`)
  },

  // Tasks & Records
  getMyTasks() {
    return http.get<MyTasksResponse>(`${BASE}/my-tasks/`)
  },
  submitRecord(data: {
    dust_room: number
    template: number
    results: { item: number; value: string; is_normal: boolean; remark: string }[]
    remark?: string
  }) {
    return http.post<InspectionRecordDetail>(`${BASE}/records/create/`, data)
  },
  getRecords(params: Record<string, string | number> = {}) {
    return http.get<RecordListResponse>(`${BASE}/records/`, { params })
  },
  getRecord(id: number) {
    return http.get<InspectionRecordDetail>(`${BASE}/records/${id}/`)
  },

  // Overview
  getOverview() {
    return http.get<OverviewData>(`${BASE}/overview/`)
  },
}
