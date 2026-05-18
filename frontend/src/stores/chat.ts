import { create } from 'zustand'
import type { ChatMessage, ConversationSummary } from '@/types'

interface ChatState {
  currentConversationId: string | null
  messages: ChatMessage[]
  streamingContent: string
  isStreaming: boolean
  isConnected: boolean
  conversations: ConversationSummary[]

  setConversationId: (id: string | null) => void
  addMessage: (msg: ChatMessage) => void
  appendStreamToken: (token: string) => void
  finalizeStream: (fullResponse: string) => void
  clearStream: () => void
  setStreaming: (v: boolean) => void
  setConnected: (v: boolean) => void
  setConversations: (convos: ConversationSummary[]) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  currentConversationId: null,
  messages: [],
  streamingContent: '',
  isStreaming: false,
  isConnected: false,
  conversations: [],

  setConversationId: (id) => set({ currentConversationId: id }),

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  appendStreamToken: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token, isStreaming: true })),

  finalizeStream: (fullResponse) => {
    const content = fullResponse || get().streamingContent
    if (!content) {
      set({ streamingContent: '', isStreaming: false })
      return
    }

    const amyMsg: ChatMessage = {
      role: 'assistant',
      content,
      timestamp: new Date().toISOString(),
      voice_used: false,
    }
    set((state) => ({
      messages: [...state.messages, amyMsg],
      streamingContent: '',
      isStreaming: false,
    }))
  },

  clearStream: () => set({ streamingContent: '', isStreaming: false }),

  setStreaming: (v) => set({ isStreaming: v }),
  setConnected: (v) => set({ isConnected: v }),

  setConversations: (convos) => set({ conversations: convos }),

  clearMessages: () => set({ messages: [], currentConversationId: null, streamingContent: '', isStreaming: false }),
}))
