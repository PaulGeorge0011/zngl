import axios from 'axios'
import { ElMessage } from 'element-plus'

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const csrf = getCsrfToken()
  if (csrf) {
    config.headers['X-CSRFToken'] = csrf
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const isAuthFailure =
      status === 401 ||
      (status === 403 && (
        detail === 'Authentication credentials were not provided.' ||
        detail === 'You do not have permission to perform this action.' ||
        detail === 'Invalid token.'
      ))

    if (isAuthFailure) {
      import('@/stores/user').then(({ useUserStore }) => {
        useUserStore().clearUser()
      })

      import('@/router-app').then(({ default: router }) => {
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      })

      return Promise.reject(error)
    }

    const msg = error.response?.data?.detail || error.response?.data?.error || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http
