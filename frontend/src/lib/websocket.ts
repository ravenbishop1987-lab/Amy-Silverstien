import type { WSMessage } from '@/types'

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export type WSEventHandler = (msg: WSMessage) => void

export class AmyWebSocket {
  private ws: WebSocket | null = null
  private token: string
  private onMessage: WSEventHandler
  private onConnect?: () => void
  private onDisconnect?: () => void
  private reconnectAttempts = 0
  private maxReconnects = 5
  private reconnectDelay = 1000

  constructor(token: string, onMessage: WSEventHandler, onConnect?: () => void, onDisconnect?: () => void) {
    this.token = token
    this.onMessage = onMessage
    this.onConnect = onConnect
    this.onDisconnect = onDisconnect
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const url = `${WS_BASE}/conversations/ws/chat?token=${encodeURIComponent(this.token)}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.reconnectDelay = 1000
      this.onConnect?.()
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        this.onMessage(msg)
      } catch {
        // ignore parse errors
      }
    }

    this.ws.onclose = () => {
      this.onDisconnect?.()
      this._scheduleReconnect()
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  sendMessage(content: string, conversationId?: string, voiceUsed = false) {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected')
    }
    this.ws.send(JSON.stringify({
      type: 'message',
      content,
      conversation_id: conversationId,
      voice_used: voiceUsed,
    }))
  }

  disconnect() {
    this.maxReconnects = 0
    this.ws?.close()
    this.ws = null
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnects) return
    setTimeout(() => {
      this.reconnectAttempts++
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000)
      this.connect()
    }, this.reconnectDelay)
  }
}

// Audio playback helper for ElevenLabs voice responses
export async function playAudioBuffer(arrayBuffer: ArrayBuffer) {
  const blob = new Blob([arrayBuffer], { type: 'audio/mpeg' })
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  return new Promise<void>((resolve, reject) => {
    audio.onended = () => {
      URL.revokeObjectURL(url)
      resolve()
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Audio playback failed'))
    }
    audio.play().catch((error) => {
      URL.revokeObjectURL(url)
      reject(error)
    })
  })
}

// Voice recording helper
export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private chunks: Blob[] = []

  async start(): Promise<void> {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this.chunks = []
    this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data)
    }
    this.mediaRecorder.start(100)
  }

  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(new Blob())
        return
      }
      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: 'audio/webm' })
        this.mediaRecorder?.stream.getTracks().forEach((t) => t.stop())
        resolve(blob)
      }
      this.mediaRecorder.stop()
    })
  }
}
