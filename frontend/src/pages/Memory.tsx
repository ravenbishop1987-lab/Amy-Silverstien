import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import toast from 'react-hot-toast'
import MemoryBankViewer from '@/components/memory/MemoryBankViewer'
import { memoryApi } from '@/lib/api'

type AddType = 'event' | 'goal' | 'sensitivity' | null

export default function Memory() {
  const [adding, setAdding] = useState<AddType>(null)
  const qc = useQueryClient()

  return (
    <div className="h-screen overflow-y-auto bg-cream-100 px-8 py-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="font-serif text-2xl text-charcoal-900">Memory Bank</h1>
            <p className="text-sm text-stone-500 mt-1">
              Everything Amy knows about you — fully editable
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setAdding('goal')}
              className="btn-ghost text-sm flex items-center gap-1.5"
            >
              <Plus size={14} /> Add goal
            </button>
            <button
              onClick={() => setAdding('sensitivity')}
              className="btn-ghost text-sm flex items-center gap-1.5"
            >
              <Plus size={14} /> Add sensitivity
            </button>
          </div>
        </div>

        {/* Add forms */}
        {adding === 'goal' && (
          <AddGoalForm onDone={() => { qc.invalidateQueries({ queryKey: ['memory'] }); setAdding(null) }} onCancel={() => setAdding(null)} />
        )}
        {adding === 'sensitivity' && (
          <AddSensitivityForm onDone={() => { qc.invalidateQueries({ queryKey: ['memory'] }); setAdding(null) }} onCancel={() => setAdding(null)} />
        )}

        <MemoryBankViewer />
      </div>
    </div>
  )
}

function AddGoalForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [text, setText] = useState('')
  const [category, setCategory] = useState('confidence')

  const mutation = useMutation({
    mutationFn: () => memoryApi.createGoal({ goal_text: text, category }),
    onSuccess: () => { toast.success('Goal added!'); onDone() },
    onError: () => toast.error('Could not add goal'),
  })

  return (
    <div className="card mb-6 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-charcoal-800">Add a goal</h3>
        <button onClick={onCancel}><X size={16} className="text-stone-400" /></button>
      </div>
      <div className="space-y-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Build dating confidence, Set better boundaries..."
          className="input-base"
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="input-base">
          <option value="confidence">Confidence</option>
          <option value="boundaries">Boundaries</option>
          <option value="vulnerability">Vulnerability</option>
          <option value="communication">Communication</option>
          <option value="other">Other</option>
        </select>
        <button onClick={() => mutation.mutate()} disabled={!text.trim() || mutation.isPending} className="btn-primary w-full">
          {mutation.isPending ? 'Saving...' : 'Add goal'}
        </button>
      </div>
    </div>
  )
}

function AddSensitivityForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [topic, setTopic] = useState('')
  const [description, setDescription] = useState('')
  const [notes, setNotes] = useState('')

  const mutation = useMutation({
    mutationFn: () => memoryApi.createSensitivity({ topic, description, handling_notes: notes || undefined }),
    onSuccess: () => { toast.success('Sensitivity added!'); onDone() },
    onError: () => toast.error('Could not add sensitivity'),
  })

  return (
    <div className="card mb-6 animate-slide-up">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-charcoal-800">Add a sensitivity</h3>
        <button onClick={onCancel}><X size={16} className="text-stone-400" /></button>
      </div>
      <div className="space-y-3">
        <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic (e.g. abandonment, trust)" className="input-base" />
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Why is this sensitive for you?" className="input-base h-20 resize-none" />
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="How should Amy handle this? (optional)" className="input-base h-16 resize-none" />
        <button onClick={() => mutation.mutate()} disabled={!topic.trim() || !description.trim() || mutation.isPending} className="btn-primary w-full">
          {mutation.isPending ? 'Saving...' : 'Add sensitivity'}
        </button>
      </div>
    </div>
  )
}
