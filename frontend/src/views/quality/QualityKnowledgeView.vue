<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">工艺质量知识库</h2>
        <p class="page-subtitle">查询烟草制丝质量相关知识与标准</p>
      </div>
    </div>

    <!-- 搜索区域 -->
    <div class="search-card">
      <div class="search-row">
        <el-input
          v-model="question"
          placeholder="输入问题，如：烟丝含水率标准是多少？"
          size="large"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="6.5" cy="6.5" r="5"/><line x1="10.5" y1="10.5" x2="14" y2="14"/>
            </svg>
          </template>
        </el-input>
        <el-select v-model="topN" style="width: 120px" size="large">
          <el-option label="返回 3 条" :value="3" />
          <el-option label="返回 5 条" :value="5" />
          <el-option label="返回 10 条" :value="10" />
        </el-select>
        <el-button type="primary" size="large" :loading="loading" @click="handleSearch">
          搜索
        </el-button>
      </div>

      <!-- 快捷问题 -->
      <div class="quick-questions">
        <span class="quick-label">快捷查询：</span>
        <el-tag
          v-for="q in quickQuestions"
          :key="q"
          class="quick-tag"
          @click="quickSearch(q)"
        >
          {{ q }}
        </el-tag>
      </div>
    </div>

    <!-- 结果区域 -->
    <div v-if="searched">
      <!-- 无结果 -->
      <div v-if="results.length === 0 && !loading" class="empty-result">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <circle cx="18" cy="18" r="14"/><line x1="28" y1="28" x2="36" y2="36"/>
          <line x1="14" y1="18" x2="22" y2="18"/><line x1="18" y1="14" x2="18" y2="22"/>
        </svg>
        <p>未找到相关内容，请尝试其他关键词</p>
      </div>

      <!-- 结果列表 -->
      <div v-else class="results-header">
        <span class="results-count">找到 <b>{{ results.length }}</b> 条相关内容</span>
        <span class="results-query">「{{ lastQuestion }}」</span>
      </div>

      <div class="results-list">
        <div
          v-for="(item, index) in results"
          :key="index"
          class="result-card card-stagger"
          :style="{ animationDelay: index * 60 + 'ms' }"
        >
          <div class="result-header">
            <div class="result-index">{{ index + 1 }}</div>
            <div class="result-meta">
              <span v-if="item.document_name" class="result-doc">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="1" y="1" width="10" height="10" rx="1.5"/>
                  <line x1="3" y1="4" x2="9" y2="4"/>
                  <line x1="3" y1="6.5" x2="9" y2="6.5"/>
                  <line x1="3" y1="9" x2="7" y2="9"/>
                </svg>
                {{ item.document_name }}
              </span>
              <span class="result-score" :class="scoreClass(item.score)">
                相关度 {{ (item.score * 100).toFixed(0) }}%
              </span>
            </div>
          </div>
          <div class="result-content">{{ item.content }}</div>
        </div>
      </div>
    </div>

    <!-- 初始状态 -->
    <div v-else class="initial-state">
      <div class="initial-icon">
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.2">
          <rect x="8" y="4" width="32" height="40" rx="3"/>
          <line x1="14" y1="14" x2="34" y2="14"/>
          <line x1="14" y1="20" x2="34" y2="20"/>
          <line x1="14" y1="26" x2="26" y2="26"/>
          <circle cx="40" cy="40" r="10"/>
          <line x1="46" y1="46" x2="52" y2="52"/>
        </svg>
      </div>
      <p class="initial-text">输入问题，从质量知识库中检索相关内容</p>
      <p class="initial-sub">知识库包含烟草制丝质量标准、检测方法、工艺规范等内容</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import http from '@/api/http'
import { ElMessage } from 'element-plus'

interface KnowledgeResult {
  content: string
  document_name: string
  score: number
}

const question = ref('')
const topN = ref(5)
const loading = ref(false)
const searched = ref(false)
const results = ref<KnowledgeResult[]>([])
const lastQuestion = ref('')

const quickQuestions = [
  '烟丝含水率标准',
  '切丝宽度要求',
  '烘丝温度控制',
  '质量检验方法',
  '工艺参数规范',
]

function scoreClass(score: number) {
  if (score >= 0.7) return 'score-high'
  if (score >= 0.4) return 'score-mid'
  return 'score-low'
}

async function handleSearch() {
  const q = question.value.trim()
  if (!q) {
    ElMessage.warning('请输入查询内容')
    return
  }

  loading.value = true
  searched.value = true
  lastQuestion.value = q
  results.value = []

  try {
    const { data } = await http.post('/api/quality/knowledge/search/', {
      question: q,
      top_n: topN.value,
    })
    results.value = data.results || []
    if (results.value.length === 0) {
      ElMessage.info('未找到相关内容')
    }
  } catch (err: any) {
    const msg = err.response?.data?.error || '查询失败'
    ElMessage.error(msg)
    searched.value = false
  } finally {
    loading.value = false
  }
}

function quickSearch(q: string) {
  question.value = q
  handleSearch()
}
</script>

<style scoped>
.search-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.search-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.quick-questions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.quick-tag {
  cursor: pointer;
  background: var(--bg-elevated) !important;
  border-color: var(--border-default) !important;
  color: var(--text-secondary) !important;
  transition: all var(--transition-fast);
}

.quick-tag:hover {
  border-color: var(--color-accent) !important;
  color: var(--color-accent) !important;
}

/* 结果 */
.results-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.results-count {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.results-count b {
  color: var(--color-accent);
  font-family: var(--font-mono);
}

.results-query {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  transition: border-color var(--transition-fast);
}

.result-card:hover {
  border-color: var(--border-default);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.result-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-info-dim);
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.result-doc {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.result-score {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
  margin-left: auto;
}

.score-high { background: var(--color-healthy-dim); color: var(--color-healthy); }
.score-mid { background: var(--color-warning-dim); color: var(--color-warning); }
.score-low { background: rgba(255,255,255,0.04); color: var(--text-muted); }

.result-content {
  font-size: 0.9rem;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 空状态 */
.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-muted);
}

/* 初始状态 */
.initial-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 0;
}

.initial-icon {
  color: var(--text-secondary);
}

.initial-text {
  font-size: 1rem;
  color: var(--text-secondary);
}

.initial-sub {
  font-size: 0.85rem;
  color: var(--text-muted);
}

@media (max-width: 960px) {
  .search-card {
    padding: 16px;
  }

  .search-row {
    flex-wrap: wrap;
  }

  .search-row > * {
    width: 100% !important;
  }

  .results-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .result-card {
    padding: 14px 16px;
  }

  .result-header,
  .result-meta {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .result-score {
    margin-left: 0;
  }

  .initial-state,
  .empty-result {
    padding: 40px 0;
  }
}
</style>
