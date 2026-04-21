import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Equipment } from '@/types'
import { equipmentApi } from '@/api/equipment'

export const useEquipmentStore = defineStore('equipment', () => {
  const equipments = ref<Equipment[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchList(params?: Record<string, any>) {
    loading.value = true
    try {
      const { data } = await equipmentApi.list(params)
      equipments.value = data.results
      total.value = data.count
    } finally {
      loading.value = false
    }
  }

  return { equipments, total, loading, fetchList }
})
