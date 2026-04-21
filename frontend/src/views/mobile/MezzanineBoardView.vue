<template>
  <div class="board-page">
    <div class="board-header">
      <div class="header-left">
        <h1 class="board-title">夹层施工现场人员</h1>
        <span class="board-time">{{ currentTime }}</span>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-value">{{ totalPeople }}</span>
          <span class="stat-label">当前在场</span>
        </div>
      </div>
    </div>

    <div v-if="onsite.length === 0" class="empty-board">
      <div class="empty-icon">🏗</div>
      <p>当前无人在夹层作业</p>
    </div>

    <div v-else class="cards-container">
      <transition-group name="card-fade" tag="div" class="cards-grid">
        <div
          v-for="person in currentPage"
          :key="person.id"
          class="person-card"
        >
          <div class="card-name">{{ person.name }}</div>
          <div class="card-project">{{ person.project }}</div>
          <div v-if="person.count > 1" class="card-count">共 {{ person.count }} 人</div>
          <div v-if="person.company" class="card-company">{{ person.company }}</div>
          <div class="card-time">
            <span class="time-label">入场</span>
            <span class="time-value">{{ person.check_in_at }}</span>
          </div>
          <div class="card-duration">已在场 {{ getDuration(person.check_in_at) }}</div>
        </div>
      </transition-group>

      <div v-if="totalPages > 1" class="page-indicator">
        <span
          v-for="i in totalPages"
          :key="i"
          class="indicator-dot"
          :class="{ active: i - 1 === currentPageIndex }"
        ></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { mezzanineApi, type MezzanineOnsite } from '@/api/mezzanine'

const PAGE_SIZE = 6
const SLIDE_INTERVAL = 5000
const REFRESH_INTERVAL = 30000

const onsite = ref<MezzanineOnsite[]>([])
const currentPageIndex = ref(0)
const currentTime = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(onsite.value.length / PAGE_SIZE)))

const totalPeople = computed(() => onsite.value.reduce((sum, p) => sum + p.count, 0))

const currentPage = computed(() => {
  const start = currentPageIndex.value * PAGE_SIZE
  return onsite.value.slice(start, start + PAGE_SIZE)
})

function getDuration(checkInAt: string): string {
  const now = new Date()
  const checkin = new Date(checkInAt)
  const diffMs = now.getTime() - checkin.getTime()
  const hours = Math.floor(diffMs / 3600000)
  const minutes = Math.floor((diffMs % 3600000) / 60000)
  return `${hours}h${String(minutes).padStart(2, '0')}m`
}

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

async function fetchData() {
  try {
    const { data } = await mezzanineApi.onsite()
    onsite.value = data
    if (currentPageIndex.value >= totalPages.value) {
      currentPageIndex.value = 0
    }
  } catch {
    // silent, keep previous data
  }
}

let slideTimer: ReturnType<typeof setInterval>
let refreshTimer: ReturnType<typeof setInterval>
let clockTimer: ReturnType<typeof setInterval>

onMounted(async () => {
  await fetchData()
  updateTime()

  slideTimer = setInterval(() => {
    if (onsite.value.length > 0) {
      currentPageIndex.value = (currentPageIndex.value + 1) % totalPages.value
    }
  }, SLIDE_INTERVAL)

  refreshTimer = setInterval(fetchData, REFRESH_INTERVAL)
  clockTimer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(slideTimer)
  clearInterval(refreshTimer)
  clearInterval(clockTimer)
})
</script>

<style scoped>
.board-page {
  min-height: 100vh;
  background: var(--bg-root);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 40px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.board-title {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 4px;
  letter-spacing: 0.05em;
}

.board-time {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-muted);
}

.header-stats { display: flex; gap: 32px; }

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}

.stat-label { font-size: 0.8rem; color: var(--text-muted); }

.empty-board {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 16px;
}

.empty-icon { font-size: 4rem; }
.empty-board p { font-size: 1.2rem; }

.cards-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 32px 40px;
  gap: 24px;
  overflow: hidden;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  flex: 1;
}

.person-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-name {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
}

.card-project {
  font-size: 1rem;
  color: var(--color-accent);
  font-weight: 500;
}

.card-company { font-size: 0.9rem; color: var(--text-secondary); }

.card-count {
  font-size: 0.9rem;
  color: var(--color-warning);
  font-weight: 600;
}

.card-time {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;
}

.time-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 2px 6px;
  border-radius: 3px;
}

.time-value {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.card-duration {
  font-size: 0.85rem;
  color: var(--color-warning);
  font-family: var(--font-mono);
}

.card-fade-enter-active,
.card-fade-leave-active { transition: all 0.4s ease; }
.card-fade-enter-from { opacity: 0; transform: translateY(10px); }
.card-fade-leave-to { opacity: 0; transform: translateY(-10px); }

.page-indicator {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-default);
  transition: all var(--transition-fast);
}

.indicator-dot.active {
  background: var(--color-accent);
  transform: scale(1.3);
}
</style>
