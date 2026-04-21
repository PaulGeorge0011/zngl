<template>
  <div class="sidebar-nav">
    <!-- Logo -->
    <div class="logo-section">
      <div class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect x="2" y="6" width="8" height="16" rx="2" fill="#4a9eff" opacity="0.9"/>
          <rect x="18" y="6" width="8" height="16" rx="2" fill="#4a9eff" opacity="0.5"/>
          <rect x="6" y="11" width="16" height="6" rx="1.5" fill="#00d4aa" opacity="0.8"/>
        </svg>
      </div>
      <div class="logo-text">
        <span class="logo-title">ZS2</span>
        <span class="logo-sub">制丝车间</span>
      </div>
    </div>

    <div class="nav-divider"></div>

    <!-- Navigation -->
    <nav class="nav-list">
      <!-- 系统总览 -->
      <router-link to="/dashboard" class="nav-item" :class="{ active: isActive('/dashboard') }" @click="handleNavSelect">
        <div class="nav-icon" v-html="icons.dashboard"></div>
        <span class="nav-label">系统总览</span>
      </router-link>

      <!-- 设备管理（可展开） -->
      <div class="nav-group">
        <div
          class="nav-item nav-group-header"
          :class="{ active: isEquipmentGroupActive }"
          @click="toggleEquipment"
        >
          <div class="nav-icon" v-html="icons.equipment"></div>
          <span class="nav-label">设备管理</span>
          <svg
            class="nav-chevron"
            :class="{ expanded: equipmentExpanded }"
            width="14" height="14" viewBox="0 0 14 14"
            fill="none" stroke="currentColor" stroke-width="1.5"
          >
            <polyline points="3,5 7,9 11,5"/>
          </svg>
        </div>

        <!-- 子菜单 -->
        <div class="nav-sub" :class="{ open: equipmentExpanded }">
          <router-link to="/equipment" class="nav-sub-item" :class="{ active: route.path === '/equipment' || route.path.startsWith('/equipment/') }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>设备列表</span>
          </router-link>
          <router-link to="/monitoring" class="nav-sub-item" :class="{ active: route.path === '/monitoring' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>实时监控</span>
          </router-link>
          <router-link to="/monitoring/alarms" class="nav-sub-item" :class="{ active: route.path === '/monitoring/alarms' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>报警历史</span>
            <span v-if="alarmStore.unreadCount > 0" class="nav-badge alarm">
              {{ alarmStore.unreadCount }}
            </span>
          </router-link>
        </div>
      </div>

      <!-- 质量管理（可展开） -->
      <div class="nav-group">
        <div
          class="nav-item nav-group-header"
          :class="{ active: isQualityGroupActive }"
          @click="toggleQuality"
        >
          <div class="nav-icon" v-html="icons.quality"></div>
          <span class="nav-label">质量管理</span>
          <svg
            class="nav-chevron"
            :class="{ expanded: qualityExpanded }"
            width="14" height="14" viewBox="0 0 14 14"
            fill="none" stroke="currentColor" stroke-width="1.5"
          >
            <polyline points="3,5 7,9 11,5"/>
          </svg>
        </div>
        <div class="nav-sub" :class="{ open: qualityExpanded }">
          <router-link to="/quality" class="nav-sub-item" :class="{ active: route.path === '/quality' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>成品水分</span>
          </router-link>
          <router-link to="/quality/knowledge" class="nav-sub-item" :class="{ active: route.path === '/quality/knowledge' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>工艺质量知识库</span>
          </router-link>
        </div>
      </div>

      <!-- 安全管理（可展开） -->
      <div class="nav-group">
        <div
          class="nav-item nav-group-header"
          :class="{ active: isSafetyGroupActive }"
          @click="toggleSafety"
        >
          <div class="nav-icon" v-html="icons.safety"></div>
          <span class="nav-label">安全管理</span>
          <svg
            class="nav-chevron"
            :class="{ expanded: safetyExpanded }"
            width="14" height="14" viewBox="0 0 14 14"
            fill="none" stroke="currentColor" stroke-width="1.5"
          >
            <polyline points="3,5 7,9 11,5"/>
          </svg>
        </div>
        <div class="nav-sub" :class="{ open: safetyExpanded }">
          <router-link to="/safety" class="nav-sub-item" :class="{ active: route.path === '/safety' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>安全概览</span>
          </router-link>
          <router-link to="/safety/dustroom" class="nav-sub-item" :class="{ active: route.path.startsWith('/safety/dustroom') }" @click="handleNavSelect">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="1" y="4" width="11" height="7" rx="1.5"/>
              <path d="M3 4V2.5a1 1 0 011-1h5a1 1 0 011 1V4"/>
              <circle cx="6.5" cy="7.5" r="1.5"/>
            </svg>
            除尘房巡检
          </router-link>
          <router-link to="/safety/nightshift" class="nav-sub-item" :class="{ active: route.path.startsWith('/safety/nightshift') }" @click="handleNavSelect">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="6.5" cy="6.5" r="5"/>
              <path d="M6.5 3v3.5l2.5 1.5"/>
            </svg>
            夜班监护检查
          </router-link>
          <router-link to="/safety/hazard" class="nav-sub-item" active-class="active" @click="handleNavSelect">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M10.5 8.5a2 2 0 01-2 2h-5a2 2 0 01-2-2V5a2 2 0 012-2h1l1-1.5h3L9.5 3h1a2 2 0 012 2v3.5z"/>
              <circle cx="6.5" cy="6.5" r="1.8"/>
            </svg>
            随手拍
          </router-link>
          <router-link to="/safety/mezzanine" class="nav-sub-item" active-class="active" @click="handleNavSelect">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="1" y="3" width="11" height="8" rx="1.5"/>
              <path d="M4 3V2a1 1 0 011-1h3a1 1 0 011 1v1"/>
              <path d="M4 7h5M4 9h3"/>
            </svg>
            夹层施工
          </router-link>
          <router-link to="/safety/knowledge" class="nav-sub-item" :class="{ active: route.path === '/safety/knowledge' }" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>安全知识库</span>
          </router-link>
        </div>
      </div>

      <!-- 系统设置 -->
      <div class="nav-group">
        <div
          class="nav-item nav-group-header"
          :class="{ active: isSettingsGroupActive }"
          @click="toggleSettings"
        >
          <div class="nav-icon" v-html="icons.settings"></div>
          <span class="nav-label">系统设置</span>
          <svg
            class="nav-chevron"
            :class="{ expanded: settingsExpanded }"
            width="14" height="14" viewBox="0 0 14 14"
            fill="none" stroke="currentColor" stroke-width="1.5"
          >
            <polyline points="3,5 7,9 11,5"/>
          </svg>
        </div>
        <div class="nav-sub" :class="{ open: settingsExpanded }">
          <router-link to="/settings/users" class="nav-sub-item" active-class="active" @click="handleNavSelect">
            <span class="sub-dot"></span>
            <span>用户管理</span>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Bottom section -->
    <div class="nav-footer">
      <div class="system-status">
        <div class="status-dot" :class="wsConnected ? 'online' : 'offline'"></div>
        <span class="status-text">{{ wsConnected ? '系统在线' : '连接中...' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAlarmStore } from '@/stores/alarm'
import { useShell } from '@/composables/useShell'

const route = useRoute()
const alarmStore = useAlarmStore()
const wsConnected = computed(() => true)
const { isMobile, closeMobileNav } = useShell()

// 设备管理子菜单展开状态
const equipmentExpanded = ref(false)
const qualityExpanded = ref(false)
const safetyExpanded = ref(false)

// 当前路由在设备管理组内时自动展开
const isEquipmentGroupActive = computed(() =>
  route.path.startsWith('/equipment') ||
  route.path.startsWith('/monitoring')
)

const isQualityGroupActive = computed(() =>
  route.path.startsWith('/quality')
)

const isSafetyGroupActive = computed(() =>
  route.path.startsWith('/safety')
)

watch(isEquipmentGroupActive, (val) => {
  if (val) equipmentExpanded.value = true
}, { immediate: true })

watch(isQualityGroupActive, (val) => {
  if (val) qualityExpanded.value = true
}, { immediate: true })

watch(isSafetyGroupActive, (val) => {
  if (val) safetyExpanded.value = true
}, { immediate: true })

const settingsExpanded = ref(false)
const isSettingsGroupActive = computed(() => route.path.startsWith('/settings'))
watch(isSettingsGroupActive, (v) => { if (v) settingsExpanded.value = true }, { immediate: true })
function toggleSettings() { settingsExpanded.value = !settingsExpanded.value }

function toggleEquipment() {
  equipmentExpanded.value = !equipmentExpanded.value
}

function toggleQuality() {
  qualityExpanded.value = !qualityExpanded.value
}

function toggleSafety() {
  safetyExpanded.value = !safetyExpanded.value
}

function isActive(path: string): boolean {
  return route.path === path
}

function handleNavSelect() {
  if (isMobile.value) closeMobileNav()
}

const icons = {
  dashboard: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="7" height="7" rx="1.5"/><rect x="10" y="1" width="7" height="4" rx="1.5"/><rect x="1" y="10" width="7" height="7" rx="1.5"/><rect x="10" y="7" width="7" height="10" rx="1.5"/></svg>`,
  equipment: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="9" r="3"/><path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M3.3 14.7l1.4-1.4M13.3 4.7l1.4-1.4"/></svg>`,
  quality: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 9l2.5 2.5L13 6"/><rect x="1" y="1" width="16" height="16" rx="3"/></svg>`,
  safety: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 1L2 4.5v5c0 4 3 7 7 7.5 4-.5 7-3.5 7-7.5v-5L9 1z"/></svg>`,
  settings: `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="9" r="2.5"/><path d="M9 1.5v2M9 14.5v2M1.5 9h2M14.5 9h2M3.7 3.7l1.4 1.4M12.9 12.9l1.4 1.4M12.9 5.1l-1.4 1.4M5.1 12.9l-1.4 1.4"/></svg>`,
}
</script>

<style scoped>
.sidebar-nav {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px;
}

.logo-icon { flex-shrink: 0; }

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: 0.1em;
}

.logo-sub {
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.nav-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-default), transparent);
  margin: 0 16px 8px;
}

.nav-list {
  flex: 1;
  padding: 4px 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 一级菜单项 */
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all var(--transition-fast);
  position: relative;
  cursor: pointer;
  user-select: none;
}

.nav-item:hover {
  background: var(--sidebar-item-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--sidebar-item-active);
  color: var(--color-accent);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--color-accent);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
}

.nav-item.active .nav-icon { opacity: 1; }

/* 展开箭头 */
.nav-chevron {
  margin-left: auto;
  transition: transform var(--transition-fast);
  opacity: 0.5;
  flex-shrink: 0;
}

.nav-chevron.expanded {
  transform: rotate(180deg);
}

/* 分组容器 */
.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-group-header {
  /* 继承 nav-item 样式 */
}

/* 子菜单 */
.nav-sub {
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.25s ease;
}

.nav-sub.open {
  max-height: 300px;
}

.nav-sub-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px 8px 36px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 400;
  transition: all var(--transition-fast);
  position: relative;
}

.nav-sub-item:hover {
  background: var(--sidebar-item-hover);
  color: var(--text-primary);
}

.nav-sub-item.active {
  color: var(--color-accent);
  background: var(--sidebar-item-active);
}

.nav-sub-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background: var(--color-accent);
  border-radius: 0 2px 2px 0;
}

.sub-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.4;
  flex-shrink: 0;
}

.nav-sub-item.active .sub-dot {
  opacity: 1;
  background: var(--color-accent);
}

/* Badge */
.nav-badge {
  margin-left: auto;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  font-size: 0.7rem;
  font-weight: 700;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.nav-badge.alarm {
  background: var(--color-alarm);
  color: white;
  animation: pulse-alarm 2s ease-in-out infinite;
}

/* Footer */
.nav-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
}

.system-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-dot.online {
  background: var(--color-healthy);
  box-shadow: 0 0 6px var(--color-healthy);
}

.status-dot.offline { background: var(--text-muted); }

.status-text {
  font-size: 0.75rem;
  color: var(--text-muted);
}

@media (max-width: 960px) {
  .logo-section {
    padding: 16px 16px 12px;
  }

  .nav-list {
    padding: 6px 10px 14px;
  }

  .nav-item {
    min-height: 46px;
    font-size: 0.94rem;
  }

  .nav-sub-item {
    min-height: 42px;
    padding-left: 34px;
  }

  .nav-footer {
    padding: 14px 16px calc(14px + env(safe-area-inset-bottom));
  }
}
</style>
