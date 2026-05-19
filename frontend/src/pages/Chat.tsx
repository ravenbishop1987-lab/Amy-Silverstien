import { useState } from 'react'
import { Lock, MessageCircle } from 'lucide-react'
import { useParams } from 'react-router-dom'
import LoginForm from '@/components/auth/LoginForm'
import SignupForm from '@/components/auth/SignupForm'
import ChatInterface from '@/components/chat/ChatInterface'
import { useAuthStore } from '@/stores/auth'

function ChatAuthGate() {
  const [mode, setMode] = useState<'signup' | 'login'>('signup')

  return (
    <div className="h-[100dvh] bg-white text-charcoal-900 flex flex-col overflow-hidden">
      <div className="h-16 border-b border-stone-200 px-5 lg:px-8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-sage-100 text-sage-700 flex items-center justify-center">
            <MessageCircle size={18} />
          </div>
          <div>
            <div className="font-semibold leading-tight">Amy Silverstein</div>
            <div className="text-xs text-stone-500">Create an account to start chatting</div>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 rounded-full border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-500">
          <Lock size={13} />
          Members only
        </div>
      </div>

      <div className="flex-1 min-h-0 grid lg:grid-cols-[minmax(0,1fr)_430px] overflow-hidden">
        <section className="relative min-h-[360px] lg:min-h-0 overflow-hidden bg-[repeating-linear-gradient(135deg,#fbfbfb_0,#fbfbfb_12px,#f7f7f7_12px,#f7f7f7_24px)]">
          <div className="absolute inset-0 flex items-center justify-center p-6">
            <div className="w-full max-w-4xl grid grid-cols-[minmax(120px,280px)_minmax(180px,1fr)] gap-5 sm:gap-10 items-center opacity-40 blur-[1px] pointer-events-none select-none">
              <div className="amy-picture-section">
                <img src="/amy-portrait.png" alt="Amy Silverstein" className="w-full h-full object-cover" />
                <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/65 via-black/18 to-transparent">
                  <p className="text-white font-semibold leading-tight">Amy Silverstein</p>
                  <p className="text-white/75 text-xs mt-0.5">Age 39 · Voice companion</p>
                </div>
              </div>
              <div className="flex flex-col items-center justify-center">
                <div className="voice-orb" />
                <div className="mt-4 w-14 h-14 rounded-full bg-charcoal-900 text-white shadow-card flex items-center justify-center">
                  <Lock size={22} />
                </div>
              </div>
            </div>
          </div>

          <div className="absolute inset-0 bg-white/55 backdrop-blur-[2px]" />
          <div className="relative z-10 h-full min-h-[360px] flex items-center justify-center px-6 py-10 text-center">
            <div className="max-w-md">
              <div className="mx-auto mb-4 w-12 h-12 rounded-2xl bg-charcoal-900 text-white flex items-center justify-center shadow-card">
                <Lock size={20} />
              </div>
              <h1 className="text-2xl sm:text-3xl font-serif font-semibold text-charcoal-900">
                Join before you chat
              </h1>
              <p className="mt-3 text-sm sm:text-base text-stone-600 leading-relaxed">
                Your account keeps Amy's memory, conversation history, and voice credits tied to you.
              </p>
            </div>
          </div>
        </section>

        <section className="min-h-0 overflow-y-auto border-t lg:border-t-0 lg:border-l border-stone-200 bg-white px-5 py-6 sm:px-8">
          <div className="mx-auto max-w-sm">
            <div className="mb-5 grid grid-cols-2 rounded-xl border border-stone-200 bg-stone-50 p-1">
              <button
                type="button"
                onClick={() => setMode('signup')}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${mode === 'signup' ? 'bg-white text-charcoal-900 shadow-sm' : 'text-stone-500'}`}
              >
                Create account
              </button>
              <button
                type="button"
                onClick={() => setMode('login')}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${mode === 'login' ? 'bg-white text-charcoal-900 shadow-sm' : 'text-stone-500'}`}
              >
                Sign in
              </button>
            </div>

            {mode === 'signup' ? <SignupForm /> : <LoginForm />}
          </div>
        </section>
      </div>
    </div>
  )
}

export default function Chat() {
  const { conversationId } = useParams<{ conversationId?: string }>()
  const { token, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="h-[100dvh] bg-cream-100 flex items-center justify-center">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    )
  }

  if (!token) return <ChatAuthGate />

  return <ChatInterface conversationId={conversationId} />
}
