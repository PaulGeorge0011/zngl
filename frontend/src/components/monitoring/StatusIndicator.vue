<template>
  <span class="status-indicator" :class="status" :style="{ width: size + 'px', height: size + 'px' }">
    <span class="indicator-core"></span>
    <span v-if="status === 'alarm'" class="indicator-ring"></span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  status: 'normal' | 'warning' | 'alarm' | 'offline'
  size?: number
}>()
</script>

<style scoped>
.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}

.indicator-core {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  transition: all var(--transition-fast);
}

.normal .indicator-core {
  background: var(--color-healthy);
  box-shadow: 0 0 6px var(--color-healthy);
}

.warning .indicator-core {
  background: var(--color-warning);
  box-shadow: 0 0 6px var(--color-warning);
  animation: pulse-alarm 2s ease-in-out infinite;
}

.alarm .indicator-core {
  background: var(--color-alarm);
  box-shadow: 0 0 8px var(--color-alarm);
  animation: pulse-alarm 1s ease-in-out infinite;
}

.offline .indicator-core {
  background: var(--text-muted);
}

.indicator-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 200%;
  height: 200%;
  border-radius: 50%;
  border: 1.5px solid var(--color-alarm);
  opacity: 0;
  animation: ring-expand 1.5s ease-out infinite;
}

@keyframes ring-expand {
  0% {
    width: 100%;
    height: 100%;
    opacity: 0.6;
  }
  100% {
    width: 250%;
    height: 250%;
    opacity: 0;
  }
}
</style>
