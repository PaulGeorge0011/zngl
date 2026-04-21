import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { LatestReading, WSSensorData } from '@/types'

export const useMonitoringStore = defineStore('monitoring', () => {
  // 各设备的最新读数 { equipmentId: LatestReading[] }
  const latestReadings = reactive<Record<number, LatestReading[]>>({})
  // 各监控点的实时数据缓存 { pointId: {value, time}[] }
  const realtimeData = reactive<Record<number, { value: number; time: string }[]>>({})

  function updateReading(data: WSSensorData) {
    // 更新最新值
    const readings = latestReadings[data.equipment_id]
    if (readings) {
      const idx = readings.findIndex((r) => r.monitor_point_id === data.monitor_point_id)
      if (idx >= 0) {
        readings[idx].value = data.value
        readings[idx].recorded_at = data.recorded_at
      }
    }

    // 追加到实时缓存（保留最近 120 条）
    if (!realtimeData[data.monitor_point_id]) {
      realtimeData[data.monitor_point_id] = []
    }
    const cache = realtimeData[data.monitor_point_id]
    cache.push({ value: data.value, time: data.recorded_at })
    if (cache.length > 120) cache.shift()
  }

  function setLatestReadings(equipmentId: number, readings: LatestReading[]) {
    latestReadings[equipmentId] = readings
  }

  return { latestReadings, realtimeData, updateReading, setLatestReadings }
})
