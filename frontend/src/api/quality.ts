import http from './http'

export interface Brand {
  id: number
  name: string
  created_at: string
}

export interface MoistureData {
  id: number
  brand: number
  brand_name: string
  sampling_date: string
  sample_number: string
  machine_number: string
  machine_stage: string
  finished_moisture: number | null
  powder_rate: number | null
  addition_method: string | null
  batch_number: string | null
  shift: string | null
  drying_moisture: number | null
  mixed_moisture: number | null
  cabinet_moisture: number | null
  rolling_moisture: number | null
  drying_mixed_diff: number | null
  mixed_cabinet_diff: number | null
  cabinet_rolling_diff: number | null
  rolling_finished_diff: number | null
  mixed_finished_diff: number | null
}

export const getBrands = () => http.get<Brand[]>('/api/quality/brands/')
export const createBrand = (data: { name: string }) => http.post<Brand>('/api/quality/brands/', data)
export const updateBrand = (id: number, data: { name: string }) => http.put<Brand>(`/api/quality/brands/${id}/`, data)
export const deleteBrand = (id: number) => http.delete(`/api/quality/brands/${id}/`)

export const getMoistureData = (brandId?: number) =>
  http.get<MoistureData[]>('/api/quality/moisture-data/', { params: brandId ? { brand: brandId } : {} })
export const createMoistureData = (data: Partial<MoistureData>) => http.post<MoistureData>('/api/quality/moisture-data/', data)
export const updateMoistureData = (id: number, data: Partial<MoistureData>) => http.put<MoistureData>(`/api/quality/moisture-data/${id}/`, data)
export const deleteMoistureData = (id: number) => http.delete(`/api/quality/moisture-data/${id}/`)
export const importExcel = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/api/quality/moisture-data/import_excel/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
