import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { referralApi } from '@/lib/api'

const VIDEO_MAP: Record<string, string> = {
  'let-me-stay-with-you': 'Let Me Stay With You Tonight 💤 ADHD Sleep Talk',
  'when-adhd-brain-wont-shut-up': "When Your ADHD Brain Won't Shut Up 🧠 Sleep...",
  'anxious-attachment-2am': 'Anxious Attachment & The 2AM Overthrinking Loop',
  'nervous-system-rest': 'Let Your Nervous System Rest 💚 ADHD Sleep...',
  'fall-asleep-adhd-girl': 'Fall Asleep With An ADHD Girl Who Actually Gets...',
  'fall-asleep-sophie-ep8': 'Sleeping With Sophie Ep. 8 | Let Your ADHD Brain...',
  'ill-be-here-when-you-wake-up': "I'll Be Here When You Wake Up 💤 ADHD Guided...",
  'stay-with-me-tonight': 'Stay With Me Tonight ❤️ ADHD Sleep Talk Down...',
  'sleep-with-sophie-ep4': 'Sleep With Sophie Ep 4 💤 Fall Asleep Beside Me...',
  'come-lay-next-to-me': 'Come Lay Next To Me | Sleeping With Sophie Ep...',
  'adhd-girl-who-gets-it': 'Fall Asleep With An ADHD Girl Who Actually Gets...',
  'late-night-comfort-talks': 'Late Night Comfort Talks 💭 For Overthinkers &...',
  'rainy-night-conversations': 'Rainy Night Conversations for ADHD Overthinker...',
  'adhd-relationships-intense': 'ADHD Relationships Feel Intense When Someone...',
  "i-dont-care-bad-sleep": "I Don't Care If You Didn't Sleep Well Last Night...",
}

export function getStoredReferral(): { slug: string; title: string } | null {
  try {
    const raw = localStorage.getItem('referral')
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearStoredReferral() {
  localStorage.removeItem('referral')
}

export default function YouTubeReferral() {
  const { slug = '' } = useParams<{ slug: string }>()
  const navigate = useNavigate()

  useEffect(() => {
    const videoTitle = VIDEO_MAP[slug] ?? null

    // Store referral in localStorage (last-click attribution)
    if (videoTitle) {
      localStorage.setItem('referral', JSON.stringify({ slug, title: videoTitle }))
    }

    // Fire-and-forget click log — never block the redirect on this
    referralApi.logClick(slug, videoTitle ?? undefined, document.referrer || undefined).catch(() => {})

    // Redirect immediately
    navigate('/', { replace: true })
  }, [slug, navigate])

  return (
    <div className="min-h-screen bg-cream-100 flex items-center justify-center">
      <div className="typing-dots">
        <span /><span /><span />
      </div>
    </div>
  )
}
