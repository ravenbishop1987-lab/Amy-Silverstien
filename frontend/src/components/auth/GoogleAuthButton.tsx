import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential?: string }) => void
          }) => void
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: 'outline' | 'filled_blue' | 'filled_black'
              size?: 'large' | 'medium' | 'small'
              type?: 'standard' | 'icon'
              shape?: 'rectangular' | 'pill' | 'circle' | 'square'
              text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
              width?: number
            },
          ) => void
        }
      }
    }
  }
}

const GOOGLE_SCRIPT_ID = 'google-identity-services'
const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

type Props = {
  mode: 'login' | 'signup'
}

function loadGoogleScript() {
  const existing = document.getElementById(GOOGLE_SCRIPT_ID)
  if (existing) return Promise.resolve()

  return new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.id = GOOGLE_SCRIPT_ID
    script.src = GOOGLE_SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Google login failed to load'))
    document.head.appendChild(script)
  })
}

export default function GoogleAuthButton({ mode }: Props) {
  const buttonRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

  useEffect(() => {
    if (!clientId || !buttonRef.current) return

    let cancelled = false

    loadGoogleScript()
      .then(() => {
        if (cancelled || !buttonRef.current || !window.google) return
        buttonRef.current.innerHTML = ''
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async ({ credential }) => {
            if (!credential) {
              toast.error('Google did not return a login token')
              return
            }

            setLoading(true)
            try {
              const { data } = await authApi.googleLogin(credential)
              setAuth(data.access_token, {
                user_id: data.user_id,
                email: data.email,
                subscription_tier: data.subscription_tier,
                created_at: new Date().toISOString(),
                profile: null,
              })
              toast.success(mode === 'signup' ? "Let's go! Amy's ready to chat." : 'Welcome back!')
              navigate('/chat')
            } catch (err: unknown) {
              const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
              toast.error(typeof msg === 'string' ? msg : 'Google login failed')
            } finally {
              setLoading(false)
            }
          },
        })
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          type: 'standard',
          shape: 'rectangular',
          text: mode === 'signup' ? 'signup_with' : 'continue_with',
          width: 320,
        })
      })
      .catch(() => toast.error('Google login failed to load'))

    return () => {
      cancelled = true
    }
  }, [clientId, mode, navigate, setAuth])

  if (!clientId) {
    return (
      <button type="button" disabled className="w-full rounded-lg border border-stone-200 px-4 py-2.5 text-sm text-stone-400">
        Google login unavailable
      </button>
    )
  }

  return (
    <div className="relative min-h-[44px]">
      <div ref={buttonRef} className={loading ? 'pointer-events-none opacity-60' : undefined} />
    </div>
  )
}
