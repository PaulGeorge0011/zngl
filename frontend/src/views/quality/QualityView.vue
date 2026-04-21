<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">成品水分质量管理</h2>
        <p class="page-subtitle">MOISTURE QUALITY CONTROL</p>
      </div>
      <div class="header-actions">
        <el-button @click="showBrandDialog = true">管理牌号</el-button>
        <el-upload :show-file-list="false" :before-upload="handleImport" accept=".xlsx,.xls">
          <el-button type="success">导入Excel</el-button>
        </el-upload>
        <el-button type="primary" @click="openAddDialog">添加数据</el-button>
      </div>
    </div>

    <!-- Brand Filter & Stats -->
    <div class="control-bar">
      <el-select v-model="selectedBrand" placeholder="选择牌号" clearable @change="loadData" class="brand-select">
        <el-option v-for="b in brands" :key="b.id" :label="b.name" :value="b.id" />
      </el-select>

      <div v-if="selectedBrand && tableData.length > 0" class="quick-stats">
        <div class="stat-item">
          <span class="stat-label">样本数</span>
          <span class="stat-value">{{ tableData.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">平均水分</span>
          <span class="stat-value">{{ avgMoisture }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">标准差</span>
          <span class="stat-value">{{ stdDeviation }}</span>
        </div>
      </div>
    </div>

    <!-- Charts Section - Priority Display -->
    <div v-if="selectedBrand && tableData.length > 0" class="charts-section">
      <div class="chart-card primary-chart">
        <div class="chart-header">
          <h3 class="chart-title">成品水分趋势</h3>
          <div class="chart-legend">
            <span class="legend-item">
              <span class="legend-dot primary"></span>
              最近20条数据
            </span>
          </div>
        </div>
        <div ref="finishedChartRef" class="chart-container large"></div>
      </div>

      <div class="chart-grid">
        <div v-for="chart in secondaryCharts" :key="chart.key" class="chart-card">
          <div class="chart-header">
            <h4 class="chart-title small">{{ chart.title }}</h4>
          </div>
          <div :ref="(el) => { if (el) chartRefs[chart.key] = el as HTMLElement }" class="chart-container"></div>
        </div>
      </div>
    </div>

    <!-- Data Table - Compact View -->
    <div v-if="selectedBrand" class="table-section">
      <div class="table-header">
        <h3 class="section-title">数据记录</h3>
        <span class="record-count">共 {{ tableData.length }} 条</span>
      </div>

      <el-table :data="tableData" class="data-table" stripe>
        <el-table-column prop="sampling_date" label="日期" width="100" />
        <el-table-column prop="sample_number" label="样品编号" width="130" />
        <el-table-column prop="machine_stage" label="机台" width="80" />
        <el-table-column prop="finished_moisture" label="成品" width="80">
          <template #default="{ row }">
            <span class="data-value" :class="getMoistureClass(row.finished_moisture)">
              {{ row.finished_moisture ?? '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="drying_moisture" label="烘丝" width="80">
          <template #default="{ row }">
            <span class="data-value">{{ row.drying_moisture ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mixed_moisture" label="混合丝" width="90">
          <template #default="{ row }">
            <span class="data-value">{{ row.mixed_moisture ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cabinet_moisture" label="出柜" width="80">
          <template #default="{ row }">
            <span class="data-value">{{ row.cabinet_moisture ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rolling_moisture" label="卷制" width="80">
          <template #default="{ row }">
            <span class="data-value">{{ row.rolling_moisture ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="drying_mixed_diff" label="烘丝-混合丝" width="110">
          <template #default="{ row }">
            <span class="data-value diff">{{ row.drying_mixed_diff ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mixed_cabinet_diff" label="混合丝-出柜" width="110">
          <template #default="{ row }">
            <span class="data-value diff">{{ row.mixed_cabinet_diff ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cabinet_rolling_diff" label="出柜-卷制" width="110">
          <template #default="{ row }">
            <span class="data-value diff">{{ row.cabinet_rolling_diff ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rolling_finished_diff" label="卷制-成品" width="110">
          <template #default="{ row }">
            <span class="data-value diff">{{ row.rolling_finished_diff ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="烘丝-成品" width="110">
          <template #default="{ row }">
            <span class="data-value diff">{{ calculateDryingFinishedDiff(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="addition_method" label="加丝机" width="120" />
        <el-table-column prop="batch_number" label="批次号" width="110" />
        <el-table-column prop="shift" label="班次" width="70" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Empty State -->
    <div v-if="!selectedBrand" class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="8" y="8" width="48" height="48" rx="4"/>
          <path d="M8 20h48M20 8v48"/>
        </svg>
      </div>
      <p class="empty-text">请选择牌号查看数据</p>
    </div>

    <!-- Dialogs -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="form" label-width="100px" class="compact-form">
        <div class="form-grid">
          <el-form-item label="牌号">
            <el-select v-model="form.brand" placeholder="选择牌号">
              <el-option v-for="b in brands" :key="b.id" :label="b.name" :value="b.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="取样日期">
            <el-date-picker v-model="form.sampling_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="样品编号">
            <el-input v-model="form.sample_number" />
          </el-form-item>
          <el-form-item label="机台">
            <el-input v-model="form.machine_stage" />
          </el-form-item>
          <el-form-item label="成品水分">
            <el-input-number v-model="form.finished_moisture" :precision="2" :step="0.01" />
          </el-form-item>
          <el-form-item label="烘丝水分">
            <el-input-number v-model="form.drying_moisture" :precision="2" :step="0.01" />
          </el-form-item>
          <el-form-item label="混合丝水分">
            <el-input-number v-model="form.mixed_moisture" :precision="2" :step="0.01" />
          </el-form-item>
          <el-form-item label="出柜水分">
            <el-input-number v-model="form.cabinet_moisture" :precision="2" :step="0.01" />
          </el-form-item>
          <el-form-item label="卷制水分">
            <el-input-number v-model="form.rolling_moisture" :precision="2" :step="0.01" />
          </el-form-item>
          <el-form-item label="加丝机">
            <el-input v-model="form.addition_method" />
          </el-form-item>
          <el-form-item label="批次号">
            <el-input v-model="form.batch_number" />
          </el-form-item>
          <el-form-item label="班次">
            <el-input v-model="form.shift" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBrandDialog" title="牌号管理" width="500px">
      <div style="margin-bottom: 16px">
        <el-input v-model="newBrandName" placeholder="输入牌号名称" style="width: 300px; margin-right: 8px" />
        <el-button type="primary" @click="addBrand">添加</el-button>
      </div>
      <el-table :data="brands" border>
        <el-table-column prop="name" label="牌号名称" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDeleteBrand(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import * as qualityApi from '@/api/quality'
import type { Brand, MoistureData } from '@/api/quality'

const brands = ref<Brand[]>([])
const selectedBrand = ref<number>()
const tableData = ref<MoistureData[]>([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const editingId = ref<number>()
const showBrandDialog = ref(false)
const newBrandName = ref('')

const form = ref({
  brand: undefined as number | undefined,
  sampling_date: '',
  sample_number: '',
  machine_number: '',
  machine_stage: '',
  finished_moisture: null as number | null,
  powder_rate: null as number | null,
  addition_method: '',
  batch_number: '',
  shift: '',
  drying_moisture: null as number | null,
  mixed_moisture: null as number | null,
  cabinet_moisture: null as number | null,
  rolling_moisture: null as number | null,
})

const finishedChartRef = ref<HTMLElement | null>(null)
const chartRefs = ref<Record<string, HTMLElement | null>>({})
const chartInstances = ref<Record<string, echarts.ECharts>>({})

const secondaryCharts = [
  { key: 'drying', title: '烘丝水分', field: 'drying_moisture', yMin: 12.5, yMax: 14.0 },
  { key: 'mixed', title: '混合丝水分', field: 'mixed_moisture', yMin: 12.0, yMax: 14.0 },
  { key: 'cabinet', title: '出柜水分', field: 'cabinet_moisture', yMin: 12.0, yMax: 14.0 },
  { key: 'rolling', title: '卷制水分', field: 'rolling_moisture', yMin: 12.0, yMax: 14.0 },
]

const calculateDryingFinishedDiff = (row: MoistureData) => {
  if (row.drying_moisture != null && row.finished_moisture != null) {
    return (row.drying_moisture - row.finished_moisture).toFixed(2)
  }
  return '-'
}

const avgMoisture = computed(() => {
  const values = tableData.value.map(d => d.finished_moisture).filter(v => v != null) as number[]
  if (values.length === 0) return '-'
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  return avg.toFixed(2)
})

const stdDeviation = computed(() => {
  const values = tableData.value.map(d => d.finished_moisture).filter(v => v != null) as number[]
  if (values.length < 2) return '-'
  const avg = parseFloat(avgMoisture.value)
  const variance = values.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / values.length
  return Math.sqrt(variance).toFixed(2)
})

const getMoistureClass = (value: number | null) => {
  if (value == null) return ''
  if (value < 12.0) return 'low'
  if (value > 13.0) return 'high'
  return 'normal'
}

const loadBrands = async () => {
  try {
    const res = await qualityApi.getBrands()
    brands.value = (res.data as any).results || res.data || []
  } catch (e) {
    brands.value = []
    ElMessage.error('加载牌号失败')
  }
}

const loadData = async () => {
  if (!selectedBrand.value) {
    tableData.value = []
    return
  }
  try {
    const res = await qualityApi.getMoistureData(selectedBrand.value)
    tableData.value = (res.data as any).results || res.data || []
    await nextTick()
    renderCharts()
  } catch (e) {
    tableData.value = []
    ElMessage.error('加载数据失败')
  }
}

const openAddDialog = () => {
  editingId.value = undefined
  form.value = {
    brand: selectedBrand.value,
    sampling_date: '',
    sample_number: '',
    machine_number: '',
    machine_stage: '',
    finished_moisture: null,
    powder_rate: null,
    addition_method: '',
    batch_number: '',
    shift: '',
    drying_moisture: null,
    mixed_moisture: null,
    cabinet_moisture: null,
    rolling_moisture: null,
  }
  dialogTitle.value = '添加数据'
  dialogVisible.value = true
}

const openEditDialog = (row: MoistureData) => {
  editingId.value = row.id
  form.value = {
    brand: row.brand,
    sampling_date: row.sampling_date || '',
    sample_number: row.sample_number || '',
    machine_number: row.machine_number || '',
    machine_stage: row.machine_stage || '',
    finished_moisture: row.finished_moisture,
    powder_rate: row.powder_rate,
    addition_method: row.addition_method || '',
    batch_number: row.batch_number || '',
    shift: row.shift || '',
    drying_moisture: row.drying_moisture,
    mixed_moisture: row.mixed_moisture,
    cabinet_moisture: row.cabinet_moisture,
    rolling_moisture: row.rolling_moisture,
  }
  dialogTitle.value = '编辑数据'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingId.value) {
      await qualityApi.updateMoistureData(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await qualityApi.createMoistureData(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确认删除该数据？', '提示', { type: 'warning' })
    await qualityApi.deleteMoistureData(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const addBrand = async () => {
  if (!newBrandName.value.trim()) return
  try {
    await qualityApi.createBrand({ name: newBrandName.value.trim() })
    ElMessage.success('添加成功')
    newBrandName.value = ''
    loadBrands()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

const handleDeleteBrand = async (id: number) => {
  try {
    await ElMessageBox.confirm('删除牌号将同时删除其所有数据，确认删除？', '警告', { type: 'warning' })
    await qualityApi.deleteBrand(id)
    ElMessage.success('删除成功')
    loadBrands()
    if (selectedBrand.value === id) {
      selectedBrand.value = undefined
      tableData.value = []
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleImport = async (file: File) => {
  const loading = ElMessage({ message: '导入中...', type: 'info', duration: 0 })
  try {
    const res = await qualityApi.importExcel(file)
    loading.close()
    const result = res.data as any
    ElMessage.success(`导入完成：新增${result.created}条，跳过${result.skipped}条`)
    if (result.errors?.length > 0) {
      console.error('导入错误:', result.errors)
    }
    loadBrands()
    if (selectedBrand.value) loadData()
  } catch (e: any) {
    loading.close()
    ElMessage.error(e.response?.data?.error || '导入失败')
  }
  return false
}

const renderCharts = () => {
  const recentData = tableData.value.slice(0, 30).reverse()

  // Primary chart - Finished Moisture
  if (finishedChartRef.value) {
    if (!chartInstances.value.finished) {
      chartInstances.value.finished = echarts.init(finishedChartRef.value)
    }
    const validData = recentData.filter(d => d.finished_moisture != null)
    const option: EChartsOption = {
      grid: { left: 60, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: validData.map(d => d.sampling_date), show: false },
      yAxis: {
        type: 'value',
        min: 11.5,
        max: 13.5,
        interval: 0.5,
        axisLabel: { fontSize: 12, color: '#8b949e' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
      },
      series: [{
        type: 'line',
        data: validData.map(d => d.finished_moisture),
        smooth: true,
        lineStyle: { width: 3, color: '#00ffa3' },
        itemStyle: { color: '#00ffa3' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(0, 255, 163, 0.3)' },
          { offset: 1, color: 'rgba(0, 255, 163, 0)' }
        ]}},
        markPoint: {
          data: [
            { type: 'max', name: '最大', label: { fontSize: 11, color: '#fff', backgroundColor: '#f85149', padding: 4, borderRadius: 3 } },
            { type: 'min', name: '最小', label: { fontSize: 11, color: '#fff', backgroundColor: '#58a6ff', padding: 4, borderRadius: 3 } }
          ],
          itemStyle: { borderWidth: 2, borderColor: '#fff' }
        }
      }],
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(22, 27, 34, 0.95)',
        borderColor: '#30363d',
        textStyle: { color: '#c9d1d9', fontSize: 12 },
        formatter: (params: any) => {
          const item = validData[params.dataIndex]
          const dryingFinished = item.drying_moisture != null && item.finished_moisture != null
            ? (item.drying_moisture - item.finished_moisture).toFixed(2) : '-'
          return `<div style="padding: 4px">
            <div style="color: #00ffa3; font-weight: 600; margin-bottom: 6px">${item.sampling_date || '-'}</div>
            <div><span style="color: #8b949e">样品:</span> ${item.sample_number || '-'}</div>
            <div><span style="color: #8b949e">机台号:</span> ${item.machine_number || '-'}</div>
            <div><span style="color: #8b949e">机台:</span> ${item.machine_stage || '-'}</div>
            <div><span style="color: #8b949e">加丝机:</span> ${item.addition_method || '-'}</div>
            <div><span style="color: #8b949e">批次:</span> ${item.batch_number || '-'}</div>
            <div><span style="color: #8b949e">班次:</span> ${item.shift || '-'}</div>
            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #30363d">
              <div><span style="color: #8b949e">成品:</span> <strong>${item.finished_moisture ?? '-'}</strong></div>
              <div><span style="color: #8b949e">烘丝:</span> ${item.drying_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">混合丝:</span> ${item.mixed_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">出柜:</span> ${item.cabinet_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">卷制:</span> ${item.rolling_moisture ?? '-'}</div>
              <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #30363d">
                <div><span style="color: #8b949e">出柜-卷制:</span> ${item.cabinet_rolling_diff ?? '-'}</div>
                <div><span style="color: #8b949e">烘丝-成品:</span> ${dryingFinished}</div>
              </div>
            </div>
          </div>`
        }
      }
    }
    chartInstances.value.finished.setOption(option)
  }

  // Secondary charts
  secondaryCharts.forEach(chart => {
    const el = chartRefs.value[chart.key]
    if (!el) return
    if (!chartInstances.value[chart.key]) {
      chartInstances.value[chart.key] = echarts.init(el)
    }
    const validData = recentData.filter(d => d[chart.field as keyof MoistureData] != null)
    const option: EChartsOption = {
      grid: { left: 50, right: 20, top: 20, bottom: 20 },
      xAxis: { type: 'category', data: validData.map(d => d.sampling_date), show: false },
      yAxis: {
        type: 'value',
        min: chart.yMin,
        max: chart.yMax,
        axisLabel: { fontSize: 11, color: '#8b949e' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } }
      },
      series: [{
        type: 'line',
        data: validData.map(d => d[chart.field as keyof MoistureData] as number),
        smooth: true,
        lineStyle: { width: 2, color: '#58a6ff' },
        itemStyle: { color: '#58a6ff' },
        markPoint: {
          data: [
            { type: 'max', name: '最大', label: { fontSize: 10, color: '#fff', backgroundColor: '#f85149', padding: 3, borderRadius: 2 } },
            { type: 'min', name: '最小', label: { fontSize: 10, color: '#fff', backgroundColor: '#58a6ff', padding: 3, borderRadius: 2 } }
          ],
          itemStyle: { borderWidth: 2, borderColor: '#fff' }
        }
      }],
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(22, 27, 34, 0.95)',
        borderColor: '#30363d',
        textStyle: { color: '#c9d1d9', fontSize: 11 },
        formatter: (params: any) => {
          const item = validData[params.dataIndex]
          const dryingFinished = item.drying_moisture != null && item.finished_moisture != null
            ? (item.drying_moisture - item.finished_moisture).toFixed(2) : '-'
          return `<div style="padding: 4px">
            <div style="font-weight: 600; margin-bottom: 4px">${item.sampling_date || '-'}</div>
            <div><span style="color: #8b949e">样品:</span> ${item.sample_number || '-'}</div>
            <div><span style="color: #8b949e">机台号:</span> ${item.machine_number || '-'}</div>
            <div><span style="color: #8b949e">机台:</span> ${item.machine_stage || '-'}</div>
            <div><span style="color: #8b949e">加丝机:</span> ${item.addition_method || '-'}</div>
            <div><span style="color: #8b949e">批次:</span> ${item.batch_number || '-'}</div>
            <div><span style="color: #8b949e">班次:</span> ${item.shift || '-'}</div>
            <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #30363d">
              <div><span style="color: #8b949e">成品:</span> ${item.finished_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">烘丝:</span> ${item.drying_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">混合丝:</span> ${item.mixed_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">出柜:</span> ${item.cabinet_moisture ?? '-'}</div>
              <div><span style="color: #8b949e">卷制:</span> ${item.rolling_moisture ?? '-'}</div>
              <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #30363d">
                <div><span style="color: #8b949e">出柜-卷制:</span> ${item.cabinet_rolling_diff ?? '-'}</div>
                <div><span style="color: #8b949e">烘丝-成品:</span> ${dryingFinished}</div>
              </div>
            </div>
          </div>`
        }
      }
    }
    chartInstances.value[chart.key].setOption(option)
  })
}

onMounted(() => {
  loadBrands()
})
</script>

<style scoped>
.page-subtitle {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.1em;
  margin-top: 4px;
}

.control-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.brand-select {
  width: 220px;
}

.quick-stats {
  display: flex;
  gap: 32px;
  margin-left: auto;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-accent);
}

.charts-section {
  margin-bottom: 32px;
}

.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
}

.primary-chart {
  border-left: 3px solid var(--color-healthy);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-title.small {
  font-size: 0.9rem;
}

.chart-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.primary {
  background: var(--color-healthy);
}

.chart-container {
  height: 200px;
}

.chart-container.large {
  height: 320px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.table-section {
  margin-top: 32px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.record-count {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-muted);
}

.data-table {
  font-size: 0.9rem;
}

.data-value {
  font-family: var(--font-mono);
  font-weight: 600;
}

.data-value.normal {
  color: var(--color-healthy);
}

.data-value.low {
  color: var(--color-info);
}

.data-value.high {
  color: var(--color-warning);
}

.data-value.diff {
  color: var(--text-muted);
  font-size: 0.85rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-muted);
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-text {
  font-size: 0.95rem;
}

.compact-form .form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px 24px;
}

@media (max-width: 960px) {
  .header-actions,
  .control-bar,
  .results-header,
  .table-header {
    flex-wrap: wrap;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
  }

  .control-bar {
    gap: 14px;
    padding: 14px;
  }

  .brand-select {
    width: 100%;
  }

  .quick-stats {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  .chart-container.large {
    height: 260px;
  }

  .table-section :deep(.el-table) {
    min-width: 1400px;
  }

  .compact-form .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}

@media (max-width: 640px) {
  .chart-card {
    padding: 14px;
  }

  .chart-header,
  .table-header {
    gap: 8px;
  }

  .chart-legend {
    width: 100%;
  }

  .chart-container {
    height: 180px;
  }

  .chart-container.large {
    height: 220px;
  }

  .empty-state {
    padding: 40px 16px;
  }
}
</style>
