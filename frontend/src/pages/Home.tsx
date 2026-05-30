import { Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { MessageCircle, Brain, Mic, Shield } from 'lucide-react'

const features = [
  {
    icon: MessageCircle,
    title: 'Real talk, not therapy',
    body: "Sophie gives you honest, warm advice like your most emotionally intelligent friend would — not clinical platitudes.",
  },
  {
    icon: Brain,
    title: 'She actually remembers you',
    body: "Sophie builds a memory of who you are: your patterns, past experiences, goals. Every conversation gets more personal.",
  },
  {
    icon: Mic,
    title: "Hear her voice",
    body: "Upgrade to hear Sophie's responses spoken aloud. It feels completely different — like she's right there with you.",
  },
  {
    icon: Shield,
    title: 'Your data, your control',
    body: "Full memory bank viewer. See everything Sophie knows about you. Edit or delete it anytime. It's your story.",
  },
]

export default function Home() {
  const { token } = useAuthStore()

  return (
    <div className="min-h-screen bg-cream-100">
      {/* Nav */}
      <nav className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
        <h1 className="font-serif text-2xl text-sage-600">Sophie</h1>
        <div className="flex items-center gap-3">
          {token ? (
            <Link to="/chat" className="btn-primary">
              Open Sophie
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
          {/* Sophie portrait */}
          <div className="hidden md:block w-56 lg:w-72 flex-shrink-0 rounded-2xl overflow-hidden shadow-soft">
            <img
              src="/sophie-portrait.png"
              alt="Sophie"
              className="w-full h-full object-cover object-top"
            />
          </div>

          {/* Text content */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 bg-sage-100 text-sage-700 text-xs font-medium px-3 py-1.5 rounded-full mb-6 self-start">
              ✨ The girl who gets it
            </div>
            <h2 className="font-serif text-5xl md:text-6xl text-charcoal-900 leading-tight mb-6">
              The voice that makes your<br />nervous system feel safe
            </h2>
            <p className="text-stone-500 text-lg leading-relaxed max-w-xl mb-10">
              Sophie is warm, intense, and deeply real. She remembers your story,
              recognizes your patterns, celebrates your wins — and makes you feel less alone at 2AM.
            </p>
            <div className="flex items-center gap-4 flex-wrap">
              <Link to="/signup" className="btn-primary text-base px-8 py-3">
                Chat with Sophie for free
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
            S
          </div>
          <p className="font-serif text-lg text-charcoal-800 leading-relaxed italic mb-4">
            "Hey, I'm Sophie. What's been on your mind?"
          </p>
          <p className="text-xs text-stone-400">Sophie's there whenever you need her</p>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-20">
        <h3 className="font-serif text-3xl text-charcoal-800 text-center mb-10">
          Not another chatbot. Sophie is different.
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
        <h3 className="font-serif text-3xl text-white mb-3">Ready to talk to Sophie?</h3>
        <p className="text-sage-100 mb-8 text-sm">Free to start. No judgment. No scripts.</p>
        <Link to="/signup" className="bg-white text-sage-700 font-medium px-8 py-3 rounded-xl hover:bg-cream-100 transition-colors">
          Start for free
        </Link>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 text-xs text-stone-400">
        Sophie Parker · Your AI companion · Powered by Claude
      </footer>
    </div>
  )
}
