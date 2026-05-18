import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, CheckCircle, Plus, Heart, Target, AlertCircle, Zap, Trophy } from 'lucide-react'
import toast from 'react-hot-toast'
import { memoryApi } from '@/lib/api'
import type { MemoryBank, LifeEvent, Goal, BehavioralPattern, Sensitivity, MemoryExtract } from '@/types'

const SECTION_CONFIG = {
  life_events: { label: 'Life Events', icon: Heart, color: 'text-blush-400', bg: 'bg-blush-100' },
  behavioral_patterns: { label: 'Your Patterns', icon: Zap, color: 'text-sage-600', bg: 'bg-sage-100' },
  goals: { label: 'Your Goals', icon: Target, color: 'text-sage-600', bg: 'bg-sage-100' },
  sensitivities: { label: 'Handle with Care', icon: AlertCircle, color: 'text-blush-400', bg: 'bg-blush-100' },
  memory_extracts: { label: 'What Amy Remembers', icon: Trophy, color: 'text-sage-600', bg: 'bg-sage-100' },
}

export default function MemoryBankViewer() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery<MemoryBank>({
    queryKey: ['memory'],
    queryFn: () => memoryApi.getBank().then((r) => r.data),
  })

  const deleteEvent = useMutation({
    mutationFn: (id: string) => memoryApi.deleteLifeEvent(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Removed') },
  })
  const deletePattern = useMutation({
    mutationFn: (id: string) => memoryApi.deletePattern(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Removed') },
  })
  const achieveGoal = useMutation({
    mutationFn: (id: string) => memoryApi.achieveGoal(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Goal achieved! 🎉') },
  })
  const deleteGoal = useMutation({
    mutationFn: (id: string) => memoryApi.deleteGoal(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Removed') },
  })
  const deleteSensitivity = useMutation({
    mutationFn: (id: string) => memoryApi.deleteSensitivity(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Removed') },
  })
  const deleteExtract = useMutation({
    mutationFn: (id: string) => memoryApi.deleteExtract(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['memory'] }); toast.success('Removed') },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="typing-dots"><span /><span /><span /></div>
      </div>
    )
  }

  if (!data) return null

  const hasAnyMemory = data.life_events.length + data.behavioral_patterns.length + data.goals.length + data.sensitivities.length + data.memory_extracts.length > 0

  return (
    <div className="space-y-6">
      {!hasAnyMemory && (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">🧠</div>
          <p className="text-stone-500">Amy doesn't know much about you yet. Start a conversation!</p>
        </div>
      )}

      {/* Life Events */}
      {data.life_events.length > 0 && (
        <MemorySection title="Life Events" icon={Heart} iconColor="text-blush-400" bg="bg-blush-100">
          {data.life_events.map((e: LifeEvent) => (
            <MemoryCard
              key={e.event_id}
              title={e.event_type.replace('_', ' ')}
              body={e.description}
              badge={`Weight: ${e.emotional_weight}/10`}
              badgeColor={e.emotional_weight >= 7 ? 'bg-blush-100 text-blush-400' : 'bg-cream-200 text-stone-500'}
              tag={e.still_processing ? 'still processing' : undefined}
              onDelete={() => deleteEvent.mutate(e.event_id)}
            />
          ))}
        </MemorySection>
      )}

      {/* Behavioral Patterns */}
      {data.behavioral_patterns.length > 0 && (
        <MemorySection title="Your Patterns" icon={Zap} iconColor="text-sage-600" bg="bg-sage-100">
          {data.behavioral_patterns.map((p: BehavioralPattern) => (
            <MemoryCard
              key={p.pattern_id}
              title={p.pattern_name.replace(/_/g, ' ')}
              body={p.description}
              badge={`Seen ${p.frequency_detected}x`}
              badgeColor="bg-sage-100 text-sage-700"
              onDelete={() => deletePattern.mutate(p.pattern_id)}
            />
          ))}
        </MemorySection>
      )}

      {/* Goals */}
      {data.goals.length > 0 && (
        <MemorySection title="Your Goals" icon={Target} iconColor="text-sage-600" bg="bg-sage-100">
          {data.goals.map((g: Goal) => (
            <MemoryCard
              key={g.goal_id}
              title={g.category}
              body={g.goal_text}
              badge={g.achieved_date ? 'Achieved!' : g.category}
              badgeColor={g.achieved_date ? 'bg-sage-100 text-sage-700' : 'bg-cream-200 text-stone-500'}
              onDelete={() => deleteGoal.mutate(g.goal_id)}
              extraAction={
                !g.achieved_date
                  ? { label: 'Mark achieved', icon: CheckCircle, onClick: () => achieveGoal.mutate(g.goal_id) }
                  : undefined
              }
            />
          ))}
        </MemorySection>
      )}

      {/* Sensitivities */}
      {data.sensitivities.length > 0 && (
        <MemorySection title="Handle with Care" icon={AlertCircle} iconColor="text-blush-400" bg="bg-blush-100">
          {data.sensitivities.map((s: Sensitivity) => (
            <MemoryCard
              key={s.sensitivity_id}
              title={s.topic}
              body={s.description}
              note={s.handling_notes || undefined}
              onDelete={() => deleteSensitivity.mutate(s.sensitivity_id)}
            />
          ))}
        </MemorySection>
      )}

      {/* Memory Extracts */}
      {data.memory_extracts.length > 0 && (
        <MemorySection title="What Amy Remembers" icon={Trophy} iconColor="text-sage-600" bg="bg-sage-100">
          {data.memory_extracts.slice(0, 20).map((m: MemoryExtract) => (
            <MemoryCard
              key={m.memory_id}
              title={m.memory_type}
              body={m.content}
              badge={`Importance: ${m.importance_score}/10`}
              badgeColor={m.importance_score >= 7 ? 'bg-sage-100 text-sage-700' : 'bg-cream-200 text-stone-500'}
              onDelete={() => deleteExtract.mutate(m.memory_id)}
            />
          ))}
        </MemorySection>
      )}
    </div>
  )
}

function MemorySection({ title, icon: Icon, iconColor, bg, children }: {
  title: string; icon: React.ElementType; iconColor: string; bg: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-7 h-7 ${bg} rounded-lg flex items-center justify-center`}>
          <Icon size={14} className={iconColor} />
        </div>
        <h3 className="font-medium text-charcoal-800">{title}</h3>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function MemoryCard({ title, body, badge, badgeColor, tag, note, onDelete, extraAction }: {
  title: string; body: string; badge?: string; badgeColor?: string; tag?: string;
  note?: string; onDelete: () => void;
  extraAction?: { label: string; icon: React.ElementType; onClick: () => void }
}) {
  return (
    <div className="bg-white rounded-xl px-4 py-3 flex gap-3 group shadow-soft">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className="text-xs font-semibold text-charcoal-800 capitalize">{title}</span>
          {badge && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${badgeColor || 'bg-cream-200 text-stone-500'}`}>
              {badge}
            </span>
          )}
          {tag && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-blush-100 text-blush-400">{tag}</span>
          )}
        </div>
        <p className="text-sm text-stone-600 leading-snug">{body}</p>
        {note && <p className="text-xs text-stone-400 mt-1 italic">{note}</p>}
      </div>
      <div className="flex items-start gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        {extraAction && (
          <button
            onClick={extraAction.onClick}
            className="p-1 text-sage-500 hover:text-sage-700 transition-colors"
            title={extraAction.label}
          >
            <extraAction.icon size={14} />
          </button>
        )}
        <button
          onClick={onDelete}
          className="p-1 text-stone-300 hover:text-blush-400 transition-colors"
          title="Remove"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}
