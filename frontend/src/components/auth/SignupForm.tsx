import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types'

export default function SignupForm() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      const { data } = await authApi.register(email, password, name || undefined)
      localStorage.setItem('amy_token', data.access_token)
      const meRes = await authApi.me()
      setAuth(data.access_token, meRes.data as User)
      toast.success("Let's go! Amy's ready to chat.")
      navigate('/chat')
    } catch (err: unknown) {
      localStorage.removeItem('amy_token')
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Could not create account. Try again!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-charcoal-800 mb-1.5">
          First name <span className="text-stone-400 font-normal">(optional)</span>
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
        <div className="relative">
          <input
            type={showPw ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-base pr-12"
            placeholder="At least 8 characters"
            required
            autoComplete="new-password"
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
        {loading ? 'Creating account...' : 'Start chatting with Amy'}
      </button>
      <p className="text-center text-xs text-stone-400">
        Free tier: 3 conversations/day. Upgrade anytime for unlimited + voice.
      </p>
      <p className="text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link to="/login" className="text-sage-600 hover:text-sage-700 font-medium">
          Sign in
        </Link>
      </p>
    </form>
  )
}
