import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      const onAuthPage = ['/login', '/signup', '/magic-login'].includes(window.location.pathname)
      if (!onAuthPage) {
        localStorage.removeItem('token')
        localStorage.removeItem('amy_user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  register: (email: string, password: string, preferred_name?: string) =>
    api.post('/auth/register', { email, password, preferred_name }),
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  googleLogin: (credential: string) =>
    api.post('/auth/google', { credential }),
  requestMagicLink: (email: string) =>
    api.post('/auth/magic-link', { email }),
  verifyMagicLink: (token: string) =>
    api.post('/auth/magic-link/verify', { token }),
  me: () => api.get('/auth/me'),
  updateProfile: (data: Record<string, unknown>) => api.put('/auth/profile', data),
  deleteAccount: () => api.delete('/auth/account'),
}

// Conversations
export const conversationsApi = {
  list: (skip = 0, limit = 20) =>
    api.get('/conversations', { params: { skip, limit } }),
  get: (id: string) => api.get(`/conversations/${id}`),
  create: (data: { title?: string; user_mood_before?: number }) =>
    api.post('/conversations', data),
  updateMood: (id: string, mood_after: number) =>
    api.patch(`/conversations/${id}/mood`, { mood_after }),
  delete: (id: string) => api.delete(`/conversations/${id}`),
}

// Memory
export const memoryApi = {
  getBank: () => api.get('/memory'),
  createLifeEvent: (data: Record<string, unknown>) => api.post('/memory/events', data),
  updateLifeEvent: (id: string, data: Record<string, unknown>) => api.put(`/memory/events/${id}`, data),
  deleteLifeEvent: (id: string) => api.delete(`/memory/events/${id}`),
  createPattern: (data: Record<string, unknown>) => api.post('/memory/patterns', data),
  deletePattern: (id: string) => api.delete(`/memory/patterns/${id}`),
  createGoal: (data: Record<string, unknown>) => api.post('/memory/goals', data),
  achieveGoal: (id: string) => api.patch(`/memory/goals/${id}/achieve`),
  deleteGoal: (id: string) => api.delete(`/memory/goals/${id}`),
  createSensitivity: (data: Record<string, unknown>) => api.post('/memory/sensitivities', data),
  deleteSensitivity: (id: string) => api.delete(`/memory/sensitivities/${id}`),
  deleteExtract: (id: string) => api.delete(`/memory/extracts/${id}`),
}

// Voice
export const voiceApi = {
  synthesize: async (text: string): Promise<ArrayBuffer> => {
    const res = await api.post('/voice/synthesize', { text, stream: false }, { responseType: 'arraybuffer' })
    return res.data
  },
  transcribe: async (blob: Blob): Promise<string> => {
    const form = new FormData()
    form.append('audio', blob, 'audio.webm')
    const res = await api.post('/voice/transcribe', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data.text
  },
  enrollVoice: async (blob: Blob) => {
    const form = new FormData()
    form.append('audio', blob, 'enroll.webm')
    return api.post('/voice/enroll', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  verifyVoice: async (blob: Blob) => {
    const form = new FormData()
    form.append('audio', blob, 'verify.webm')
    return api.post<{ verified: boolean; similarity: number; enrolled_at: string }>(
      '/voice/verify', form, { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },
  deleteEnrollment: () => api.delete('/voice/enroll'),
}

// Stripe
export const stripeApi = {
  subscribe: () => api.post('/stripe/subscribe'),
  buySingleCredits: () => api.post('/stripe/credits/single'),
  buyBulkCredits: () => api.post('/stripe/credits/bulk'),
  buyGift: (data: { gift_type: string; personal_message: string; conversation_id?: string | null }) =>
    api.post('/stripe/gifts/checkout', data),
  confirmGift: (sessionId: string) => api.post('/stripe/gifts/confirm', { session_id: sessionId }),
  cancelSubscription: () => api.delete('/stripe/subscription'),
  status: () => api.get('/stripe/status'),
}

// Embed
export const embedApi = {
  create: (domain: string, config?: Record<string, unknown>) =>
    api.post('/embed/create', { website_domain: domain, widget_config: config }),
  list: () => api.get('/embed/list'),
}
