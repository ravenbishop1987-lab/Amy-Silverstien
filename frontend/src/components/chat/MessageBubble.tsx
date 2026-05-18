import { Volume2 } from 'lucide-react'
import { format } from 'date-fns'
import type { ChatMessage } from '@/types'

interface Props {
  message: ChatMessage
  onPlayVoice?: (content: string) => void
  canPlayVoice?: boolean
}

export default function MessageBubble({ message, onPlayVoice, canPlayVoice }: Props) {
  const isAmy = message.role === 'assistant'
  const time = format(new Date(message.timestamp), 'h:mm a')

  if (isAmy) {
    return (
      <div className="flex items-end gap-3 animate-slide-up">
        {/* Amy avatar */}
        <div className="w-8 h-8 rounded-full bg-sage-400 flex items-center justify-center text-white text-xs font-semibold shrink-0 mb-1">
          A
        </div>
        <div className="flex flex-col gap-1 max-w-[80%] min-w-0">
          <div className="amy-bubble">
            <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
          </div>
          <div className="flex items-center gap-2 px-1">
            <span className="text-xs text-stone-400">{time}</span>
            {canPlayVoice && onPlayVoice && (
              <button
                onClick={() => onPlayVoice(message.content)}
                className="text-stone-400 hover:text-sage-500 transition-colors"
                title="Play as Amy's voice"
              >
                <Volume2 size={13} />
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end justify-end gap-3 animate-slide-up">
      <div className="flex flex-col items-end gap-1 max-w-[80%] min-w-0">
        <div className="user-bubble">
          <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
        </div>
        <span className="text-xs text-stone-400 px-1">{time}</span>
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-sage-400 flex items-center justify-center text-white text-xs font-semibold shrink-0">
        A
      </div>
      <div className="amy-bubble py-3">
        <div className="typing-dots flex items-center gap-1">
          <span /><span /><span />
        </div>
      </div>
    </div>
  )
}

export function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex items-end gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-sage-400 flex items-center justify-center text-white text-xs font-semibold shrink-0">
        A
      </div>
      <div className="amy-bubble max-w-[80%] min-w-0">
        <p className="whitespace-pre-wrap break-words leading-relaxed">{content}</p>
        <span className="inline-block w-1 h-4 bg-sage-400 ml-0.5 animate-pulse-soft" />
      </div>
    </div>
  )
}
