import { Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { MessageCircle, Brain, Mic, Shield } from 'lucide-react'

const features = [
  {
    icon: MessageCircle,
    title: 'Real talk, not therapy',
    body: "Amy gives you honest, warm advice like your most emotionally intelligent friend would — not clinical platitudes.",
  },
  {
    icon: Brain,
    title: 'She actually remembers you',
    body: "Amy builds a memory of who you are: your patterns, past experiences, goals. Every conversation gets more personal.",
  },
  {
    icon: Mic,
    title: "Hear her voice",
    body: "Upgrade to hear Amy's responses spoken aloud. It feels completely different — like she's right there with you.",
  },
  {
    icon: Shield,
    title: 'Your data, your control',
    body: "Full memory bank viewer. See everything Amy knows about you. Edit or delete it anytime. It's your story.",
  },
]

export default function Home() {
  const { token } = useAuthStore()

  return (
    <div className="min-h-screen bg-cream-100">
      {/* Nav */}
      <nav className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
        <h1 className="font-serif text-2xl text-sage-600">Amy</h1>
        <div className="flex items-center gap-3">
          {token ? (
            <Link to="/chat" className="btn-primary">
              Open Amy
            </Link>
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
          {/* Amy portrait */}
          <div className="hidden md:block w-56 lg:w-72 flex-shrink-0 rounded-2xl overflow-hidden shadow-soft">
            <img
              src="/amy-portrait.png"
              alt="Amy"
              className="w-full h-full object-cover object-top"
            />
          </div>

          {/* Text content */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 bg-sage-100 text-sage-700 text-xs font-medium px-3 py-1.5 rounded-full mb-6 self-start">
              ✨ AI dating advice that actually gets it
            </div>
            <h2 className="font-serif text-5xl md:text-6xl text-charcoal-900 leading-tight mb-6">
              The advice you wish<br />your best friend had
            </h2>
            <p className="text-stone-500 text-lg leading-relaxed max-w-xl mb-10">
              Amy is your AI companion for dating and relationships. She remembers your story,
              recognizes your patterns, celebrates your wins — and gives you real advice, not platitudes.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link to="/signup" className="btn-primary text-base px-8 py-3">
                Chat with Amy for free
              </Link>
              <p className="text-xs text-stone-400">3 free conversations/day. No credit card.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section className="max-w-2xl mx-auto px-6 pb-16 text-center">
        <div className="bg-white rounded-3xl p-8 shadow-soft">
          <div className="w-12 h-12 rounded-full bg-sage-400 flex items-center justify-center text-white font-semibold text-lg mx-auto mb-4">
            A
          </div>
          <p className="font-serif text-lg text-charcoal-800 leading-relaxed italic mb-4">
            "Hey, I'm Amy. What's on your mind about dating or relationships?"
          </p>
          <p className="text-xs text-stone-400">Amy's there whenever you need her</p>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <h3 className="font-serif text-3xl text-charcoal-800 text-center mb-10">
          Not another chatbot.
        </h3>
        <div className="grid md:grid-cols-2 gap-6">
          {features.map(({ icon: Icon, title, body }) => (
            <div key={title} className="card">
              <div className="w-10 h-10 bg-sage-100 rounded-xl flex items-center justify-center mb-4">
                <Icon size={20} className="text-sage-600" />
              </div>
              <h4 className="font-medium text-charcoal-800 mb-2">{title}</h4>
              <p className="text-stone-500 text-sm leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-sage-400 py-16 text-center">
        <h3 className="font-serif text-3xl text-white mb-3">Ready to talk to Amy?</h3>
        <p className="text-sage-100 mb-8 text-sm">Free to start. No judgment. No scripts.</p>
        <Link to="/signup" className="bg-white text-sage-700 font-medium px-8 py-3 rounded-xl hover:bg-cream-100 transition-colors">
          Start for free
        </Link>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 text-xs text-stone-400">
        Amy · Your AI dating companion · Powered by Claude
      </footer>
    </div>
  )
}
