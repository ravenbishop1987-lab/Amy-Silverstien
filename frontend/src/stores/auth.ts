import { create } from 'zustand'
import type { User, SubscriptionTier } from '@/types'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  setAuth: (token: string, user: User) => void
  updateUser: (user: Partial<User>) => void
  updateTier: (tier: SubscriptionTier) => void
  logout: () => void
  loadFromStorage: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isLoading: true,

  setAuth: (token, user) => {
    localStorage.setItem('token', token)
    localStorage.setItem('amy_user', JSON.stringify(user))
    set({ user, token, isLoading: false })
  },

  updateUser: (partial) => {
    const current = get().user
    if (!current) return
    const updated = { ...current, ...partial }
    localStorage.setItem('amy_user', JSON.stringify(updated))
    set({ user: updated })
  },

  updateTier: (tier) => {
    const current = get().user
    if (!current) return
    const updated = { ...current, subscription_tier: tier }
    localStorage.setItem('amy_user', JSON.stringify(updated))
    set({ user: updated })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('amy_user')
    set({ user: null, token: null })
  },

  loadFromStorage: () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('amy_user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as User
        set({ user, token, isLoading: false })
      } catch {
        set({ isLoading: false })
      }
    } else {
      set({ isLoading: false })
    }
  },
}))
