import { useState } from 'react'
import { X, Check, Zap, Crown, MessageCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { stripeApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

interface Props {
  onClose: () => void
}

export default function PricingModal({ onClose }: Props) {
  const [loading, setLoading] = useState<string | null>(null)
  const { user } = useAuthStore()

  const handleSubscribe = async () => {
    setLoading('premium')
    try {
      const { data } = await stripeApi.subscribe()
      window.location.href = data.checkout_url
    } catch {
      toast.error('Could not open checkout. Try again!')
      setLoading(null)
    }
  }

  const handleSingleCredit = async () => {
    setLoading('single')
    try {
      const { data } = await stripeApi.buySingleCredits()
      window.location.href = data.checkout_url
    } catch {
      toast.error('Could not open checkout. Try again!')
      setLoading(null)
    }
  }

  const handleBulkCredits = async () => {
    setLoading('bulk')
    try {
      const { data } = await stripeApi.buyBulkCredits()
      window.location.href = data.checkout_url
    } catch {
      toast.error('Could not open checkout. Try again!')
      setLoading(null)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-3xl max-w-2xl w-full p-8 shadow-card animate-slide-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="font-serif text-2xl text-charcoal-900">Unlock more Amy</h2>
            <p className="text-stone-500 text-sm mt-1">Get unlimited conversations + Amy's actual voice</p>
          </div>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-600 p-1">
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          {/* Free */}
          <div className="border border-cream-300 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle size={18} className="text-stone-400" />
              <span className="font-medium text-stone-600">Free</span>
            </div>
            <p className="text-2xl font-serif text-charcoal-900 mb-1">$0</p>
            <p className="text-xs text-stone-400 mb-4">forever</p>
            <ul className="space-y-2 text-sm text-stone-600">
              {['3 conversations/day', 'Text only', 'Full memory bank', 'Basic advice'].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <Check size={13} className="text-stone-300 shrink-0" />{f}
                </li>
              ))}
            </ul>
            <div className="mt-4 text-center text-xs text-stone-400">Your current plan</div>
          </div>

          {/* Credits */}
          <div className="border border-sage-300 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={18} className="text-sage-500" />
              <span className="font-medium text-sage-700">Credits</span>
            </div>
            <div className="mb-4">
              <p className="text-lg font-serif text-charcoal-900">$0.99 <span className="text-sm font-sans text-stone-400">/convo</span></p>
              <p className="text-xs text-stone-400 mt-0.5">or $2.99 for 50</p>
            </div>
            <ul className="space-y-2 text-sm text-stone-600 mb-4">
              {['Unlimited text convos', "Amy's voice", 'Pay as you go', 'No commitment'].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <Check size={13} className="text-sage-400 shrink-0" />{f}
                </li>
              ))}
            </ul>
            <div className="space-y-2">
              <button
                onClick={handleSingleCredit}
                disabled={!!loading}
                className="w-full btn-secondary text-sm py-2"
              >
                {loading === 'single' ? 'Opening...' : 'Buy 1 ($0.99)'}
              </button>
              <button
                onClick={handleBulkCredits}
                disabled={!!loading}
                className="w-full btn-primary text-sm py-2"
              >
                {loading === 'bulk' ? 'Opening...' : 'Buy 50 ($2.99)'}
              </button>
            </div>
          </div>

          {/* Premium */}
          <div className="border-2 border-sage-400 rounded-2xl p-5 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-sage-400 text-white text-xs px-3 py-1 rounded-full font-medium">
              Best value
            </div>
            <div className="flex items-center gap-2 mb-3">
              <Crown size={18} className="text-sage-500" />
              <span className="font-medium text-sage-700">Premium</span>
            </div>
            <p className="text-2xl font-serif text-charcoal-900 mb-1">$9.99</p>
            <p className="text-xs text-stone-400 mb-4">per month</p>
            <ul className="space-y-2 text-sm text-stone-600 mb-4">
              {[
                'Unlimited everything',
                "Amy's voice on every message",
                'Export conversations (PDF)',
                'Memory bank analytics',
                'Priority response',
                'Cancel anytime',
              ].map((f) => (
                <li key={f} className="flex items-center gap-2">
                  <Check size={13} className="text-sage-500 shrink-0" />{f}
                </li>
              ))}
            </ul>
            <button
              onClick={handleSubscribe}
              disabled={!!loading || user?.subscription_tier === 'premium'}
              className="w-full btn-primary text-sm"
            >
              {loading === 'premium' ? 'Opening...' : user?.subscription_tier === 'premium' ? 'Current plan' : 'Get Premium'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
