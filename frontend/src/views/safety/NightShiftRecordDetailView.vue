<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">检查详情</h2>
        <p class="page-subtitle" v-if="record">{{ record.inspection_date }} · {{ record.inspector_display.display_name }}</p>
      </div>
      <button class="btn-back" @click="$router.back()">← 返回</button>
    </div>

    <div v-if="loading" class="loading-hint">加载中...</div>

    <template v-else-if="record">
      <div class="info-card">
        <div class="info-row"><span class="info-label">巡检人</span><span>{{ record.inspector_display.display_name }}</span></div>
        <div class="info-row"><span class="info-label">巡检日期</span><span>{{ record.inspection_date }}</span></div>
        <div class="info-row"><span class="info-label">提交时间</span><span>{{ record.submitted_at || '-' }}</span></div>
        <div class="info-row">
          <span class="info-label">状态</span>
          <el-tag :type="record.has_issues ? 'warning' : 'success'" size="small">{{ record.has_issues ? '存在问题' : '全部正常' }}</el-tag>
        </div>
        <div v-if="record.overall_remark" class="info-row full">
          <span class="info-label">备注</span><span>{{ record.overall_remark }}</span>
        </div>
      </div>

      <!-- 按分类展示检查结果 -->
      <div v-for="catName in categoryNames" :key="catName" class="section">
        <h3 class="section-title">{{ catName }}</h3>
        <div class="results-list">
          <div v-for="r in resultsByCategory[catName]" :key="r.id" class="result-item" :class="{ abnormal: !r.is_normal }">
            <div class="result-header">
              <span class="result-name">
                <span v-if="r.custom_name && !r.item" class="custom-badge">自填</span>
                {{ r.item_name }}
              </span>
              <el-tag :type="r.is_normal ? 'success' : 'danger'" size="small">{{ r.is_normal ? '正常' : '异常' }}</el-tag>
            </div>
            <div v-if="r.remark" class="result-remark">{{ r.remark }}</div>
          </div>
        </div>
      </div>

      <!-- 问题列表 -->
      <div v-if="record.issues.length" class="section">
        <h3 class="section-title issue-title">发现问题 ({{ record.issues.length }})</h3>
        <div v-for="(issue, idx) in record.issues" :key="issue.id" class="issue-card" :class="{ resolved: issue.is_resolved }">
          <div class="issue-header">
            <span class="issue-num">问题 {{ idx + 1 }}</span>
            <el-tag :type="issue.is_resolved ? 'success' : 'warning'" size="small">{{ issue.is_resolved ? '已整改' : '未整改' }}</el-tag>
          </div>
          <div class="issue-field"><span class="field-label">问题描述：</span>{{ issue.description }}</div>
          <div v-if="issue.rectification" class="issue-field"><span class="field-label">整改情况：</span>{{ issue.rectification }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { nightshiftApi } from '@/api/nightshift'
import type { NightShiftRecordDetail } from '@/api/nightshift'

const route = useRoute()
const loading = ref(true)
const record = ref<NightShiftRecordDetail | null>(null)

const categoryNames = computed(() => {
  if (!record.value) return []
  const names = new Set(record.value.results.map(r => r.category_name))
  return Array.from(names)
})

const resultsByCategory = computed(() => {
  if (!record.value) return {}
  const map: Record<string, typeof record.value.results> = {}
  for (const r of record.value.results) {
    if (!map[r.category_name]) map[r.category_name] = []
    map[r.category_name].push(r)
  }
  return map
})

onMounted(async () => {
  try {
    const { data } = await nightshiftApi.getRecord(Number(route.params.id))
    record.value = data
  } finally { loading.value = false }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back { color: var(--color-accent); background: transparent; border: 1px solid var(--border-default); padding: 6px 12px; border-radius: var(--radius-md); font-size: 0.85rem; cursor: pointer; }
.btn-back:hover { background: var(--bg-card); }
.loading-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }

.info-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 20px; margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px;
}
.info-row { display: flex; gap: 8px; align-items: center; font-size: 0.9rem; }
.info-row.full { grid-column: 1 / -1; }
.info-label { color: var(--text-muted); min-width: 70px; flex-shrink: 0; }

.section { margin-top: 24px; }
.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
.issue-title { color: var(--color-warning); }

.results-list { display: flex; flex-direction: column; gap: 6px; }
.result-item {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 12px; transition: border-color 0.2s;
}
.result-item.abnormal { border-color: var(--color-warning); border-left-width: 3px; }
.result-header { display: flex; justify-content: space-between; align-items: center; }
.result-name { font-weight: 500; color: var(--text-primary); font-size: 0.9rem; display: flex; align-items: center; gap: 6px; }
.custom-badge { font-size: 0.7rem; padding: 1px 6px; border-radius: 8px; background: rgba(74,158,255,0.15); color: var(--color-accent); font-weight: 600; }
.result-remark { margin-top: 6px; font-size: 0.85rem; color: var(--color-warning); }

.issue-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 16px; margin-bottom: 8px; border-left: 3px solid var(--color-warning);
}
.issue-card.resolved { border-left-color: var(--color-healthy); }
.issue-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.issue-num { font-weight: 600; font-size: 0.85rem; color: var(--color-accent); }
.issue-field { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 6px; }
.field-label { color: var(--text-muted); }

@media (max-width: 640px) { .info-card { grid-template-columns: 1fr; } }
</style>
