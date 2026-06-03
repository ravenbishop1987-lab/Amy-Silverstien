import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

export default function MagicLogin() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'checking' | 'failed'>('checking')
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const supabaseAccessToken = hashParams.get('access_token')
    if (supabaseAccessToken) {
      authApi.loginWithSupabaseSession(supabaseAccessToken)
        .then(({ data }) => {
          setAuth(data.access_token, {
            user_id: data.user_id,
            email: data.email,
            subscription_tier: data.subscription_tier,
            created_at: new Date().toISOString(),
            profile: null,
          })
          toast.success('Signed in')
          navigate('/chat', { replace: true })
        })
        .catch((err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          toast.error(typeof msg === 'string' ? msg : 'That Supabase sign-in link did not work')
          setStatus('failed')
        })
      return
    }

    const token = searchParams.get('token')
    if (!token) {
      setStatus('failed')
      return
    }

    authApi.verifyMagicLink(token)
      .then(({ data }) => {
        setAuth(data.access_token, {
          user_id: data.user_id,
          email: data.email,
          subscription_tier: data.subscription_tier,
          created_at: new Date().toISOString(),
          profile: null,
        })
        toast.success('Signed in')
        navigate('/chat', { replace: true })
      })
      .catch((err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        toast.error(typeof msg === 'string' ? msg : 'That sign-in link did not work')
        setStatus('failed')
      })
  }, [navigate, searchParams, setAuth])

  return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm text-center">
        <Link to="/">
          <h1 className="font-serif text-3xl text-sage-600 mb-1">Amy</h1>
        </Link>
        <div className="card mt-8">
          {status === 'checking' ? (
            <div className="py-6">
              <div className="typing-dots justify-center">
                <span /><span /><span />
              </div>
              <p className="mt-4 text-sm text-stone-500">Signing you in...</p>
            </div>
          ) : (
            <div className="py-4">
              <p className="font-medium text-charcoal-900">This sign-in link is invalid or expired.</p>
              <Link to="/chat" className="btn-primary mt-5 inline-flex">
                Get a new link
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
