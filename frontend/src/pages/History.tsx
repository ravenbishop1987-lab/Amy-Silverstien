import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Trash2, MessageCircle } from 'lucide-react'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { conversationsApi } from '@/lib/api'
import type { ConversationSummary } from '@/types'

const MOOD_EMOJIS = ['', '😞', '😕', '😐', '🙂', '😊']

export default function History() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<ConversationSummary[]>({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list().then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
      toast.success('Conversation deleted')
    },
  })

  return (
    <div className="h-screen overflow-y-auto bg-cream-100 px-8 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="font-serif text-2xl text-charcoal-900">Conversation History</h1>
          <p className="text-sm text-stone-500 mt-1">All your past chats with Amy</p>
        </div>

        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="typing-dots"><span /><span /><span /></div>
          </div>
        )}

        {!isLoading && (!data || data.length === 0) && (
          <div className="text-center py-12">
            <MessageCircle size={40} className="text-stone-200 mx-auto mb-3" />
            <p className="text-stone-500">No conversations yet.</p>
            <Link to="/chat" className="text-sage-600 text-sm hover:underline mt-1 block">
              Start your first chat with Amy →
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {data?.map((convo) => (
            <div key={convo.conversation_id} className="card group flex gap-4 hover:shadow-card transition-shadow">
              <Link to={`/chat/${convo.conversation_id}`} className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-medium text-charcoal-800 truncate">
                    {convo.title || 'Untitled conversation'}
                  </h3>
                  <span className="text-xs text-stone-400 shrink-0">
                    {format(new Date(convo.date_started), 'MMM d')}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-xs text-stone-400">
                    {convo.message_count} messages
                  </span>
                  {convo.user_mood_before && (
                    <span className="text-xs text-stone-400">
                      Started: {MOOD_EMOJIS[convo.user_mood_before]}
                    </span>
                  )}
                  {convo.user_mood_after && (
                    <span className="text-xs text-stone-400">
                      Ended: {MOOD_EMOJIS[convo.user_mood_after]}
                    </span>
                  )}
                  {convo.topics_discussed?.slice(0, 2).map((t) => (
                    <span key={t} className="text-xs bg-sage-100 text-sage-700 px-2 py-0.5 rounded-full">
                      {t}
                    </span>
                  ))}
                </div>
              </Link>
              <button
                onClick={() => deleteMutation.mutate(convo.conversation_id)}
                className="opacity-0 group-hover:opacity-100 p-1.5 text-stone-300 hover:text-blush-400 transition-all self-start"
                title="Delete conversation"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
