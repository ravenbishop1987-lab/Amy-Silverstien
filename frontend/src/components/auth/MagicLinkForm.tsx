import { useState } from 'react'
import { Mail } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import GoogleAuthButton from './GoogleAuthButton'

type Props = {
  mode: 'login' | 'signup'
}

export default function MagicLinkForm({ mode }: Props) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [devLink, setDevLink] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setDevLink(null)
    try {
      const { data } = await authApi.requestMagicLink(email)
      setSent(true)
      if (data.magic_link) setDevLink(data.magic_link)
      toast.success('Check your email for your sign-in link')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Could not send sign-in link')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <GoogleAuthButton mode={mode} />
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-stone-200" />
        <span className="text-xs text-stone-400">or</span>
        <div className="h-px flex-1 bg-stone-200" />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-charcoal-800 mb-1.5">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-base"
            placeholder="you@example.com"
            required
            autoComplete="email"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full mt-2 flex items-center justify-center gap-2">
          <Mail size={16} />
          {loading ? 'Sending link...' : sent ? 'Send another link' : 'Email me a sign-in link'}
        </button>
      </form>

      {sent && (
        <div className="rounded-xl border border-sage-200 bg-sage-50 px-4 py-3 text-sm text-sage-900">
          <p className="font-medium">Magic link sent.</p>
          <p className="mt-1 text-sage-700">Open it from your email to unlock chat, memory, history, and settings.</p>
          {devLink && (
            <a href={devLink} className="mt-3 block break-all text-xs font-medium text-sage-800 underline">
              Development link
            </a>
          )}
        </div>
      )}
    </div>
  )
}
