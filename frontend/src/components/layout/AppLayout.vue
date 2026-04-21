<template>
  <div class="layout" :class="{ 'mobile-nav-open': mobileNavOpen }">
    <div
      v-if="isMobile && mobileNavOpen"
      class="mobile-backdrop"
      @click="closeMobileNav"
    />

    <aside class="sidebar" :class="{ mobile: isMobile, open: mobileNavOpen }">
      <SidebarNav />
    </aside>

    <div class="main-area">
      <TopHeaderWithLogout />
      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="slide-up" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import SidebarNav from './SidebarNav.vue'
import TopHeaderWithLogout from './TopHeaderWithLogout.vue'
import { useShell } from '@/composables/useShell'

const { isMobile, mobileNavOpen, closeMobileNav } = useShell()
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-root);
  position: relative;
}

.mobile-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(4, 10, 18, 0.42);
  backdrop-filter: blur(6px);
  z-index: 30;
}

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.content {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

@media (max-width: 960px) {
  .sidebar.mobile {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: min(84vw, 320px);
    z-index: 40;
    transform: translateX(-100%);
    box-shadow: var(--shadow-elevated);
  }

  .sidebar.mobile.open {
    transform: translateX(0);
  }
}
</style>
