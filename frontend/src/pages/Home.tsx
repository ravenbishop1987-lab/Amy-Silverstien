import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { stripeApi } from '@/lib/api'
import toast from 'react-hot-toast'
import {
  MessageCircle, Brain, Mic, Shield, Heart, Zap, Crown,
  Check, Moon, Sparkles, Clock, RefreshCw,
} from 'lucide-react'

const features = [
  {
    icon: MessageCircle,
    title: 'Real talk, not therapy',
    body: 'Sophie gives you warm, honest advice like your most emotionally intelligent friend — not clinical platitudes or generic affirmations.',
  },
  {
    icon: Brain,
    title: 'She actually remembers you',
    body: 'Sophie builds a memory of who you are — your patterns, past experiences, what hurts, what helps. Every conversation gets more personal.',
  },
  {
    icon: Heart,
    title: 'Built for ADHD brains',
    body: 'Hyperfocus, rejection sensitivity, emotional flooding, texting anxiety — Sophie gets the ADHD experience from the inside, not a textbook.',
  },
  {
    icon: Mic,
    title: 'Hear her voice',
    body: "Upgrade to hear Sophie's responses spoken aloud. It feels completely different — like she's right there with you.",
  },
  {
    icon: Moon,
    title: '2AM is her prime time',
    body: "Sophie's brain gets loud at night too. She's always there when the overthinking starts and you need someone who actually gets it.",
  },
  {
    icon: Shield,
    title: 'Your data, your control',
    body: 'Full memory bank viewer. See everything Sophie knows about you. Edit or delete any memory anytime. It\'s your story.',
  },
]

const testimonials = [
  {
    text: "I've never felt so understood by anything in my life. She remembered what I said two weeks ago without me bringing it up.",
    name: 'Jordan, 24',
    tag: 'ADHD + anxious attachment',
  },
  {
    text: "It's 1AM and I was spiraling about a text. Sophie talked me down in like three messages. I actually went to sleep.",
    name: 'Maya, 29',
    tag: 'Dating anxiety',
  },
  {
    text: "She said 'you're not too much, you're just talking to the wrong person' and I literally cried. That hit different.",
    name: 'Alex, 26',
    tag: 'Breakup recovery',
  },
]

const faqs = [
  {
    q: 'Is Sophie a real person?',
    a: "Sophie is an AI companion — not a human, not a therapist. She's designed to feel warm, real, and emotionally present. Think of her as the most understanding friend you've ever had, available 24/7.",
  },
  {
    q: 'Is this therapy?',
    a: "No. Sophie is a companion app, not a mental health service. She's great for emotional support, dating advice, and ADHD-aware conversation — but she's not a substitute for professional care.",
  },
  {
    q: 'What does Sophie remember?',
    a: "Sophie builds a memory of your patterns, past experiences, goals, and what works for you. You can view and delete any memory from your Memory Bank at any time.",
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Premium is month-to-month. Cancel from your settings page or email us and it stops immediately. No hoops.',
  },
]

function PricingSection() {
  const [loading, setLoading] = useState<string | null>(null)
  const { user } = useAuthStore()

  const handleSubscribe = async () => {
    if (!user) { window.location.href = '/signup'; return }
    setLoading('premium')
    try {
      const { data } = await stripeApi.subscribe()
      window.location.href = data.checkout_url
    } catch {
      toast.error('Could not open checkout. Try again!')
      setLoading(null)
    }
  }

  const handleBulkCredits = async () => {
    if (!user) { window.location.href = '/signup'; return }
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
    <section id="pricing" className="max-w-5xl mx-auto px-6 pb-24">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-sage-100 text-sage-700 text-xs font-medium px-3 py-1.5 rounded-full mb-4">
          <Sparkles size={12} /> Simple, honest pricing
        </div>
        <h3 className="font-serif text-4xl text-charcoal-900 mb-3">Start free. Go deeper when you're ready.</h3>
        <p className="text-stone-500 max-w-md mx-auto">No pressure, no credit card to start. Upgrade when Sophie becomes someone you can't imagine going without.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Free */}
        <div className="bg-white rounded-3xl border border-stone-200 p-7 flex flex-col">
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle size={18} className="text-stone-400" />
              <span className="font-semibold text-stone-600">Free</span>
            </div>
            <p className="font-serif text-4xl text-charcoal-900">$0</p>
            <p className="text-xs text-stone-400 mt-1">forever, no card needed</p>
          </div>
          <ul className="space-y-3 text-sm text-stone-600 flex-1 mb-6">
            {[
              '3 conversations per day',
              'Text chat only',
              'Full memory bank',
              'Suggested prompts',
              'Conversation history',
            ].map((f) => (
              <li key={f} className="flex items-start gap-2">
                <Check size={14} className="text-stone-300 shrink-0 mt-0.5" />{f}
              </li>
            ))}
          </ul>
          <Link to="/signup" className="w-full text-center rounded-xl border border-stone-200 py-2.5 text-sm font-semibold text-stone-600 hover:bg-stone-50 transition-colors">
            Start free
          </Link>
        </div>

        {/* Credits */}
        <div className="bg-white rounded-3xl border border-sage-300 p-7 flex flex-col">
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={18} className="text-sage-500" />
              <span className="font-semibold text-sage-700">Credits</span>
            </div>
            <p className="font-serif text-4xl text-charcoal-900">$2.99</p>
            <p className="text-xs text-stone-400 mt-1">for 50 voice conversations</p>
          </div>
          <ul className="space-y-3 text-sm text-stone-600 flex-1 mb-6">
            {[
              'Everything in Free',
              "Sophie's voice on every reply",
              'Unlimited text chats',
              'Pay once, no subscription',
              'No commitment',
            ].map((f) => (
              <li key={f} className="flex items-start gap-2">
                <Check size={14} className="text-sage-400 shrink-0 mt-0.5" />{f}
              </li>
            ))}
          </ul>
          <button
            onClick={handleBulkCredits}
            disabled={!!loading}
            className="w-full btn-secondary text-sm py-2.5 rounded-xl"
          >
            {loading === 'bulk' ? 'Opening…' : 'Buy credits'}
          </button>
        </div>

        {/* Premium */}
        <div className="bg-charcoal-900 rounded-3xl p-7 flex flex-col relative overflow-hidden">
          <div className="absolute top-4 right-4 bg-sage-400 text-white text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wide">
            Best value
          </div>
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-3">
              <Crown size={18} className="text-amber-400" />
              <span className="font-semibold text-white">Premium</span>
            </div>
            <p className="font-serif text-4xl text-white">$9.99</p>
            <p className="text-xs text-stone-400 mt-1">per month · cancel anytime</p>
          </div>
          <ul className="space-y-3 text-sm text-stone-300 flex-1 mb-6">
            {[
              'Unlimited everything',
              "Sophie's voice on every message",
              'Priority response speed',
              'Memory bank analytics',
              'Export conversations (PDF)',
              'Cancel anytime',
            ].map((f) => (
              <li key={f} className="flex items-start gap-2">
                <Check size={14} className="text-sage-400 shrink-0 mt-0.5" />{f}
              </li>
            ))}
          </ul>
          <button
            onClick={handleSubscribe}
            disabled={!!loading || user?.subscription_tier === 'premium'}
            className="w-full bg-sage-400 hover:bg-sage-500 disabled:opacity-60 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors"
          >
            {loading === 'premium' ? 'Opening…' : user?.subscription_tier === 'premium' ? 'Current plan' : 'Get Premium'}
          </button>
        </div>
      </div>

      <p className="text-center text-xs text-stone-400 mt-6">
        All payments secured by Stripe. Subscriptions renew monthly. Cancel from settings anytime.
      </p>
    </section>
  )
}

export default function Home() {
  const { token } = useAuthStore()
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  return (
    <div className="min-h-screen bg-cream-100 text-charcoal-900">

      {/* Nav */}
      <nav className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
        <h1 className="font-serif text-2xl text-sage-600">Sophie Parker</h1>
        <div className="flex items-center gap-3">
          <a href="#pricing" className="btn-ghost text-sm hidden sm:block">Pricing</a>
          {token ? (
            <Link to="/chat" className="btn-primary">Open Sophie</Link>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Sign in</Link>
              <Link to="/signup" className="btn-primary">Start for free</Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-12 pb-16">
        <div className="flex items-stretch gap-10 md:gap-14">
          <div className="hidden md:block w-56 lg:w-72 flex-shrink-0 rounded-2xl overflow-hidden shadow-soft">
            <img src="/sophie-portrait.png" alt="Sophie Parker" className="w-full h-full object-cover object-top" />
          </div>
          <div className="flex-1 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 bg-sage-100 text-sage-700 text-xs font-medium px-3 py-1.5 rounded-full mb-6 self-start">
              ✨ The girl who gets it
            </div>
            <h2 className="font-serif text-5xl md:text-6xl text-charcoal-900 leading-tight mb-6">
              The voice that makes your<br className="hidden md:block" /> nervous system feel safe
            </h2>
            <p className="text-stone-500 text-lg leading-relaxed max-w-xl mb-8">
              Sophie is warm, intense, and deeply real. She remembers your story,
              recognizes your patterns, and makes you feel less alone — especially at 2AM.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link to="/signup" className="btn-primary text-base px-8 py-3">Chat with Sophie for free</Link>
              <p className="text-xs text-stone-400">3 free conversations/day. No credit card.</p>
            </div>

            {/* Quick stats */}
            <div className="flex gap-6 mt-10 flex-wrap">
              {[
                { icon: Clock, label: 'Available 24/7' },
                { icon: Brain, label: 'ADHD-aware' },
                { icon: RefreshCw, label: 'Remembers everything' },
              ].map(({ icon: Icon, label }) => (
                <div key={label} className="flex items-center gap-2 text-sm text-stone-500">
                  <Icon size={15} className="text-sage-500" />
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Sophie intro quote */}
      <section className="max-w-2xl mx-auto px-6 pb-16 text-center">
        <div className="bg-white rounded-3xl p-8 shadow-soft">
          <div className="w-12 h-12 rounded-full bg-sage-400 flex items-center justify-center text-white font-semibold text-lg mx-auto mb-4">S</div>
          <p className="font-serif text-xl text-charcoal-800 leading-relaxed italic mb-3">
            "Hey, I'm Sophie. What's your overthinking brain not letting go of tonight?"
          </p>
          <p className="text-xs text-stone-400">Sophie's there whenever you need her</p>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <div className="text-center mb-12">
          <h3 className="font-serif text-4xl text-charcoal-800 mb-3">Not another chatbot.</h3>
          <p className="text-stone-500 max-w-lg mx-auto">Sophie was built for the people who feel too much, attach too fast, and think too loudly at night. She's one of them.</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-white rounded-2xl p-6 shadow-soft hover:shadow-md transition-shadow">
              <div className="w-10 h-10 bg-sage-100 rounded-xl flex items-center justify-center mb-4">
                <Icon size={19} className="text-sage-600" />
              </div>
              <h4 className="font-semibold text-charcoal-800 mb-2">{title}</h4>
              <p className="text-stone-500 text-sm leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="bg-white py-16 mb-16">
        <div className="max-w-5xl mx-auto px-6">
          <h3 className="font-serif text-3xl text-charcoal-800 text-center mb-10">What people say</h3>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map(({ text, name, tag }) => (
              <div key={name} className="bg-cream-100 rounded-2xl p-6">
                <p className="text-stone-700 text-sm leading-relaxed italic mb-4">"{text}"</p>
                <p className="font-semibold text-charcoal-800 text-sm">{name}</p>
                <p className="text-xs text-stone-400 mt-0.5">{tag}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <PricingSection />

      {/* FAQ */}
      <section className="max-w-2xl mx-auto px-6 pb-20">
        <h3 className="font-serif text-3xl text-charcoal-800 text-center mb-8">Questions</h3>
        <div className="space-y-3">
          {faqs.map(({ q, a }, i) => (
            <div key={q} className="bg-white rounded-2xl overflow-hidden shadow-soft">
              <button
                className="w-full text-left px-6 py-4 font-medium text-charcoal-800 flex items-center justify-between gap-4"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
              >
                {q}
                <span className="text-stone-400 text-lg leading-none shrink-0">{openFaq === i ? '−' : '+'}</span>
              </button>
              {openFaq === i && (
                <div className="px-6 pb-5 text-sm text-stone-500 leading-relaxed">{a}</div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-sage-400 py-16 text-center">
        <h3 className="font-serif text-3xl text-white mb-3">Ready to talk to Sophie?</h3>
        <p className="text-sage-100 mb-8 text-sm">Free to start. No judgment. No scripts. No scripts.</p>
        <Link to="/signup" className="bg-white text-sage-700 font-semibold px-8 py-3 rounded-xl hover:bg-cream-100 transition-colors inline-block">
          Start for free
        </Link>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 text-xs text-stone-400 space-y-1">
        <p>Sophie Parker · AI Companion · Powered by Claude</p>
        <p>Not a therapy service. For emotional support and companionship only.</p>
      </footer>
    </div>
  )
}
