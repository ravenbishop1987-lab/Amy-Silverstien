import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

export default function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      setAuth(data.access_token, {
        user_id: data.user_id,
        email: data.email,
        subscription_tier: data.subscription_tier,
        created_at: new Date().toISOString(),
        profile: null,
      })
      toast.success('Welcome back!')
      navigate('/chat')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
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
      <div>
        <label className="block text-sm font-medium text-charcoal-800 mb-1.5">Password</label>
        <div className="relative">
          <input
            type={showPw ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-base pr-12"
            placeholder="••••••••"
            required
            autoComplete="current-password"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
          >
            {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>
      <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
        {loading ? 'Signing in...' : 'Sign in'}
      </button>
      <p className="text-center text-sm text-stone-500">
        Don't have an account?{' '}
        <Link to="/signup" className="text-sage-600 hover:text-sage-700 font-medium">
          Sign up free
        </Link>
      </p>
    </form>
  )
}
