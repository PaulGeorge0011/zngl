import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WSAlarmData } from '@/types'
import { ElNotification } from 'element-plus'

export const useAlarmStore = defineStore('alarm', () => {
  const recentAlarms = ref<WSAlarmData[]>([])
  const unreadCount = ref(0)

  function addAlarm(data: WSAlarmData) {
    recentAlarms.value.unshift(data)
    if (recentAlarms.value.length > 50) recentAlarms.value.pop()
    unreadCount.value++

    // 弹窗通知
    const isAlarm = data.level === 'alarm'
    ElNotification({
      title: isAlarm ? '设备报警' : '设备预警',
      message: `${data.equipment_name} - ${data.point_name}: ${data.triggered_value}${data.unit}`,
      type: isAlarm ? 'error' : 'warning',
      duration: 6000,
      position: 'top-right',
    })
  }

  function clearUnread() {
    unreadCount.value = 0
  }

  return { recentAlarms, unreadCount, addAlarm, clearUnread }
})
