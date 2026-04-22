import http from './http'

export interface NightShiftCheckItem {
  id: number
  category: number
  name: string
  is_active: boolean
  sort_order: number
}

export interface NightShiftCategory {
  id: number
  name: string
  allows_custom: boolean
  sort_order: number
  is_active: boolean
  items: NightShiftCheckItem[]
  items_count: number
}

export interface NightShiftCategoryListItem {
  id: number
  name: string
  allows_custom: boolean
  sort_order: number
  is_active: boolean
  items_count: number
}

export interface UserBrief {
  id: number
  username: string
  display_name: string
}

export interface NightShiftDuty {
  id: number
  duty_date: string
  inspector: number
  inspector_display: UserBrief
  inspector_phone: string
  status: 'pending' | 'completed'
  status_display: string
  record_id: number | null
  has_issues: boolean
  sms_sent_at: string | null
  created_by: number
  created_by_display: UserBrief
  created_at: string
  updated_at: string
}

export interface NightShiftIssue {
  id: number
  description: string
  rectification: string
  is_resolved: boolean
}

export interface NightShiftCheckResult {
  id: number
  category: number
  category_name: string
  item: number | null
  item_name: string
  custom_name: string
  is_normal: boolean
  remark: string
}

export interface NightShiftRecordListItem {
  id: number
  inspector_display: UserBrief
  inspection_date: string
  status: string
  has_issues: boolean
  abnormal_count: number
  issue_count: number
  unresolved_count: number
  created_at: string
  submitted_at: string
}

export interface NightShiftRecordDetail {
  id: number
  duty_id: number | null
  inspector_display: UserBrief
  inspection_date: string
  status: string
  has_issues: boolean
  overall_remark: string
  results: NightShiftCheckResult[]
  issues: NightShiftIssue[]
  created_at: string
  submitted_at: string
}

export interface NightShiftOverview {
  today: string
  today_duty: NightShiftDuty | null
  upcoming: NightShiftDuty[]
  recent_completed: NightShiftDuty[]
  stats_30d: { total: number; completed: number }
  check_stats: { total: number; normal: number; abnormal: number }
  issue_stats: { total: number; resolved: number; unresolved: number }
  recent_issues: { description: string; rectification: string; is_resolved: boolean }[]
}

export interface TodayStatus {
  has_duty_today: boolean
  is_my_duty: boolean
  duty: NightShiftDuty | null
}

export interface RecordListResponse {
  count: number
  page: number
  page_size: number
  results: NightShiftRecordListItem[]
}

export interface InspectorStatRow {
  inspector_id: number
  username: string
  display_name: string
  total: number
  completed: number
  pending: number
  with_issues: number
}

export interface InspectorStatsResponse {
  month: string
  results: InspectorStatRow[]
}

const BASE = '/api/safety/nightshift'

export const nightshiftApi = {
  // Categories
  getCategories(activeOnly = false) {
    const params = activeOnly ? { active: 'true' } : {}
    return http.get<NightShiftCategoryListItem[]>(`${BASE}/categories/`, { params })
  },
  getCategoryDetail(id: number) {
    return http.get<NightShiftCheckItem[]>(`${BASE}/categories/${id}/items/`)
  },
  createCategory(data: Partial<NightShiftCategory>) {
    return http.post<NightShiftCategory>(`${BASE}/categories/`, data)
  },
  updateCategory(id: number, data: Partial<NightShiftCategory>) {
    return http.put<NightShiftCategory>(`${BASE}/categories/${id}/`, data)
  },
  deleteCategory(id: number) {
    return http.delete(`${BASE}/categories/${id}/`)
  },

  // Items
  getItems(categoryId: number, activeOnly = false) {
    const params = activeOnly ? { active: 'true' } : {}
    return http.get<NightShiftCheckItem[]>(`${BASE}/categories/${categoryId}/items/`, { params })
  },
  createItem(categoryId: number, data: Partial<NightShiftCheckItem>) {
    return http.post<NightShiftCheckItem>(`${BASE}/categories/${categoryId}/items/`, data)
  },
  updateItem(categoryId: number, itemId: number, data: Partial<NightShiftCheckItem>) {
    return http.put<NightShiftCheckItem>(`${BASE}/categories/${categoryId}/items/${itemId}/`, data)
  },
  deleteItem(categoryId: number, itemId: number) {
    return http.delete(`${BASE}/categories/${categoryId}/items/${itemId}/`)
  },

  // Duties
  getDuties(params: Record<string, string> = {}) {
    return http.get<NightShiftDuty[]>(`${BASE}/duties/`, { params })
  },
  createDuty(data: { dates?: string[]; duty_date?: string; inspector: number }) {
    return http.post<NightShiftDuty[]>(`${BASE}/duties/`, data)
  },
  updateDuty(id: number, data: { duty_date?: string; inspector?: number }) {
    return http.put<NightShiftDuty>(`${BASE}/duties/${id}/`, data)
  },
  deleteDuty(id: number) {
    return http.delete(`${BASE}/duties/${id}/`)
  },

  // Today
  getTodayStatus() {
    return http.get<TodayStatus>(`${BASE}/today/`)
  },

  // Records
  submitRecord(data: {
    duty_id: number
    results: { category: number; item?: number; custom_name?: string; is_normal: boolean; remark: string }[]
    issues: { description: string; rectification: string; is_resolved: boolean }[]
    overall_remark?: string
  }) {
    return http.post<NightShiftRecordDetail>(`${BASE}/records/create/`, data)
  },
  getRecords(params: Record<string, string | number> = {}) {
    return http.get<RecordListResponse>(`${BASE}/records/`, { params })
  },
  getRecord(id: number) {
    return http.get<NightShiftRecordDetail>(`${BASE}/records/${id}/`)
  },

  // Overview
  getOverview() {
    return http.get<NightShiftOverview>(`${BASE}/overview/`)
  },

  // Inspector stats（按人员汇总监护次数，可选 month=YYYY-MM）
  getInspectorStats(month?: string) {
    const params = month ? { month } : {}
    return http.get<InspectorStatsResponse>(`${BASE}/inspector-stats/`, { params })
  },
}
