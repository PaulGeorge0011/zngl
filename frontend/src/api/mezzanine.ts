import http from './http'

export interface MezzanineOnsite {
  id: number
  name: string
  phone: string        // 脱敏（138****8000）
  company: string
  project: string
  count: number
  check_in_at: string
}

export interface MezzanineRecord {
  id: number
  name: string
  phone: string        // 完整手机号（管理端）
  company: string
  project: string
  count: number
  check_in_at: string
  check_out_at: string | null
  duration: string
  status: 'onsite' | 'left'
}

export interface MezzanineHistoryResponse {
  count: number
  page: number
  results: MezzanineRecord[]
  stats: {
    today_count: number
    onsite_count: number
  }
}

export interface CheckinPayload {
  name: string
  phone: string
  company?: string
  project: string
  count?: number
}

export interface CheckoutPayload {
  record_id: number
  phone_last4: string
}

export interface HistoryFilters {
  search?: string
  project?: string
  date_from?: string
  date_to?: string
  status?: 'onsite' | 'left' | ''
  page?: number
}

export const mezzanineApi = {
  checkin(data: CheckinPayload) {
    return http.post<{ id: number; name: string; check_in_at: string; message: string }>(
      '/api/safety/mezzanine/checkin/',
      data
    )
  },

  onsite() {
    return http.get<MezzanineOnsite[]>('/api/safety/mezzanine/onsite/')
  },

  checkout(data: CheckoutPayload) {
    return http.post<{ name: string; check_out_at: string; message: string }>(
      '/api/safety/mezzanine/checkout/',
      data
    )
  },

  history(filters: HistoryFilters = {}) {
    return http.get<MezzanineHistoryResponse>('/api/safety/mezzanine/history/', {
      params: filters,
    })
  },

  create(data: { name: string; phone: string; company?: string; project: string; count?: number }) {
    return http.post('/api/safety/mezzanine/manage/', data)
  },

  update(id: number, data: { name: string; phone: string; company?: string; project: string; count?: number }) {
    return http.put(`/api/safety/mezzanine/manage/${id}/`, data)
  },

  remove(id: number) {
    return http.delete(`/api/safety/mezzanine/manage/${id}/delete/`)
  },
}
