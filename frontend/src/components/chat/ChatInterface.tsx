import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Candy,
  Flower2,
  Grid2X2,
  HandHeart,
  Heart,
  MessageCircle,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Play,
  Plus,
  Send,
  Smile,
  SlidersHorizontal,
  Volume2,
  Wrench,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { AmyWebSocket, playAudioBuffer } from '@/lib/websocket'
import { conversationsApi, voiceApi, stripeApi } from '@/lib/api'
import MessageBubble, { TypingIndicator, StreamingBubble } from './MessageBubble'
import VoiceInput from './VoiceInput'
import PricingModal from '@/components/subscription/PricingModal'
import type { ChatMessage, Conversation } from '@/types'

const FANVUE_URL = import.meta.env.VITE_FANVUE_URL || 'https://www.fanvue.com/amysilverstein87'

const GIFT_OPTIONS = [
  { id: 'roses', label: 'Roses', price: '$2.99', Icon: Flower2 },
  { id: 'candy', label: 'Candy', price: '$1.99', Icon: Candy },
  { id: 'kisses', label: 'Kisses', price: '$1.49', Icon: Heart },
  { id: 'hugs', label: 'Hugs', price: '$1.49', Icon: HandHeart },
  { id: 'smiles', label: 'Smiles', price: '$0.99', Icon: Smile },
]

const NAUGHTY_PATTERNS = [
  /\b(adult|18\+|nsfw|explicit|naughty|dirty|spicy|erotic|sexual|sensual)\b/i,
  /\b(sex|sexy|sext|sexting|horny|aroused|turned on|turn me on|lust|desire|fantasy|fantasies)\b/i,
  /\b(nudes?|naked|undress|strip|striptease|lingerie|thong|panties|bra)\b/i,
  /\b(onlyfans|fanvue|porn|porno|xxx|camgirl|cam boy|webcam|escort|hookup|hook up)\b/i,
  /\b(fuck|fucking|fuck me|suck|lick|ride|grind|moan|dirty talk|send pics|send nudes)\b/i,
  /\b(blowjob|handjob|anal|oral|orgasm|climax|cum|cumming|ejaculate|dick|cock|penis|pussy|vagina|clit|boobs?|breasts?|tits?|ass|butt)\b/i,
  /\b(master|mistress|slave|submissive|sub|dom|domme|bdsm|kink|kinky|fetish|spank|choke|collar|leash|roleplay|role play)\b/i,
  /\b(sugar daddy|sugar baby|feet pics|foot fetish|lap dance|thirst trap)\b/i,
]

function isNaughtyMessage(text: string) {
  const normalized = text
    .toLowerCase()
    .replace(/[^a-z0-9+]+/g, ' ')
    .trim()
  const compact = normalized.replace(/\s+/g, '')

  return (
    NAUGHTY_PATTERNS.some((pattern) => pattern.test(normalized)) ||
    /\b(master\s*bait(?:e|ing)?|mastur\s*bat(?:e|ing|ion)?|jerk\s*off|jacking\s*off)\b/i.test(normalized) ||
    /(masterbait|masterbating|masturbat|jerkoff|jackingoff)/i.test(compact)
  )
}

type BrowserSpeechRecognition = {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionEvent = {
  resultIndex: number
  results: {
    length: number
    [index: number]: {
      isFinal: boolean
      [index: number]: { transcript: string }
    }
  }
}

type SpeechRecognitionErrorEvent = {
  error: string
}

declare global {
  interface Window {
    SpeechRecognition?: new () => BrowserSpeechRecognition
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition
  }
}

interface Props {
  conversationId?: string
}

export default function ChatInterface({ conversationId: initialConvoId }: Props) {
  const { user, token } = useAuthStore()
  const {
    messages, streamingContent, isStreaming, isConnected,
    currentConversationId, setConversationId, addMessage, appendStreamToken,
    finalizeStream, clearStream, setConnected, clearMessages,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [isWaiting, setIsWaiting] = useState(false)
  const [showPricing, setShowPricing] = useState(false)
  const [voiceCallActive, setVoiceCallActive] = useState(false)
  const [muted, setMuted] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(true)
  const [showFanvuePrompt, setShowFanvuePrompt] = useState(false)
  const [selectedGift, setSelectedGift] = useState(GIFT_OPTIONS[0].id)
  const [giftMessage, setGiftMessage] = useState('')
  const [giftLoading, setGiftLoading] = useState<string | null>(null)
  const [messagesHydrated, setMessagesHydrated] = useState(false)
  const wsRef = useRef<AmyWebSocket | null>(null)
  const setIsWaitingRef = useRef(setIsWaiting)
  const mutedRef = useRef(muted)
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const recognitionRunningRef = useRef(false)
  const sendMessageRef = useRef<(text: string, voiceUsed?: boolean) => Promise<void>>(async () => {})
  const speechDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const accumulatedTranscriptRef = useRef('')
  const isBusyRef = useRef(false)
  const isSpeakingRef = useRef(isSpeaking)
  const streamingContentRef = useRef(streamingContent)
  const voiceCallActiveRef = useRef(voiceCallActive)
  const confirmedGiftSessionRef = useRef<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const navigate = useNavigate()
  const location = useLocation()

  const canUseVoice = user?.subscription_tier !== 'free'
  const isEmpty = messages.length === 0 && !isStreaming && !isWaiting

  useEffect(() => {
    setIsWaitingRef.current = setIsWaiting
  })

  useEffect(() => {
    mutedRef.current = muted
  }, [muted])

  useEffect(() => {
    isBusyRef.current = isStreaming || isWaiting
  }, [isStreaming, isWaiting])

  useEffect(() => {
    isSpeakingRef.current = isSpeaking
  }, [isSpeaking])

  useEffect(() => {
    streamingContentRef.current = streamingContent
  }, [streamingContent])

  useEffect(() => {
    voiceCallActiveRef.current = voiceCallActive
  }, [voiceCallActive])

  const speakAsAmy = useCallback(async (content: string) => {
    if (!content.trim()) return
    if (user?.subscription_tier === 'free') {
      setShowPricing(true)
      return
    }

    // Set ref synchronously BEFORE stopping recognition so that onend and
    // onresult both see isSpeaking=true and won't restart the mic or process
    // captured audio as a user message. React state (setIsSpeaking) is async
    // and would be too late — the ref is what the callbacks actually check.
    isSpeakingRef.current = true
    recognitionRunningRef.current = false
    recognitionRef.current?.stop()
    setIsListening(false)
    setIsSpeaking(true)
    // Cancel any pending debounced send — Amy's voice must never trigger a message
    if (speechDebounceRef.current) { clearTimeout(speechDebounceRef.current); speechDebounceRef.current = null }
    accumulatedTranscriptRef.current = ''

    try {
      const buffer = await voiceApi.synthesize(content)
      await playAudioBuffer(buffer)
    } catch {
      toast.error("Couldn't play Amy's voice. Check the ElevenLabs voice settings.")
    } finally {
      isSpeakingRef.current = false
      setIsSpeaking(false)
    }
  }, [user?.subscription_tier])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  useEffect(() => {
    if (initialConvoId) {
      setMessagesHydrated(false)
      conversationsApi.get(initialConvoId).then(({ data }) => {
        const convo = data as Conversation
        clearMessages()
        setConversationId(convo.conversation_id)
        convo.messages.forEach((m) => addMessage(m as ChatMessage))
        setMessagesHydrated(true)
      }).catch(() => {
        toast.error('Conversation not found')
        navigate('/chat')
      })
    } else if (!initialConvoId) {
      clearMessages()
      setMessagesHydrated(true)
    }
  }, [initialConvoId, clearMessages, setConversationId, addMessage, navigate])

  useEffect(() => {
    if (!messagesHydrated) return

    const params = new URLSearchParams(location.search)
    const sessionId = params.get('gift_session_id')
    const canceled = params.get('gift') === 'canceled'

    if (canceled) {
      toast('Gift checkout canceled.')
      navigate(location.pathname, { replace: true })
      return
    }

    if (!sessionId || confirmedGiftSessionRef.current === sessionId) return
    confirmedGiftSessionRef.current = sessionId

    stripeApi.confirmGift(sessionId).then(({ data }) => {
      const now = new Date().toISOString()
      if (data.conversation_id) setConversationId(data.conversation_id)
      addMessage({
        role: 'user',
        content: data.user_message,
        timestamp: now,
        voice_used: false,
      })
      addMessage({
        role: 'assistant',
        content: data.assistant_message,
        timestamp: now,
        voice_used: false,
      })
      toast.success(`${data.gift_label} sent to Amy`)
      navigate(location.pathname, { replace: true })
    }).catch(() => {
      toast.error('Could not confirm that gift payment.')
      navigate(location.pathname, { replace: true })
    })
  }, [addMessage, location.pathname, location.search, messagesHydrated, navigate, setConversationId])

  useEffect(() => {
    if (!token) return

    const ws = new AmyWebSocket(
      token,
      (msg) => {
        if (msg.type === 'token' && msg.content) {
          appendStreamToken(msg.content)
          setIsWaiting(false)
        } else if (msg.type === 'done') {
          const response = msg.full_response || streamingContentRef.current
          if (msg.conversation_id) setConversationId(msg.conversation_id)
          finalizeStream(response)
          if (voiceCallActiveRef.current && !mutedRef.current) {
            void speakAsAmy(response)
          }
        } else if (msg.type === 'error') {
          toast.error(msg.message || 'Something went wrong')
          setIsWaiting(false)
        } else if (msg.type === 'redirect') {
          setShowFanvuePrompt(true)
          window.location.href = msg.url || FANVUE_URL
        }
      },
      () => setConnected(true),
      () => {
        setConnected(false)
        clearStream()
        setIsWaitingRef.current(false)
      },
    )
    ws.connect()
    wsRef.current = ws

    return () => ws.disconnect()
  }, [
    token,
    appendStreamToken,
    clearStream,
    finalizeStream,
    setConnected,
    setConversationId,
    speakAsAmy,
  ])

  const sendMessage = useCallback(async (text: string, voiceUsed = false) => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming || isWaiting) return

    if (isNaughtyMessage(trimmed)) {
      setShowFanvuePrompt(true)
      window.location.href = FANVUE_URL
      return
    }

    const userMsg: ChatMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
      voice_used: voiceUsed,
    }
    addMessage(userMsg)
    setInput('')
    setIsWaiting(true)

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      if (!wsRef.current?.isConnected) {
        throw new Error('Not connected')
      }
      wsRef.current.sendMessage(trimmed, currentConversationId || undefined, voiceUsed)
    } catch {
      toast.error('Connection issue. Reconnecting...')
      setIsWaiting(false)
    }
  }, [isStreaming, isWaiting, currentConversationId, addMessage])

  useEffect(() => {
    sendMessageRef.current = sendMessage
  }, [sendMessage])

  const stopListening = useCallback(() => {
    recognitionRunningRef.current = false
    setIsListening(false)
    recognitionRef.current?.stop()
  }, [])

  const startListening = useCallback(() => {
    if (!canUseVoice || mutedRef.current || isBusyRef.current || isSpeakingRef.current) return

    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) {
      setVoiceSupported(false)
      return
    }

    let recognition = recognitionRef.current
    if (!recognition) {
      recognition = new Recognition()
      recognition.continuous = true
      recognition.interimResults = false
      recognition.lang = 'en-US'
      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i]
          if (result.isFinal) {
            accumulatedTranscriptRef.current += result[0].transcript
          }
        }

        if (!accumulatedTranscriptRef.current.trim() || isBusyRef.current || isSpeakingRef.current) return

        // Wait 2 seconds of silence before sending — prevents cutting the user off mid-sentence
        if (speechDebounceRef.current) clearTimeout(speechDebounceRef.current)
        speechDebounceRef.current = setTimeout(() => {
          const text = accumulatedTranscriptRef.current.trim()
          accumulatedTranscriptRef.current = ''
          speechDebounceRef.current = null
          if (!text || isBusyRef.current || isSpeakingRef.current) return
          recognitionRunningRef.current = false
          setIsListening(false)
          recognitionRef.current?.stop()
          void sendMessageRef.current(text, true)
        }, 2000)
      }
      recognition.onerror = (event) => {
        recognitionRunningRef.current = false
        setIsListening(false)
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          toast.error('Microphone permission is blocked. Allow mic access to talk with Amy.')
          setVoiceCallActive(false)
        }
      }
      recognition.onend = () => {
        recognitionRunningRef.current = false
        setIsListening(false)
        if (voiceCallActiveRef.current && !mutedRef.current && !isBusyRef.current && !isSpeakingRef.current) {
          // 900ms delay gives audio output time to fully stop before mic reopens
          window.setTimeout(() => startListening(), 2000)
        }
      }
      recognitionRef.current = recognition
    }

    if (recognitionRunningRef.current) return
    try {
      recognition.start()
      recognitionRunningRef.current = true
      setIsListening(true)
    } catch {
      recognitionRunningRef.current = false
      setIsListening(false)
    }
  }, [canUseVoice])

  useEffect(() => {
    if (voiceCallActive && canUseVoice && !muted && !isWaiting && !isStreaming && !isSpeaking) {
      startListening()
    } else if (!voiceCallActive || muted || isWaiting || isStreaming || isSpeaking) {
      stopListening()
    }
  }, [canUseVoice, isSpeaking, isStreaming, isWaiting, muted, startListening, stopListening, voiceCallActive])

  useEffect(() => () => stopListening(), [stopListening])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
  }

  const toggleCall = () => {
    if (!canUseVoice) {
      setShowPricing(true)
      return
    }
    setVoiceCallActive((value) => !value)
  }

  const sendGift = async () => {
    setGiftLoading(selectedGift)
    try {
      const { data } = await stripeApi.buyGift({
        gift_type: selectedGift,
        personal_message: giftMessage.trim(),
        conversation_id: currentConversationId,
      })
      window.location.href = data.checkout_url
    } catch {
      toast.error('Could not open gift checkout. Try again!')
      setGiftLoading(null)
    }
  }

  const startNewConversation = () => {
    clearMessages()
    navigate('/chat')
  }

  return (
    <div className="h-[100dvh] bg-white text-charcoal-900 flex flex-col overflow-hidden">
      <div className="h-16 border-b border-stone-200 px-5 lg:px-8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            className="w-9 h-9 rounded-lg border border-stone-200 text-stone-500 flex items-center justify-center hover:bg-stone-50"
            title="Apps"
          >
            <Grid2X2 size={17} />
          </button>
          <div className="font-semibold truncate">Amy Silverstein</div>
          <div className="h-5 w-px bg-stone-200" />
          <div className="text-sm font-medium text-stone-600">Main</div>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${isConnected ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-100 text-stone-500'}`}>
            {isConnected ? 'Live 100%' : 'Connecting'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => toast('Voice settings use ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID from backend/.env')}
            className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-stone-50"
          >
            <SlidersHorizontal size={16} />
            Voice settings
          </button>
          <button
            type="button"
            className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium hover:bg-stone-50"
          >
            <Wrench size={16} />
            Mock tools
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-stone-100 text-stone-500">Off</span>
          </button>
          <button onClick={startNewConversation} className="btn-ghost flex items-center gap-1.5 text-sm">
            <Plus size={15} />
            New chat
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">
        <section className="relative flex-none overflow-y-auto overflow-x-hidden lg:flex-1 bg-[repeating-linear-gradient(135deg,#fbfbfb_0,#fbfbfb_12px,#f7f7f7_12px,#f7f7f7_24px)]">
          <div className="flex flex-col px-3 py-2 sm:px-6 sm:py-6">
            <div className="shrink-0 flex items-center justify-center pb-2 sm:pb-4">
              <div className="w-full max-w-5xl grid grid-cols-[minmax(104px,34vw)_minmax(140px,1fr)] xl:grid-cols-[minmax(200px,320px)_minmax(220px,1fr)] gap-4 sm:gap-8 items-center">
              <div className={`amy-picture-section ${isSpeaking ? 'amy-picture-speaking' : ''}`}>
                <img
                  src="/amy-portrait.png"
                  alt="Amy Silverstein"
                  className="w-full h-full object-cover"
                />
                <div className="amy-mouth" aria-hidden="true" />
                <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/65 via-black/18 to-transparent">
                  <p className="text-white font-semibold leading-tight">Amy Silverstein</p>
                  <p className="text-white/75 text-xs mt-0.5">Age 39 · Voice companion</p>
                </div>
              </div>

              <div className="flex flex-col items-center justify-center min-w-0">
                <div className={`voice-orb ${voiceCallActive ? 'voice-orb-live' : ''} ${isSpeaking ? 'voice-orb-speaking' : ''}`} />
                <button
                  type="button"
                  onClick={toggleCall}
                  className={`relative z-10 mt-4 w-14 h-14 rounded-full border-4 border-white shadow-card flex items-center justify-center transition-all ${
                    voiceCallActive ? 'bg-rose-500 text-white hover:bg-rose-600' : 'bg-charcoal-900 text-white hover:bg-charcoal-800'
                  }`}
                  title={voiceCallActive ? 'End voice call' : 'Start voice call'}
                >
                  {voiceCallActive ? <PhoneOff size={22} /> : <Phone size={22} />}
                </button>
              </div>
            </div>
          </div>

            <div className="shrink-0 mx-auto w-full max-w-3xl">
              <div className="rounded-2xl border border-stone-200 bg-white/95 shadow-soft p-2 sm:p-3">
                <div className="grid grid-cols-5 gap-1 sm:gap-2">
                  {GIFT_OPTIONS.map(({ id, label, price, Icon }) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setSelectedGift(id)}
                      className={`h-10 sm:h-16 rounded-xl border flex flex-col items-center justify-center gap-0.5 sm:gap-1 transition-colors ${
                        selectedGift === id ? 'border-sage-400 bg-sage-50 text-sage-800' : 'border-stone-200 text-stone-600 hover:bg-stone-50'
                      }`}
                      title={`${label} ${price}`}
                    >
                      <Icon size={17} />
                      <span className="text-[10px] sm:text-[11px] font-semibold leading-none">{label}</span>
                      <span className="text-[10px] text-stone-400 leading-none">{price}</span>
                    </button>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    value={giftMessage}
                    onChange={(e) => setGiftMessage(e.target.value)}
                    maxLength={160}
                    placeholder="Add a personal message"
                    className="min-w-0 flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:border-sage-400"
                  />
                  <button
                    type="button"
                    onClick={sendGift}
                    disabled={!!giftLoading}
                    className="shrink-0 rounded-xl bg-charcoal-900 px-4 py-2 text-sm font-semibold text-white hover:bg-charcoal-800 disabled:bg-stone-300"
                  >
                    {giftLoading ? 'Opening...' : 'Send gift'}
                  </button>
                </div>
              </div>

              <div className="mx-auto mt-1.5 sm:mt-3 flex w-fit items-center gap-2 rounded-full bg-white/95 border border-stone-200 shadow-soft px-4 py-2 sm:py-3">
                <button
                  type="button"
                  onClick={() => toast('Voice style is controlled by backend ElevenLabs settings.')}
                  className="text-stone-500 hover:text-charcoal-900"
                  title="Voice settings"
                >
                  <SlidersHorizontal size={16} />
                </button>
                <div className="w-px h-5 bg-stone-200" />
                <button
                  type="button"
                  onClick={() => setMuted((value) => !value)}
                  className="flex items-center gap-1.5 text-sm font-medium text-charcoal-900"
                  title={muted ? 'Unmute Amy voice' : 'Mute Amy voice'}
                >
                  {muted ? <MicOff size={16} /> : <Mic size={16} />}
                  {muted ? 'Muted' : 'Mute'}
                </button>
              </div>
            </div>
          </div>

          <div className="absolute top-6 left-8 hidden md:block">
            <div className="flex items-center gap-2 rounded-full bg-white/90 border border-stone-200 px-3 py-2 text-xs text-stone-500">
              <span className={`w-2 h-2 rounded-full ${voiceCallActive ? 'bg-emerald-500' : 'bg-stone-300'}`} />
              {voiceCallActive ? isSpeaking ? 'Amy is speaking' : 'Voice call active' : 'Voice call idle'}
            </div>
          </div>
        </section>

        <section className="flex-1 min-h-0 w-full lg:w-[40%] lg:min-w-[390px] border-t lg:border-t-0 lg:border-l border-stone-200 bg-white flex flex-col">
          <div className="flex-1 min-h-0 overflow-y-auto px-5 py-5 space-y-5">
            {isEmpty && (
              <div className="h-full min-h-[360px] flex flex-col items-center justify-center text-center text-stone-400">
                <div className="w-10 h-10 rounded-xl border border-stone-200 flex items-center justify-center mb-3">
                  <MessageCircle size={18} />
                </div>
                <p className="max-w-[230px] text-sm leading-relaxed">
                  Call or send a message to start a new conversation
                </p>
              </div>
            )}

            {showFanvuePrompt && (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-soft">
                <p className="font-medium">That conversation belongs on Fanvue.</p>
                <p className="mt-1 text-rose-700">Tap below if your browser did not redirect automatically.</p>
                <button
                  type="button"
                  onClick={() => window.location.href = FANVUE_URL}
                  className="mt-3 w-full rounded-xl bg-charcoal-900 px-4 py-2.5 text-white font-medium hover:bg-charcoal-800 transition-colors"
                >
                  Continue to Fanvue
                </button>
              </div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble
                key={i}
                message={msg}
                onPlayVoice={speakAsAmy}
                canPlayVoice={canUseVoice}
              />
            ))}

            {isWaiting && !streamingContent && <TypingIndicator />}
            {streamingContent && <StreamingBubble content={streamingContent} />}
            <div ref={bottomRef} />
          </div>

          <div className="px-5 py-5 shrink-0">
            <div className="rounded-3xl border border-stone-200 bg-white shadow-soft p-3 flex items-end gap-3">
              {canUseVoice && (
                <VoiceInput onTranscribed={(t) => sendMessage(t, true)} disabled={isStreaming || isWaiting || muted} />
              )}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Send a message to start a chat"
                rows={1}
                className="flex-1 resize-none outline-none text-charcoal-800 placeholder-stone-500 text-sm leading-relaxed px-1 py-3"
                disabled={isStreaming || isWaiting}
                style={{ maxHeight: 150 }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isStreaming || isWaiting}
                className="w-11 h-11 bg-charcoal-900 hover:bg-charcoal-800 disabled:bg-stone-200 disabled:text-stone-400 text-white rounded-full flex items-center justify-center transition-all shrink-0"
                title="Send"
              >
                {input.trim() ? <Send size={17} /> : <Play size={17} fill="currentColor" />}
              </button>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-stone-400">
              <span>
                {!voiceSupported ? 'Browser speech recognition unavailable' :
                  isListening ? 'Listening...' :
                  voiceCallActive ? 'Talk freely. Amy will answer out loud.' :
                  canUseVoice ? 'Premium voice enabled' : 'Free tier'}
              </span>
              <button
                type="button"
                onClick={() => canUseVoice ? setVoiceCallActive((value) => !value) : setShowPricing(true)}
                className="inline-flex items-center gap-1.5 text-sage-700 hover:text-sage-800 font-medium"
              >
                <Volume2 size={13} />
                {canUseVoice ? voiceCallActive ? 'Stop voice mode' : 'Start voice mode' : 'Upgrade for voice'}
              </button>
            </div>
          </div>
        </section>
      </div>

      {showPricing && <PricingModal onClose={() => setShowPricing(false)} />}
    </div>
  )
}
