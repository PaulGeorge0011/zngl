<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">执行巡检</h2>
        <p class="page-subtitle" v-if="room && template">{{ room.name }} · {{ template.role_display }}</p>
      </div>
      <router-link to="/safety/dustroom" class="btn-back">← 返回</router-link>
    </div>

    <div v-if="loadError" class="error-box">{{ loadError }}</div>

    <div v-else-if="loading" class="loading-hint">加载巡检模板...</div>

    <template v-else-if="template">
      <div class="inspect-form">
        <div v-for="(item, idx) in template.items" :key="item.id" class="inspect-item" :class="{ abnormal: results[item.id] && !results[item.id].is_normal }">
          <div class="item-header">
            <span class="item-index">{{ idx + 1 }}</span>
            <span class="item-name">{{ item.name }}</span>
            <span v-if="item.required" class="item-required">*</span>
          </div>

          <div class="item-body">
            <!-- checkbox type: 正常/异常 -->
            <template v-if="item.item_type === 'checkbox'">
              <div class="check-group">
                <button class="check-btn normal" :class="{ active: results[item.id]?.is_normal === true }" @click="setResult(item.id, 'normal', true)">
                  ✓ 正常
                </button>
                <button class="check-btn abnormal" :class="{ active: results[item.id]?.is_normal === false }" @click="setResult(item.id, 'abnormal', false)">
                  ✗ 异常
                </button>
              </div>
            </template>

            <!-- number type -->
            <template v-else-if="item.item_type === 'number'">
              <div class="number-input-wrap">
                <el-input-number v-model="results[item.id].numValue" :controls="false" size="small" @change="onNumChange(item.id)" />
                <span v-if="item.unit" class="unit-label">{{ item.unit }}</span>
              </div>
              <div class="normal-toggle">
                <label><input type="checkbox" v-model="results[item.id].is_normal" /> 正常</label>
              </div>
            </template>

            <!-- text type -->
            <template v-else-if="item.item_type === 'text'">
              <el-input v-model="results[item.id].value" size="small" placeholder="请填写" />
              <div class="normal-toggle">
                <label><input type="checkbox" v-model="results[item.id].is_normal" /> 正常</label>
              </div>
            </template>

            <!-- select type -->
            <template v-else-if="item.item_type === 'select'">
              <el-select v-model="results[item.id].value" size="small" placeholder="请选择">
                <el-option v-for="opt in item.options" :key="opt" :label="opt" :value="opt" />
              </el-select>
              <div class="normal-toggle">
                <label><input type="checkbox" v-model="results[item.id].is_normal" /> 正常</label>
              </div>
            </template>

            <!-- 异常备注 -->
            <div v-if="results[item.id] && !results[item.id].is_normal" class="remark-input">
              <el-input v-model="results[item.id].remark" size="small" type="textarea" :rows="2" placeholder="请描述异常情况" />
            </div>
          </div>
        </div>
      </div>

      <div class="form-footer">
        <div class="overall-remark">
          <label>整体备注（选填）</label>
          <el-input v-model="overallRemark" type="textarea" :rows="2" placeholder="对本次巡检的整体补充说明" />
        </div>
        <div class="submit-bar">
          <span class="progress-hint">已填 {{ filledCount }} / {{ template.items.length }} 项</span>
          <el-button type="primary" size="large" :loading="submitting" :disabled="!canSubmit" @click="submit">
            提交巡检记录
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dustroomApi } from '@/api/dustroom'
import type { DustRoom, InspectionTemplate } from '@/api/dustroom'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)

const room = ref<DustRoom | null>(null)
const template = ref<InspectionTemplate | null>(null)
const overallRemark = ref('')

interface ResultEntry {
  value: string
  numValue: number | null
  is_normal: boolean
  remark: string
}
const results = reactive<Record<number, ResultEntry>>({})

const filledCount = computed(() => {
  if (!template.value) return 0
  return template.value.items.filter(item => {
    const r = results[item.id]
    if (!r) return false
    if (item.item_type === 'checkbox') return r.value !== ''
    if (item.item_type === 'number') return r.numValue !== null
    return r.value !== ''
  }).length
})

const canSubmit = computed(() => {
  if (!template.value) return false
  return template.value.items.filter(i => i.required).every(item => {
    const r = results[item.id]
    if (!r) return false
    if (item.item_type === 'checkbox') return r.value !== ''
    if (item.item_type === 'number') return r.numValue !== null
    return r.value !== ''
  })
})

function setResult(itemId: number, value: string, isNormal: boolean) {
  results[itemId].value = value
  results[itemId].is_normal = isNormal
}

function onNumChange(itemId: number) {
  const r = results[itemId]
  r.value = r.numValue !== null ? String(r.numValue) : ''
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const roomId = Number(route.params.roomId)
    const templateId = Number(route.query.template)
    if (!roomId || !templateId) {
      loadError.value = '参数不完整'
      return
    }

    const [roomsRes, tplRes] = await Promise.all([
      dustroomApi.getRooms(),
      dustroomApi.getTemplate(templateId),
    ])

    room.value = roomsRes.data.find(r => r.id === roomId) || null
    if (!room.value) { loadError.value = '除尘房不存在'; return }

    template.value = tplRes.data

    for (const item of tplRes.data.items) {
      results[item.id] = { value: '', numValue: null, is_normal: true, remark: '' }
    }
  } catch {
    loadError.value = '加载失败'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!template.value || !room.value) return

  try {
    await ElMessageBox.confirm('确认提交巡检记录？提交后不可修改。', '确认提交', { type: 'warning' })
  } catch { return }

  submitting.value = true
  try {
    const payload = {
      dust_room: room.value.id,
      template: template.value.id,
      remark: overallRemark.value,
      results: template.value.items.map(item => {
        const r = results[item.id]
        return {
          item: item.id,
          value: item.item_type === 'number' ? String(r.numValue ?? '') : r.value,
          is_normal: r.is_normal,
          remark: r.remark,
        }
      }),
    }
    await dustroomApi.submitRecord(payload)
    ElMessage.success('巡检记录已提交')
    router.push('/safety/dustroom')
  } finally { submitting.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back {
  color: var(--color-accent); text-decoration: none; font-size: 0.85rem;
  padding: 6px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-default);
}
.btn-back:hover { background: var(--bg-card); }
.error-box { padding: 16px; background: rgba(255,80,80,0.1); color: #f55; border-radius: var(--radius-md); margin-top: 16px; }
.loading-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }

.inspect-form { margin-top: 20px; display: flex; flex-direction: column; gap: 12px; }
.inspect-item {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 16px; transition: border-color 0.2s;
}
.inspect-item.abnormal { border-color: var(--color-warning); border-left-width: 3px; }
.item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.item-index {
  width: 24px; height: 24px; border-radius: 50%; background: var(--color-accent);
  color: #fff; font-size: 0.75rem; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.item-name { font-weight: 500; color: var(--text-primary); font-size: 0.9rem; }
.item-required { color: #f55; font-weight: 700; }

.item-body { display: flex; flex-direction: column; gap: 8px; }
.check-group { display: flex; gap: 8px; }
.check-btn {
  flex: 1; padding: 10px; border: 2px solid var(--border-default); border-radius: var(--radius-md);
  background: transparent; color: var(--text-secondary); font-size: 0.9rem; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.check-btn.normal.active { border-color: var(--color-healthy); color: var(--color-healthy); background: rgba(0,212,170,0.08); }
.check-btn.abnormal.active { border-color: var(--color-warning); color: var(--color-warning); background: rgba(255,170,0,0.08); }
.check-btn:hover { border-color: var(--color-accent); }

.number-input-wrap { display: flex; align-items: center; gap: 8px; }
.unit-label { color: var(--text-muted); font-size: 0.85rem; }
.normal-toggle { font-size: 0.8rem; color: var(--text-muted); }
.normal-toggle label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.remark-input { margin-top: 4px; }

.form-footer { margin-top: 24px; }
.overall-remark { margin-bottom: 16px; }
.overall-remark label { display: block; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }
.submit-bar { display: flex; justify-content: space-between; align-items: center; }
.progress-hint { font-size: 0.85rem; color: var(--text-muted); font-family: var(--font-mono); }
</style>
