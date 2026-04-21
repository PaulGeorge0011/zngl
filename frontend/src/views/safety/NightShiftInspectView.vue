<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">执行夜班检查</h2>
        <p class="page-subtitle">{{ new Date().toLocaleDateString('zh-CN') }}</p>
      </div>
      <router-link to="/safety/nightshift" class="btn-back">← 返回</router-link>
    </div>

    <div v-if="loading" class="loading-hint">加载检查项...</div>
    <div v-else-if="categories.length === 0" class="empty-hint">
      暂无检查分类，请先前往 <router-link to="/safety/nightshift/admin">管理配置</router-link> 添加。
    </div>

    <template v-else>
      <!-- 分类 Tab -->
      <el-tabs v-model="activeTab" class="check-tabs">
        <el-tab-pane v-for="cat in categories" :key="cat.id" :label="cat.name" :name="String(cat.id)">
          <div class="check-list">
            <div v-for="entry in getEntries(cat.id)" :key="entry.key" class="check-item" :class="{ abnormal: !entry.is_normal }">
              <div class="check-name">
                <span v-if="entry.isCustom" class="custom-badge">自填</span>
                {{ entry.name }}
              </div>
              <div class="check-controls">
                <button class="ctl-btn normal" :class="{ active: entry.is_normal }" @click="entry.is_normal = true">✓ 正常</button>
                <button class="ctl-btn abnormal" :class="{ active: !entry.is_normal }" @click="entry.is_normal = false">✗ 异常</button>
              </div>
              <div v-if="!entry.is_normal" class="remark-row">
                <el-input v-model="entry.remark" size="small" placeholder="异常情况说明" />
              </div>
              <div v-if="entry.isCustom" class="remove-row">
                <el-button link size="small" type="danger" @click="removeCustomEntry(cat.id, entry.key)">移除</el-button>
              </div>
            </div>
          </div>

          <!-- 自填添加按钮（仅 allows_custom 分类） -->
          <div v-if="cat.allows_custom" class="add-custom">
            <el-input v-model="customInputs[cat.id]" size="small" placeholder="输入自定义检查部位" class="custom-input" @keyup.enter="addCustomEntry(cat.id)" />
            <el-button size="small" type="primary" :disabled="!customInputs[cat.id]?.trim()" @click="addCustomEntry(cat.id)">添加</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 问题区 -->
      <div class="issues-section">
        <div class="issues-header">
          <h3 class="issues-title">发现问题</h3>
          <el-button size="small" type="primary" @click="addIssue">+ 添加问题</el-button>
        </div>
        <div v-if="issues.length === 0" class="no-issues">无发现问题</div>
        <div v-for="(issue, idx) in issues" :key="idx" class="issue-card">
          <div class="issue-num">问题 {{ idx + 1 }}</div>
          <el-form label-width="80px" size="small">
            <el-form-item label="问题描述">
              <el-input v-model="issue.description" type="textarea" :rows="2" placeholder="描述发现的问题" />
            </el-form-item>
            <el-form-item label="整改情况">
              <el-input v-model="issue.rectification" type="textarea" :rows="2" placeholder="整改措施或情况说明" />
            </el-form-item>
            <el-form-item label="已整改">
              <el-switch v-model="issue.is_resolved" />
            </el-form-item>
          </el-form>
          <el-button link size="small" type="danger" @click="issues.splice(idx, 1)">移除此问题</el-button>
        </div>
      </div>

      <!-- 备注和提交 -->
      <div class="form-footer">
        <div class="overall-remark">
          <label>整体备注（选填）</label>
          <el-input v-model="overallRemark" type="textarea" :rows="2" placeholder="对本次夜班检查的整体补充说明" />
        </div>
        <div class="submit-bar">
          <span class="progress-hint">检查项 {{ totalEntries }} 项 · 问题 {{ issues.length }} 条</span>
          <el-button type="primary" size="large" :loading="submitting" @click="submit">提交检查记录</el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftCategoryListItem, NightShiftCheckItem } from '@/api/nightshift'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const overallRemark = ref('')
const dutyId = ref<number | null>(null)

interface CheckEntry {
  key: string
  category_id: number
  item_id: number | null
  name: string
  isCustom: boolean
  is_normal: boolean
  remark: string
}

interface IssueEntry {
  description: string
  rectification: string
  is_resolved: boolean
}

const categories = ref<(NightShiftCategoryListItem & { items?: NightShiftCheckItem[] })[]>([])
const activeTab = ref('')
const entries = reactive<Record<number, CheckEntry[]>>({})
const customInputs = reactive<Record<number, string>>({})
const issues = ref<IssueEntry[]>([])
let customCounter = 0

function getEntries(catId: number): CheckEntry[] {
  return entries[catId] || []
}

const totalEntries = computed(() => {
  return Object.values(entries).reduce((sum, arr) => sum + arr.length, 0)
})

function addCustomEntry(catId: number) {
  const name = customInputs[catId]?.trim()
  if (!name) return
  entries[catId].push({
    key: `custom-${++customCounter}`,
    category_id: catId,
    item_id: null,
    name,
    isCustom: true,
    is_normal: true,
    remark: '',
  })
  customInputs[catId] = ''
}

function removeCustomEntry(catId: number, key: string) {
  const idx = entries[catId].findIndex(e => e.key === key)
  if (idx >= 0) entries[catId].splice(idx, 1)
}

function addIssue() {
  issues.value.push({ description: '', rectification: '', is_resolved: false })
}

async function loadData() {
  loading.value = true
  const qDuty = Number(route.query.duty)
  if (!qDuty) {
    ElMessage.error('缺少排班信息，请从排班表进入')
    router.push('/safety/nightshift')
    return
  }
  dutyId.value = qDuty

  try {
    const { data: cats } = await nightshiftApi.getCategories(true)
    const enriched = await Promise.all(cats.map(async cat => {
      const { data: items } = await nightshiftApi.getItems(cat.id, true)
      return { ...cat, items }
    }))
    categories.value = enriched
    if (enriched.length) activeTab.value = String(enriched[0].id)

    for (const cat of enriched) {
      entries[cat.id] = (cat.items || []).map(item => ({
        key: `item-${item.id}`,
        category_id: cat.id,
        item_id: item.id,
        name: item.name,
        isCustom: false,
        is_normal: true,
        remark: '',
      }))
      customInputs[cat.id] = ''
    }
  } finally { loading.value = false }
}

async function submit() {
  try {
    await ElMessageBox.confirm('确认提交夜班检查记录？提交后不可修改。', '确认提交', { type: 'warning' })
  } catch { return }

  const validIssues = issues.value.filter(i => i.description.trim())

  submitting.value = true
  try {
    const results = Object.values(entries).flat().map(e => ({
      category: e.category_id,
      item: e.item_id || undefined,
      custom_name: e.isCustom ? e.name : '',
      is_normal: e.is_normal,
      remark: e.remark,
    }))

    await nightshiftApi.submitRecord({
      duty_id: dutyId.value!,
      results,
      issues: validIssues,
      overall_remark: overallRemark.value,
    })
    ElMessage.success('夜班检查记录已提交')
    router.push('/safety/nightshift')
  } finally { submitting.value = false }
}

onMounted(loadData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back { color: var(--color-accent); text-decoration: none; font-size: 0.85rem; padding: 6px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-default); }
.btn-back:hover { background: var(--bg-card); }
.loading-hint, .empty-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }
.empty-hint a { color: var(--color-accent); }

.check-tabs { margin-top: 16px; }
.check-list { display: flex; flex-direction: column; gap: 8px; }
.check-item {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 14px; transition: border-color 0.2s;
}
.check-item.abnormal { border-color: var(--color-warning); border-left-width: 3px; }
.check-name { font-weight: 500; color: var(--text-primary); font-size: 0.9rem; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
.custom-badge { font-size: 0.7rem; padding: 1px 6px; border-radius: 8px; background: rgba(74,158,255,0.15); color: var(--color-accent); font-weight: 600; }
.check-controls { display: flex; gap: 8px; }
.ctl-btn {
  flex: 1; padding: 8px; border: 2px solid var(--border-default); border-radius: var(--radius-md);
  background: transparent; color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.ctl-btn.normal.active { border-color: var(--color-healthy); color: var(--color-healthy); background: rgba(0,212,170,0.08); }
.ctl-btn.abnormal.active { border-color: var(--color-warning); color: var(--color-warning); background: rgba(255,170,0,0.08); }
.ctl-btn:hover { border-color: var(--color-accent); }
.remark-row { margin-top: 8px; }
.remove-row { margin-top: 4px; text-align: right; }

.add-custom { display: flex; gap: 8px; margin-top: 12px; }
.custom-input { flex: 1; }

.issues-section { margin-top: 28px; }
.issues-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.issues-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); }
.no-issues { padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem; background: var(--bg-card); border-radius: var(--radius-md); }
.issue-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 16px; margin-bottom: 10px;
}
.issue-num { font-weight: 600; font-size: 0.85rem; color: var(--color-accent); margin-bottom: 10px; }

.form-footer { margin-top: 24px; }
.overall-remark { margin-bottom: 16px; }
.overall-remark label { display: block; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px; }
.submit-bar { display: flex; justify-content: space-between; align-items: center; }
.progress-hint { font-size: 0.85rem; color: var(--text-muted); }
</style>
