import http from './http'
import type { UserBrief } from './safety'

export type RectSourceType = 'hazard_report' | 'dustroom_inspection' | 'nightshift_check'
export type RectStatus = 'pending' | 'fixing' | 'verifying' | 'closed' | 'cancelled'
export type RectSeverity = 'general' | 'major' | 'critical'
export type RectImagePhase = 'issue' | 'rectify'

export interface RectImage {
  id: number
  image_url: string
  phase: RectImagePhase
  created_at: string
}

export interface RectLog {
  id: number
  action: string
  action_display: string
  operator: UserBrief | null
  from_status: string
  to_status: string
  remark: string
  created_at: string
}

export interface RectListItem {
  id: number
  source_type: RectSourceType
  source_type_display: string
  source_id: number
  title: string
  location_text: string
  severity: RectSeverity
  severity_display: string
  status: RectStatus
  status_display: string
  submitter: UserBrief
  assignee: UserBrief | null
  assigned_at: string | null
  deadline: string | null
  rectified_at: string | null
  overdue: boolean
  reject_count: number
  created_at: string
  updated_at: string
}

export interface RectDetail extends RectListItem {
  description: string
  source_snapshot: Record<string, unknown>
  assigner: UserBrief | null
  rectify_description: string
  verifier: UserBrief | null
  verifier_assigner: UserBrief | null
  verifier_assigned_at: string | null
  verified_at: string | null
  verify_remark: string
  images: RectImage[]
  logs: RectLog[]
}

export type RectNotifySource = '' | RectSourceType

export interface RectNotifyRecipient {
  id: number
  user: UserBrief
  source_type: RectNotifySource
  source_type_display: string
  phone: string
  enabled: boolean
  created_at: string
}

export interface RectListResponse {
  count: number
  page: number
  page_size: number
  results: RectListItem[]
}

export interface RectFilters {
  status?: RectStatus
  source_type?: RectSourceType
  severity?: RectSeverity
  assignee?: number
  submitter?: number
  source_id?: number
  overdue?: 'true' | 'false'
  scope?: 'assigned' | 'submitted' | 'to_verify' | 'to_assign' | ''
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  page_size?: number
}

export interface RectMyCounts {
  to_fix: number
  submitted: number
  to_verify: number
  to_assign: number
  is_safety_officer: boolean
}

export interface RectStats {
  total: number
  by_status: Record<string, number>
  by_source: Record<string, number>
  overdue: number
}

export const rectificationApi = {
  list(filters: RectFilters = {}) {
    return http.get<RectListResponse>('/api/safety/rectifications/', { params: filters })
  },
  get(id: number) {
    return http.get<RectDetail>(`/api/safety/rectifications/${id}/`)
  },
  myCounts() {
    return http.get<RectMyCounts>('/api/safety/rectifications/my/')
  },
  stats() {
    return http.get<RectStats>('/api/safety/rectifications/stats/')
  },
  assign(id: number, payload: { assignee_id: number; deadline?: string; remark?: string }) {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/assign/`, payload)
  },
  reassign(id: number, payload: { assignee_id: number; deadline?: string; remark?: string }) {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/reassign/`, payload)
  },
  assignVerifier(id: number, payload: { verifier_id: number; remark?: string }) {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/assign-verifier/`, payload)
  },
  submitRectify(id: number, data: FormData) {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/submit/`, data, {
      headers: { 'Content-Type': undefined },
    })
  },
  verify(id: number, action: 'approve' | 'reject', remark = '') {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/verify/`, { action, remark })
  },
  cancel(id: number, remark: string) {
    return http.post<RectDetail>(`/api/safety/rectifications/${id}/cancel/`, { remark })
  },

  // 新工单通知接收人配置
  listNotifyRecipients() {
    return http.get<RectNotifyRecipient[]>('/api/safety/rectifications-notify-config/')
  },
  addNotifyRecipient(payload: { user_id: number; source_type: RectNotifySource }) {
    return http.post<RectNotifyRecipient>('/api/safety/rectifications-notify-config/', payload)
  },
  toggleNotifyRecipient(id: number, enabled: boolean) {
    return http.patch<RectNotifyRecipient>(
      `/api/safety/rectifications-notify-config/${id}/`,
      { enabled }
    )
  },
  removeNotifyRecipient(id: number) {
    return http.delete(`/api/safety/rectifications-notify-config/${id}/`)
  },
}
