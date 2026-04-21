import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'worker' | 'team_leader' | 'safety_officer'
}

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => user.value !== null)
  const isSafetyOfficer = computed(() => user.value?.role === 'safety_officer')
  const isTeamLeader = computed(() => user.value?.role === 'team_leader')

  function setUser(u: UserInfo) {
    user.value = u
  }

  function clearUser() {
    user.value = null
  }

  return { user, isLoggedIn, isSafetyOfficer, isTeamLeader, setUser, clearUser }
  // Not persisted — session is restored from server via usersApi.me() on page load
})
