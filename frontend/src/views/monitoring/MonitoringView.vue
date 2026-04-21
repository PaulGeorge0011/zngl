<template>
  <div class="monitoring-layout">
    <!-- Left: Equipment Selector -->
    <aside class="equipment-panel">
      <div class="panel-title">设备列表</div>
      <div class="equipment-list">
        <div
          v-for="eq in equipments"
          :key="eq.id"
          class="eq-item"
          :class="{ active: selectedId === eq.id }"
          @click="selectEquipment(eq.id)"
        >
          <StatusIndicator
            :status="eq.status === 'fault' ? 'alarm' : eq.status === 'running' ? 'normal' : 'offline'"
            :size="8"
          />
          <div class="eq-info">
            <div class="eq-name">{{ eq.name }}</div>
            <div class="eq-location">{{ eq.location }}</div>
          </div>
          <div v-if="(eq.active_alarms_count || 0) > 0" class="eq-alarm-badge">
            {{ eq.active_alarms_count }}
          </div>
        </div>
      </div>
    </aside>

    <!-- Right: Charts -->
    <main class="charts-area" v-if="selectedId">
      <div class="charts-header">
        <h3 class="charts-title">{{ selectedEquipment?.name }}</h3>
        <span class="charts-subtitle">{{ selectedEquipment?.location }}</span>
      </div>

      <div class="charts-grid" v-if="currentPoints.length > 0">
        <SensorChart
          v-for="point in currentPoints"
          :key="point.monitor_point_id"
          :title="point.name"
          :unit="point.unit"
          :param-type="point.param_type"
          :data="getChartData(point.monitor_point_id)"
          :threshold="point.threshold"
        />
      </div>

      <div v-else class="empty-state">
        <p>该设备暂无监控点</p>
      </div>
    </main>

    <main v-else class="charts-area empty-state-full">
      <div class="empty-prompt">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <polyline points="4,32 12,24 20,28 32,12 40,20 46,8"/>
          <line x1="4" y1="40" x2="44" y2="40"/>
        </svg>
        <p>选择左侧设备查看实时监控数据</p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { equipmentApi } from '@/api/equipment'
import { monitoringApi } from '@/api/monitoring'
import { useMonitoringStore } from '@/stores/monitoring'
import type { Equipment, LatestReading } from '@/types'
import SensorChart from '@/components/monitoring/SensorChart.vue'
import StatusIndicator from '@/components/monitoring/StatusIndicator.vue'

const monitoringStore = useMonitoringStore()
const equipments = ref<Equipment[]>([])
const selectedId = ref<number | null>(null)
const currentPoints = ref<LatestReading[]>([])

const selectedEquipment = computed(() =>
  equipments.value.find((e) => e.id === selectedId.value)
)

function getChartData(pointId: number) {
  return monitoringStore.realtimeData[pointId] || []
}

async function selectEquipment(id: number) {
  selectedId.value = id

  try {
    // Load latest readings
    const { data: latest } = await monitoringApi.latest(id)
    currentPoints.value = latest
    monitoringStore.setLatestReadings(id, latest)

    // Load history for each point
    for (const point of latest) {
      const { data: history } = await monitoringApi.readingsHistory(point.monitor_point_id, 30)
      monitoringStore.realtimeData[point.monitor_point_id] = history.map((r) => ({
        value: r.value,
        time: r.recorded_at,
      }))
    }
  } catch {
    // API might not be running
  }
}

async function fetchEquipments() {
  try {
    const { data } = await equipmentApi.list({ page_size: 100 })
    equipments.value = data.results
    if (data.results.length > 0 && !selectedId.value) {
      selectEquipment(data.results[0].id)
    }
  } catch {
    // API might not be running
  }
}

onMounted(fetchEquipments)
</script>

<style scoped>
.monitoring-layout {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

.equipment-panel {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-panel);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title {
  padding: 16px 18px 12px;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.equipment-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 8px;
}

.eq-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 2px;
}

.eq-item:hover {
  background: rgba(255, 255, 255, 0.03);
}

.eq-item.active {
  background: var(--sidebar-item-active);
  border-left: 3px solid var(--color-accent);
  padding-left: 9px;
}

.eq-info {
  flex: 1;
  min-width: 0;
}

.eq-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eq-location {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.eq-alarm-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--color-alarm);
  color: white;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse-alarm 2s ease-in-out infinite;
}

.charts-area {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}

.charts-header {
  margin-bottom: 20px;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.charts-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text-primary);
}

.charts-subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--text-muted);
}

.empty-state-full {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--text-muted);
  font-size: 0.95rem;
}

@media (max-width: 960px) {
  .monitoring-layout {
    height: auto;
    min-height: calc(100vh - 60px);
    flex-direction: column;
    overflow-y: auto;
  }

  .equipment-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }

  .equipment-list {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0 12px 12px;
  }

  .eq-item {
    min-width: 220px;
    margin-bottom: 0;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
  }

  .charts-area {
    padding: 16px;
  }

  .charts-header {
    margin-bottom: 14px;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .panel-title {
    padding: 14px 14px 10px;
  }

  .equipment-list {
    padding: 0 10px 10px;
  }

  .eq-item {
    min-width: 180px;
    padding: 10px;
  }

  .empty-state,
  .empty-prompt {
    padding: 24px 12px;
  }
}
</style>
