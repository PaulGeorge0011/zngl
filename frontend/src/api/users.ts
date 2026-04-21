import http from './http'
import type { UserInfo } from '@/stores/user'

// ── 认证相关（原有）─────────────────────────────────────────────────────────

export const usersApi = {
  login(username: string, password: string) {
    return http.post<UserInfo>('/api/users/login/', { username, password })
  },

  logout() {
    return http.post('/api/users/logout/')
  },

  me() {
    return http.get<UserInfo>('/api/users/me/')
  },

  list(role?: string) {
    return http.get<UserInfo[]>('/api/users/list/', { params: role ? { role } : {} })
  },
}

// ── 用户管理相关（新增）──────────────────────────────────────────────────────

export interface ManagedUser {
  id: number
  username: string
  name: string
  role: 'worker' | 'team_leader' | 'safety_officer'
  employee_id: string
  phone: string
  is_active: boolean
}

export interface CreateUserPayload {
  username: string
  name: string
  password: string
  role: string
  employee_id?: string
  phone?: string
}

export interface UpdateUserPayload {
  name: string
  role: string
  employee_id?: string
  phone?: string
}

export const userManageApi = {
  list(search?: string) {
    return http.get<ManagedUser[]>('/api/users/manage/', {
      params: search ? { search } : {},
    })
  },

  create(data: CreateUserPayload) {
    return http.post<ManagedUser>('/api/users/manage/', data)
  },

  update(id: number, data: UpdateUserPayload) {
    return http.put<ManagedUser>(`/api/users/manage/${id}/`, data)
  },

  toggle(id: number) {
    return http.patch<ManagedUser>(`/api/users/manage/${id}/toggle/`)
  },

  resetPassword(id: number, password: string) {
    return http.post(`/api/users/manage/${id}/reset-password/`, { password })
  },
}
