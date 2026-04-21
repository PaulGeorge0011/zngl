import { computed, onMounted, onUnmounted, ref } from 'vue'

const mobileBreakpoint = 960
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
const mobileNavOpen = ref(false)

function syncViewport() {
  viewportWidth.value = window.innerWidth
  if (viewportWidth.value > mobileBreakpoint) {
    mobileNavOpen.value = false
  }
}

export function useShell() {
  const isMobile = computed(() => viewportWidth.value <= mobileBreakpoint)

  function openMobileNav() {
    if (isMobile.value) mobileNavOpen.value = true
  }

  function closeMobileNav() {
    mobileNavOpen.value = false
  }

  function toggleMobileNav() {
    mobileNavOpen.value = !mobileNavOpen.value
  }

  onMounted(() => {
    syncViewport()
    window.addEventListener('resize', syncViewport)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', syncViewport)
  })

  return {
    isMobile,
    mobileNavOpen,
    openMobileNav,
    closeMobileNav,
    toggleMobileNav,
  }
}
