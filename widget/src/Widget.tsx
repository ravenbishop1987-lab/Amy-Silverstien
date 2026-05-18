import { useState, useEffect, useRef, useCallback } from 'react'
import React from 'react'

declare const __AMY_BACKEND__: string

interface WidgetConfig {
  position?: 'bottom-right' | 'bottom-left'
  primaryColor?: string
  greeting?: string
  size?: 'small' | 'medium' | 'large'
  darkMode?: boolean
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const DEFAULT_CONFIG: WidgetConfig = {
  position: 'bottom-right',
  primaryColor: '#8FAF8F',
  greeting: "Hey, I'm Amy. What's on your mind about dating or relationships?",
  size: 'medium',
  darkMode: false,
}

const STYLES = `
  .amy-widget * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'DM Sans', sans-serif; }
  .amy-bubble-btn { width: 56px; height: 56px; border-radius: 50%; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: transform 0.2s, box-shadow 0.2s; }
  .amy-bubble-btn:hover { transform: scale(1.05); box-shadow: 0 6px 24px rgba(0,0,0,0.2); }
  .amy-chat-window { width: 360px; height: 520px; background: #FAF9F7; border-radius: 20px; box-shadow: 0 8px 40px rgba(0,0,0,0.12); display: flex; flex-direction: column; overflow: hidden; }
  .amy-header { padding: 16px 18px; border-bottom: 1px solid #EDE9E3; display: flex; align-items: center; gap: 10px; background: white; }
  .amy-avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 14px; flex-shrink: 0; }
  .amy-name { font-weight: 600; font-size: 14px; color: #1A1A1A; }
  .amy-status { font-size: 11px; color: #9CA3AF; display: flex; align-items: center; gap: 4px; }
  .amy-dot { width: 6px; height: 6px; border-radius: 50%; background: #8FAF8F; display: inline-block; }
  .amy-close { margin-left: auto; cursor: pointer; background: none; border: none; color: #9CA3AF; font-size: 18px; line-height: 1; }
  .amy-messages { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; scroll-behavior: smooth; }
  .amy-msg-amy { display: flex; gap: 8px; align-items: flex-end; }
  .amy-msg-user { display: flex; justify-content: flex-end; }
  .amy-bubble-amy { background: white; border-radius: 18px 18px 18px 4px; padding: 10px 14px; max-width: 85%; min-width: 0; font-size: 13px; line-height: 1.5; color: #2D2D2D; box-shadow: 0 1px 8px rgba(0,0,0,0.06); overflow-wrap: anywhere; white-space: pre-wrap; }
  .amy-bubble-user { border-radius: 18px 18px 4px 18px; padding: 10px 14px; max-width: 85%; min-width: 0; font-size: 13px; line-height: 1.5; color: white; overflow-wrap: anywhere; white-space: pre-wrap; }
  .amy-mini-avatar { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 10px; flex-shrink: 0; }
  .amy-input-area { padding: 12px 14px; border-top: 1px solid #EDE9E3; background: white; display: flex; gap: 8px; align-items: flex-end; }
  .amy-input { flex: 1; border: 1px solid #EDE9E3; border-radius: 12px; padding: 9px 12px; font-size: 13px; outline: none; resize: none; background: #FAF9F7; color: #1A1A1A; max-height: 100px; }
  .amy-input:focus { border-color: #8FAF8F; }
  .amy-send-btn { width: 36px; height: 36px; border-radius: 10px; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0; transition: background 0.2s; }
  .amy-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .amy-typing { display: flex; gap: 4px; align-items: center; padding: 4px; }
  .amy-typing span { width: 6px; height: 6px; border-radius: 50%; background: #8FAF8F; animation: amyBounce 1.2s infinite ease-in-out; }
  .amy-typing span:nth-child(2) { animation-delay: 0.2s; }
  .amy-typing span:nth-child(3) { animation-delay: 0.4s; }
  .amy-powered { text-align: center; font-size: 10px; color: #C4B9B0; padding: 6px; }
  .amy-cta { background: #F0F8F0; border: 1px solid #C8E6C8; border-radius: 12px; padding: 10px 12px; margin: 4px 0; text-align: center; }
  .amy-cta a { color: #5C8A5C; text-decoration: none; font-size: 12px; font-weight: 500; }
  @keyframes amyBounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
  @media (max-width: 480px) { .amy-chat-window { width: 100vw; height: 100dvh; border-radius: 0; position: fixed; bottom: 0; right: 0; } }
`

interface Props {
  embedId: string | null
}

export default function AmyWidget({ embedId }: Props) {
  const [isOpen, setIsOpen] = useState(false)
  const [config, setConfig] = useState<WidgetConfig>(DEFAULT_CONFIG)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamText, setStreamText] = useState('')
  const [token, setToken] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const streamTextRef = useRef('')
  const color = config.primaryColor || '#8FAF8F'

  // Load config
  useEffect(() => {
    if (!embedId) return
    fetch(`${__AMY_BACKEND__}/embed/config/${embedId}`)
      .then((r) => r.json())
      .then((cfg) => setConfig({ ...DEFAULT_CONFIG, ...cfg }))
      .catch(() => {})
  }, [embedId])

  // Show greeting on first open
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: config.greeting || DEFAULT_CONFIG.greeting!,
        timestamp: new Date().toISOString(),
      }])
    }
  }, [isOpen])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamText])

  useEffect(() => {
    streamTextRef.current = streamText
  }, [streamText])

  // Get auth token from amy.app session or prompt login
  const getToken = useCallback(async (): Promise<string | null> => {
    if (token) return token
    // Check if user is logged in via localStorage (shared origin) or iframe message
    const stored = localStorage.getItem('amy_token')
    if (stored) { setToken(stored); return stored }
    return null
  }, [token])

  const connectWS = useCallback(async () => {
    const t = await getToken()
    if (!t) return

    const wsUrl = `${__AMY_BACKEND__.replace('http', 'ws')}/conversations/ws/chat?token=${encodeURIComponent(t)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'token') {
        setStreamText((prev) => {
          const next = prev + msg.content
          streamTextRef.current = next
          return next
        })
        setIsStreaming(true)
      } else if (msg.type === 'done') {
        if (msg.conversation_id) setConversationId(msg.conversation_id)
        const content = msg.full_response || streamTextRef.current
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content,
          timestamp: new Date().toISOString(),
        }])
        streamTextRef.current = ''
        setStreamText('')
        setIsStreaming(false)
      }
    }
    ws.onerror = () => ws.close()
  }, [getToken])

  useEffect(() => {
    if (isOpen) connectWS()
    return () => { wsRef.current?.close(); wsRef.current = null }
  }, [isOpen])

  const sendMessage = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    setMessages((prev) => [...prev, { role: 'user', content: trimmed, timestamp: new Date().toISOString() }])
    setInput('')

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message', content: trimmed, conversation_id: conversationId,
      }))
    } else {
      // Fallback: prompt login on main app
      const loginUrl = `${window.location.origin === __AMY_BACKEND__ ? '' : (new URL(__AMY_BACKEND__)).origin}/chat`
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `To continue chatting with Amy, [sign in at amy.app](${loginUrl}) — it's free!`,
        timestamp: new Date().toISOString(),
      }])
    }
  }

  return (
    <div className="amy-widget" style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 2147483647 }}>
      <style>{STYLES}</style>

      {/* Chat window */}
      {isOpen && (
        <div className="amy-chat-window" style={{ marginBottom: 12 }}>
          <div className="amy-header">
            <div className="amy-avatar" style={{ background: color }}>A</div>
            <div>
              <div className="amy-name">Amy</div>
              <div className="amy-status"><span className="amy-dot" />Dating advice AI</div>
            </div>
            <button className="amy-close" onClick={() => setIsOpen(false)}>×</button>
          </div>

          <div className="amy-messages">
            {messages.map((msg, i) => (
              msg.role === 'assistant' ? (
                <div key={i} className="amy-msg-amy">
                  <div className="amy-mini-avatar" style={{ background: color }}>A</div>
                  <div className="amy-bubble-amy">{msg.content}</div>
                </div>
              ) : (
                <div key={i} className="amy-msg-user">
                  <div className="amy-bubble-user" style={{ background: color }}>{msg.content}</div>
                </div>
              )
            ))}
            {isStreaming && streamText && (
              <div className="amy-msg-amy">
                <div className="amy-mini-avatar" style={{ background: color }}>A</div>
                <div className="amy-bubble-amy">{streamText}<span style={{ opacity: 0.5 }}>|</span></div>
              </div>
            )}
            {isStreaming && !streamText && (
              <div className="amy-msg-amy">
                <div className="amy-mini-avatar" style={{ background: color }}>A</div>
                <div className="amy-bubble-amy"><div className="amy-typing"><span /><span /><span /></div></div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="amy-input-area">
            <textarea
              className="amy-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
              placeholder="Tell Amy what's on your mind..."
              rows={1}
              disabled={isStreaming}
            />
            <button
              className="amy-send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || isStreaming}
              style={{ background: color }}
            >
              ↑
            </button>
          </div>
          <div className="amy-powered">Powered by Amy · <a href={__AMY_BACKEND__} target="_blank" rel="noreferrer" style={{ color: color }}>Get the full app</a></div>
        </div>
      )}

      {/* Bubble button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          className="amy-bubble-btn"
          onClick={() => setIsOpen(!isOpen)}
          style={{ background: color }}
          title="Chat with Amy"
        >
          {isOpen ? '×' : '💬'}
        </button>
      </div>
    </div>
  )
}
