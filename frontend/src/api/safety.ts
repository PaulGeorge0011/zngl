import http from './http'

export interface Location {
  id: number
  name: string
  sort_order: number
}

export interface UserBrief {
  id: number
  username: string
  display_name: string
}

export interface HazardImage {
  id: number
  image_url: string
  phase: 'report' | 'fix'
  created_at: string
}

export interface HazardListItem {
  id: number
  title: string
  level: 'general' | 'major'
  level_display: string
  location: number
  location_name: string
  location_detail: string
  status: 'pending' | 'fixing' | 'verifying' | 'closed' | 'rejected'
  status_display: string
  reporter: UserBrief
  assignee: UserBrief | null
  created_at: string
}

export interface HazardDetail extends HazardListItem {
  description: string
  assigned_by: UserBrief | null
  assigned_at: string | null
  fix_description: string
  fixed_at: string | null
  verified_by: UserBrief | null
  verified_at: string | null
  verify_remark: string
  updated_at: string
  images: HazardImage[]
}

export interface HazardListResponse {
  count: number
  page: number
  page_size: number
  results: HazardListItem[]
}

export interface HazardFilters {
  status?: string
  level?: string
  location?: number
  reporter?: number
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  page_size?: number
}

export const safetyApi = {
  getLocations() {
    return http.get<Location[]>('/api/safety/locations/')
  },

  listHazards(filters: HazardFilters = {}) {
    return http.get<HazardListResponse>('/api/safety/hazards/', { params: filters })
  },

  getHazard(id: number) {
    return http.get<HazardDetail>(`/api/safety/hazards/${id}/`)
  },

  createHazard(formData: FormData) {
    // Must NOT set Content-Type manually — axios auto-sets multipart/form-data
    // with the correct boundary when given FormData.
    return http.post<HazardDetail>('/api/safety/hazards/', formData, {
      headers: { 'Content-Type': undefined },
    })
  },

  assignHazard(id: number, assigneeId: number) {
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/assign/`, { assignee_id: assigneeId })
  },

  fixHazard(id: number, data: FormData) {
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/fix/`, data, {
      headers: { 'Content-Type': undefined },
    })
  },

  verifyHazard(id: number, action: 'approve' | 'reject', remark?: string) {
    return http.post<HazardDetail>(`/api/safety/hazards/${id}/verify/`, { action, remark })
  },
}
