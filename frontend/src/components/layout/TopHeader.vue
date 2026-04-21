<template>
  <header class="top-header">
    <div class="header-left">
      <button
        v-if="isMobile"
        class="menu-toggle"
        type="button"
        @click="toggleMobileNav"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.7">
          <line x1="3" y1="5" x2="15" y2="5"/>
          <line x1="3" y1="9" x2="15" y2="9"/>
          <line x1="3" y1="13" x2="15" y2="13"/>
        </svg>
      </button>

      <div class="title-stack">
        <p class="eyebrow">Workshop Command Surface</p>
        <h1 class="system-title">
          <span class="title-prefix">//</span>
          {{ pageTitle }}
        </h1>
      </div>
    </div>

    <div class="header-right">
      <button class="theme-toggle" type="button" @click="toggleTheme">
        <span class="theme-toggle__dot" />
        <span class="theme-toggle__label">{{ isDark ? 'Dark Mode' : 'Light Mode' }}</span>
      </button>

      <div
        v-if="alarmStore.unreadCount > 0"
        class="alarm-indicator"
        @click="$router.push('/monitoring/alarms')"
      >
        <div class="alarm-pulse"></div>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 1.5L1.5 13h13L8 1.5z"/>
          <line x1="8" y1="6" x2="8" y2="9"/>
          <circle cx="8" cy="11" r="0.5" fill="currentColor"/>
        </svg>
        <span class="alarm-count">{{ alarmStore.unreadCount }}</span>
      </div>

      <div class="header-time">
        <span class="time-value">{{ currentTime }}</span>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAlarmStore } from '@/stores/alarm'
import { useTheme } from '@/composables/useTheme'
import { useShell } from '@/composables/useShell'

const route = useRoute()
const alarmStore = useAlarmStore()
const { isDark, toggleTheme } = useTheme()
const { isMobile, toggleMobileNav } = useShell()

const currentTime = ref('')
let timer: ReturnType<typeof setInterval>

const pageTitle = computed(() => {
  return (route.meta.title as string) || '系统总览'
})

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.top-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-subtle);
  backdrop-filter: blur(18px);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--bg-card);
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.title-stack {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.eyebrow {
  font-size: 0.68rem;
  color: var(--text-muted);
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.system-title {
  font-family: var(--font-display);
  font-size: 1.12rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.title-prefix {
  color: var(--color-accent);
  margin-right: 6px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.alarm-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--color-alarm-dim);
  border: 1px solid rgba(230, 57, 70, 0.3);
  border-radius: var(--radius-md);
  color: var(--color-alarm);
  cursor: pointer;
  position: relative;
  transition: all var(--transition-fast);
}

.alarm-indicator:hover {
  background: rgba(230, 57, 70, 0.2);
}

.alarm-pulse {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-alarm);
  animation: pulse-alarm 1.5s ease-in-out infinite;
}

.alarm-count {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
}

.header-time {
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 40px;
  border-radius: 999px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
}

.time-value {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

@media (max-width: 960px) {
  .top-header {
    height: 60px;
    padding: 0 14px;
  }

  .eyebrow {
    display: none;
  }

  .system-title {
    font-size: 0.98rem;
  }

  .header-right {
    gap: 8px;
  }

  .header-time {
    padding: 0 10px;
    height: 36px;
  }

  .time-value {
    font-size: 0.82rem;
  }
}

@media (max-width: 640px) {
  .theme-toggle {
    width: 40px;
    justify-content: center;
    padding: 0;
  }

  .theme-toggle__label {
    display: none;
  }

  .header-time {
    display: none;
  }

  .alarm-indicator {
    padding: 6px 10px;
  }
}
</style>
