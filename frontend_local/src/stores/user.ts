import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'worker' | 'team_leader' | 'safety_officer'
  is_assigner?: boolean  // 整改分派权限
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => user.value !== null)
  const isSafetyOfficer = computed(() => user.value?.role === 'safety_officer')
  const isTeamLeader = computed(() => user.value?.role === 'team_leader')
  const isAssigner = computed(() => user.value?.is_assigner === true)

  function setUser(u: UserInfo) {
    user.value = u
  }

  function clearUser() {
    user.value = null
  }

  return { user, isLoggedIn, isSafetyOfficer, isTeamLeader, isAssigner, setUser, clearUser }
  // Not persisted — session is restored from server via usersApi.me() on page load
})
