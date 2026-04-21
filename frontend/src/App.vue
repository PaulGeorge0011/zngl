<template>
  <div class="app-root noise-overlay">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { monitoringWS } from '@/utils/websocket'
import { useMonitoringStore } from '@/stores/monitoring'
import { useAlarmStore } from '@/stores/alarm'
import type { WSSensorData, WSAlarmData } from '@/types'

const monitoringStore = useMonitoringStore()
const alarmStore = useAlarmStore()

onMounted(() => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsBase = import.meta.env.VITE_WS_BASE || `${wsProtocol}://${window.location.host}`
  const basePath = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
  monitoringWS.connect(`${wsBase}${basePath}/ws/monitoring/`)

  monitoringWS.subscribe((type, data) => {
    if (type === 'sensor') {
      monitoringStore.updateReading(data as WSSensorData)
    } else if (type === 'alarm') {
      alarmStore.addAlarm(data as WSAlarmData)
    }
  })
})

onUnmounted(() => {
  monitoringWS.disconnect()
})
</script>

<style>
.app-root {
  height: 100vh;
  overflow: hidden;
}
</style>
