<template>
  <div class="sensor-chart-wrapper">
    <div class="chart-header">
      <div class="chart-info">
        <StatusIndicator :status="currentStatus" :size="10" />
        <span class="chart-title">{{ title }}</span>
      </div>
      <div class="chart-value">
        <span class="value-num" :class="`status-${currentStatus}`">
          {{ latestValue !== null ? latestValue.toFixed(1) : '--' }}
        </span>
        <span class="value-unit">{{ unit }}</span>
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
    <div v-if="threshold" class="threshold-bar">
      <span class="threshold-label">阈值</span>
      <span v-if="threshold.warning_high" class="th-item warning">
        预警 {{ threshold.warning_high }}
      </span>
      <span v-if="threshold.alarm_high" class="th-item alarm">
        报警 {{ threshold.alarm_high }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import type { ECharts } from 'echarts'
import type { ThresholdRule } from '@/types'
import StatusIndicator from './StatusIndicator.vue'

const props = defineProps<{
  title: string
  unit: string
  data: { value: number; time: string }[]
  threshold?: ThresholdRule | null
  paramType: string
}>()

const chartRef = ref<HTMLElement>()
let chart: ECharts | null = null

const latestValue = computed(() => {
  if (props.data.length === 0) return null
  return props.data[props.data.length - 1].value
})

const currentStatus = computed(() => {
  const v = latestValue.value
  if (v === null) return 'offline'
  const th = props.threshold
  if (!th) return 'normal'
  if ((th.alarm_high && v > th.alarm_high) || (th.alarm_low && v < th.alarm_low)) return 'alarm'
  if ((th.warning_high && v > th.warning_high) || (th.warning_low && v < th.warning_low)) return 'warning'
  return 'normal'
})

const colorMap: Record<string, string> = {
  temperature: '#f0a500',
  current: '#4a9eff',
  vibration: '#00d4aa',
}

async function initChart() {
  if (!chartRef.value) return
  const echarts = await import('echarts')
  chart = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  updateChart()
}

function updateChart() {
  if (!chart) return

  const lineColor = colorMap[props.paramType] || '#4a9eff'
  const times = props.data.map((d) => {
    const t = new Date(d.time)
    return `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`
  })
  const values = props.data.map((d) => d.value)

  const markLines: any[] = []
  if (props.threshold?.warning_high) {
    markLines.push({
      yAxis: props.threshold.warning_high,
      lineStyle: { color: '#f0a500', type: 'dashed', width: 1, opacity: 0.6 },
      label: { show: false },
    })
  }
  if (props.threshold?.alarm_high) {
    markLines.push({
      yAxis: props.threshold.alarm_high,
      lineStyle: { color: '#e63946', type: 'dashed', width: 1, opacity: 0.6 },
      label: { show: false },
    })
  }

  chart.setOption({
    grid: { top: 8, right: 8, bottom: 24, left: 42 },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
      axisLabel: { color: '#556677', fontSize: 10, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      axisLabel: { color: '#556677', fontSize: 10, fontFamily: 'JetBrains Mono' },
    },
    series: [
      {
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: lineColor, width: 2 },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: lineColor + '30' },
              { offset: 1, color: lineColor + '05' },
            ],
          },
        },
        markLine: markLines.length
          ? { silent: true, symbol: 'none', data: markLines }
          : undefined,
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e2a38',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#e8ecf1', fontFamily: 'JetBrains Mono', fontSize: 12 },
      formatter: (params: any) => {
        const p = params[0]
        return `${p.axisValue}<br/><b>${p.value} ${props.unit}</b>`
      },
    },
    animation: false,
  })
}

watch(() => props.data, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.sensor-chart-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 16px 10px;
  transition: border-color var(--transition-fast);
}

.sensor-chart-wrapper:hover {
  border-color: var(--border-default);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.chart-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-title {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.chart-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.value-num {
  font-family: var(--font-mono);
  font-size: 1.3rem;
  font-weight: 700;
  transition: color var(--transition-fast);
}

.value-num.status-normal { color: var(--color-healthy); }
.value-num.status-warning { color: var(--color-warning); }
.value-num.status-alarm { color: var(--color-alarm); animation: pulse-alarm 1.5s ease-in-out infinite; }
.value-num.status-offline { color: var(--text-muted); }

.value-unit {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.chart-container {
  height: 140px;
  width: 100%;
}

.threshold-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--border-subtle);
}

.threshold-label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.th-item {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 3px;
}

.th-item.warning {
  background: var(--color-warning-dim);
  color: var(--color-warning);
}

.th-item.alarm {
  background: var(--color-alarm-dim);
  color: var(--color-alarm);
}
</style>
