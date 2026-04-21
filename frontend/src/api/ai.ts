import http from './http'
import type { RepairAdvice } from '@/types'

export const aiApi = {
  getRepairAdvice(alarmId: number) {
    return http.get<RepairAdvice>(`/api/ai/repair-advice/${alarmId}/`)
  },

  /**
   * 流式生成维修建议（SSE）
   * 返回 ReadableStream reader
   */
  async streamRepairAdvice(
    alarmId: number,
    onChunk: (text: string) => void,
    onDone: () => void,
    onError: (err: string) => void
  ) {
    const baseUrl = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
    try {
      const response = await fetch(`${baseUrl}/api/ai/repair-advice/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alarm_id: alarmId }),
      })

      if (!response.ok) {
        onError(`请求失败: ${response.status}`)
        return
      }

      // 检查是否为 JSON（已有建议直接返回）
      const contentType = response.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const data = await response.json()
        onChunk(data.ai_response)
        onDone()
        return
      }

      // SSE 流式读取
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6).trim()
            if (payload === '[DONE]') {
              onDone()
              return
            }
            try {
              const parsed = JSON.parse(payload)
              if (parsed.content) {
                onChunk(parsed.content)
              }
              if (parsed.error) {
                onError(parsed.error)
                return
              }
            } catch {
              // skip malformed chunks
            }
          }
        }
      }
      onDone()
    } catch (err: any) {
      onError(err.message || '连接失败')
    }
  },
}
