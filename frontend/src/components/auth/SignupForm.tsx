import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

export default function SignupForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.register(email, password, name || undefined)
      setAuth(data.access_token, {
        user_id: data.user_id,
        email: data.email,
        subscription_tier: data.subscription_tier,
        created_at: new Date().toISOString(),
        profile: null,
      })
      navigate('/chat', { replace: true })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Could not create account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-charcoal-800 mb-1.5">
          Name <span className="text-stone-400 font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input-base"
          placeholder="What should Amy call you?"
          autoComplete="given-name"
        />
      </div>
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
      <div>
        <label className="block text-sm font-medium text-charcoal-800 mb-1.5">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="input-base"
          placeholder="••••••••"
          required
          minLength={8}
          autoComplete="new-password"
        />
      </div>
      <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
        {loading ? 'Creating account...' : 'Create account'}
      </button>
      <p className="text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link to="/login" className="text-sage-600 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  )
}
