import type { WSSensorData, WSAlarmData } from '@/types'

type MessageHandler = (type: 'sensor' | 'alarm', data: WSSensorData | WSAlarmData) => void

class MonitoringWebSocket {
  private ws: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectDelay = 1000
  private maxReconnectDelay = 30000
  private url: string = ''

  connect(url?: string) {
    if (url) this.url = url
    if (!this.url) return
    this.cleanup()

    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('[WS] 连接成功')
      this.reconnectDelay = 1000
    }

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        this.handlers.forEach((h) => h(msg.type, msg.data))
      } catch (e) {
        console.warn('[WS] 解析失败', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[WS] 连接关闭，准备重连...')
      this.scheduleReconnect()
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay)
      this.connect()
    }, this.reconnectDelay)
  }

  private cleanup() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.onclose = null
      this.ws.close()
      this.ws = null
    }
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  disconnect() {
    this.cleanup()
    this.handlers.clear()
  }
}

export const monitoringWS = new MonitoringWebSocket()
