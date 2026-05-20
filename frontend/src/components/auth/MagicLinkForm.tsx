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
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

  const requestSupabaseMagicLink = async (normalizedEmail: string) => {
    if (!supabaseUrl || !supabaseAnonKey) return false

    const redirectTo = `${window.location.origin}/magic-login`
    const response = await fetch(
      `${supabaseUrl.replace(/\/$/, '')}/auth/v1/otp?redirect_to=${encodeURIComponent(redirectTo)}`,
      {
        method: 'POST',
        headers: {
          apikey: supabaseAnonKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: normalizedEmail,
          create_user: true,
        }),
      },
    )

    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || 'Supabase could not send the magic link')
    }

    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setDevLink(null)
    try {
      const normalizedEmail = email.trim().toLowerCase()
      const sentBySupabase = await requestSupabaseMagicLink(normalizedEmail)
      const { data } = sentBySupabase
        ? { data: { detail: 'Check your email for your sign-in link' } }
        : await authApi.requestMagicLink(normalizedEmail)
      setSent(true)
      if (data.magic_link) setDevLink(data.magic_link)
      toast.success('Check your email for your sign-in link')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      const fallback = err instanceof Error ? err.message : 'Could not send sign-in link'
      toast.error(typeof msg === 'string' ? msg : fallback)
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
