<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">巡检详情</h2>
        <p class="page-subtitle" v-if="record">{{ record.dust_room_name }} · {{ record.role_display }} · {{ record.inspection_date }}</p>
      </div>
      <button class="btn-back" @click="$router.back()">← 返回</button>
    </div>

    <div v-if="loading" class="loading-hint">加载中...</div>

    <template v-else-if="record">
      <!-- 基本信息 -->
      <div class="info-card">
        <div class="info-row"><span class="info-label">除尘房</span><span>{{ record.dust_room_name }}</span></div>
        <div class="info-row"><span class="info-label">巡检角色</span><span>{{ record.role_display }}</span></div>
        <div class="info-row"><span class="info-label">巡检人</span><span>{{ record.inspector_display.display_name }}</span></div>
        <div class="info-row"><span class="info-label">巡检日期</span><span>{{ record.inspection_date }}</span></div>
        <div class="info-row"><span class="info-label">提交时间</span><span>{{ record.submitted_at || '-' }}</span></div>
        <div class="info-row">
          <span class="info-label">状态</span>
          <el-tag :type="record.has_abnormal ? 'warning' : 'success'" size="small">
            {{ record.has_abnormal ? '存在异常' : '全部正常' }}
          </el-tag>
        </div>
        <div v-if="record.remark" class="info-row full">
          <span class="info-label">备注</span>
          <span>{{ record.remark }}</span>
        </div>
      </div>

      <!-- 逐项结果 -->
      <h3 class="section-title">检查项结果 ({{ record.results.length }})</h3>
      <div class="results-list">
        <div v-for="(r, idx) in record.results" :key="r.id" class="result-item" :class="{ abnormal: !r.is_normal }">
          <div class="result-header">
            <span class="result-index">{{ idx + 1 }}</span>
            <span class="result-name">{{ r.item_name }}</span>
            <el-tag :type="r.is_normal ? 'success' : 'danger'" size="small">
              {{ r.is_normal ? '正常' : '异常' }}
            </el-tag>
          </div>
          <div v-if="r.value" class="result-value">
            <span class="value-label">值：</span>
            <span>{{ r.value }}</span>
            <span v-if="r.item_unit" class="value-unit">{{ r.item_unit }}</span>
          </div>
          <div v-if="r.remark" class="result-remark">
            <span class="remark-label">备注：</span>{{ r.remark }}
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { dustroomApi } from '@/api/dustroom'
import type { InspectionRecordDetail } from '@/api/dustroom'

const route = useRoute()
const loading = ref(true)
const record = ref<InspectionRecordDetail | null>(null)

onMounted(async () => {
  try {
    const { data } = await dustroomApi.getRecord(Number(route.params.id))
    record.value = data
  } finally { loading.value = false }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.btn-back {
  color: var(--color-accent); background: transparent; border: 1px solid var(--border-default);
  padding: 6px 12px; border-radius: var(--radius-md); font-size: 0.85rem; cursor: pointer;
}
.btn-back:hover { background: var(--bg-card); }
.loading-hint { text-align: center; padding: 48px 0; color: var(--text-muted); }

.info-card {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 20px; margin-top: 16px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px;
}
.info-row { display: flex; gap: 8px; align-items: center; font-size: 0.9rem; }
.info-row.full { grid-column: 1 / -1; }
.info-label { color: var(--text-muted); min-width: 70px; flex-shrink: 0; }

.section-title { font-size: 1rem; font-weight: 600; color: var(--text-primary); margin: 24px 0 12px; }

.results-list { display: flex; flex-direction: column; gap: 8px; }
.result-item {
  background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  padding: 14px; transition: border-color 0.2s;
}
.result-item.abnormal { border-color: var(--color-warning); border-left-width: 3px; }
.result-header { display: flex; align-items: center; gap: 8px; }
.result-index {
  width: 22px; height: 22px; border-radius: 50%; background: var(--border-default);
  color: var(--text-secondary); font-size: 0.7rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.result-name { flex: 1; font-weight: 500; color: var(--text-primary); font-size: 0.9rem; }
.result-value { margin-top: 6px; font-size: 0.85rem; color: var(--text-secondary); }
.value-label { color: var(--text-muted); }
.value-unit { color: var(--text-muted); margin-left: 2px; }
.result-remark { margin-top: 4px; font-size: 0.85rem; color: var(--color-warning); }
.remark-label { color: var(--text-muted); }

@media (max-width: 640px) {
  .info-card { grid-template-columns: 1fr; }
}
</style>
