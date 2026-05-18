import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Crown, Zap, MessageCircle, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, stripeApi, embedApi } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import PricingModal from '@/components/subscription/PricingModal'
import type { AttachmentStyle, UserProfile, SubscriptionStatus } from '@/types'

export default function Settings() {
  const { user, updateUser, logout } = useAuthStore()
  const [showPricing, setShowPricing] = useState(false)
  const [embedDomain, setEmbedDomain] = useState('')

  const { data: subStatus } = useQuery<SubscriptionStatus>({
    queryKey: ['subscription'],
    queryFn: () => stripeApi.status().then((r) => r.data),
  })

  const { data: embeds, refetch: refetchEmbeds } = useQuery({
    queryKey: ['embeds'],
    queryFn: () => embedApi.list().then((r) => r.data),
  })

  const profileMutation = useMutation({
    mutationFn: (data: Partial<UserProfile>) => authApi.updateProfile(data),
    onSuccess: (res) => {
      updateUser({ profile: res.data })
      toast.success('Profile updated!')
    },
    onError: () => toast.error('Could not save profile'),
  })

  const cancelMutation = useMutation({
    mutationFn: () => stripeApi.cancelSubscription(),
    onSuccess: () => toast.success('Subscription canceled. You keep access until the end of the period.'),
    onError: () => toast.error('Could not cancel subscription'),
  })

  const createEmbed = useMutation({
    mutationFn: () => embedApi.create(embedDomain),
    onSuccess: () => { toast.success('Embed created!'); setEmbedDomain(''); refetchEmbeds() },
    onError: () => toast.error('Could not create embed'),
  })

  const [profileForm, setProfileForm] = useState({
    preferred_name: user?.profile?.preferred_name || '',
    age: user?.profile?.age || '',
    relationship_status: user?.profile?.relationship_status || '',
    pronouns: user?.profile?.pronouns || '',
    attachment_style: user?.profile?.attachment_style || 'unknown',
    adhd_severity: user?.profile?.adhd_severity || '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('subscription') === 'success') {
      toast.success('Welcome to Premium! 🎉')
      window.history.replaceState({}, '', '/settings')
    }
    if (params.get('credits') === 'success') {
      toast.success('Credits added! 🎉')
      window.history.replaceState({}, '', '/settings')
    }
  }, [])

  const TIER_CONFIG = {
    free: { icon: MessageCircle, label: 'Free', color: 'text-stone-500' },
    credits: { icon: Zap, label: 'Credits', color: 'text-sage-600' },
    premium: { icon: Crown, label: 'Premium', color: 'text-sage-600' },
  }
  const tierCfg = TIER_CONFIG[user?.subscription_tier || 'free']

  return (
    <div className="h-screen overflow-y-auto bg-cream-100 px-8 py-8">
      <div className="max-w-xl mx-auto space-y-6">
        <h1 className="font-serif text-2xl text-charcoal-900">Settings</h1>

        {/* Subscription */}
        <div className="card">
          <h2 className="font-medium text-charcoal-800 mb-4">Subscription</h2>
          <div className="flex items-center gap-3 mb-4 p-3 bg-cream-100 rounded-xl">
            <tierCfg.icon size={18} className={tierCfg.color} />
            <div className="flex-1">
              <p className="font-medium text-charcoal-800 capitalize">{tierCfg.label}</p>
              {subStatus && (
                <p className="text-xs text-stone-400">
                  {user?.subscription_tier === 'free'
                    ? `${subStatus.text_conversations_remaining} text convos remaining today`
                    : user?.subscription_tier === 'credits'
                    ? `${subStatus.voice_conversations_remaining} voice conversations remaining`
                    : 'Unlimited conversations'}
                </p>
              )}
            </div>
            {user?.subscription_tier !== 'premium' && (
              <button onClick={() => setShowPricing(true)} className="btn-primary text-sm px-4 py-2">
                Upgrade
              </button>
            )}
          </div>
          {user?.subscription_tier === 'premium' && (
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="text-xs text-stone-400 hover:text-blush-400 transition-colors"
            >
              Cancel subscription
            </button>
          )}
        </div>

        {/* Profile */}
        <div className="card">
          <h2 className="font-medium text-charcoal-800 mb-4">Your profile</h2>
          <p className="text-xs text-stone-400 mb-4">This helps Amy give you more personalized advice.</p>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">Preferred name</label>
                <input
                  value={profileForm.preferred_name}
                  onChange={(e) => setProfileForm({ ...profileForm, preferred_name: e.target.value })}
                  className="input-base text-sm"
                  placeholder="What should Amy call you?"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">Age</label>
                <input
                  type="number"
                  value={profileForm.age}
                  onChange={(e) => setProfileForm({ ...profileForm, age: e.target.value })}
                  className="input-base text-sm"
                  placeholder="Age"
                  min={13}
                  max={120}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">Pronouns</label>
                <input
                  value={profileForm.pronouns}
                  onChange={(e) => setProfileForm({ ...profileForm, pronouns: e.target.value })}
                  className="input-base text-sm"
                  placeholder="she/her, they/them..."
                />
              </div>
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">Relationship status</label>
                <input
                  value={profileForm.relationship_status}
                  onChange={(e) => setProfileForm({ ...profileForm, relationship_status: e.target.value })}
                  className="input-base text-sm"
                  placeholder="Single, dating..."
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">Attachment style</label>
                <select
                  value={profileForm.attachment_style}
                  onChange={(e) => setProfileForm({ ...profileForm, attachment_style: e.target.value as AttachmentStyle })}
                  className="input-base text-sm"
                >
                  <option value="unknown">Not sure</option>
                  <option value="secure">Secure</option>
                  <option value="anxious">Anxious</option>
                  <option value="avoidant">Avoidant</option>
                  <option value="fearful">Fearful-avoidant</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-stone-500 mb-1 block">ADHD severity (1-10)</label>
                <input
                  type="number"
                  value={profileForm.adhd_severity}
                  onChange={(e) => setProfileForm({ ...profileForm, adhd_severity: e.target.value })}
                  className="input-base text-sm"
                  placeholder="1-10"
                  min={1}
                  max={10}
                />
              </div>
            </div>
            <button
              onClick={() => profileMutation.mutate({
                preferred_name: profileForm.preferred_name || undefined,
                age: profileForm.age ? parseInt(profileForm.age as string) : undefined,
                relationship_status: profileForm.relationship_status || undefined,
                pronouns: profileForm.pronouns || undefined,
                attachment_style: profileForm.attachment_style as UserProfile['attachment_style'],
                adhd_severity: profileForm.adhd_severity ? parseInt(profileForm.adhd_severity as string) : undefined,
                timezone: profileForm.timezone,
              })}
              disabled={profileMutation.isPending}
              className="btn-primary w-full mt-2"
            >
              {profileMutation.isPending ? 'Saving...' : 'Save profile'}
            </button>
          </div>
        </div>

        {/* Widget Embedding */}
        <div className="card">
          <h2 className="font-medium text-charcoal-800 mb-1">Embed on your website</h2>
          <p className="text-xs text-stone-400 mb-4">Add Amy as a chat widget to any site.</p>
          <div className="flex gap-2">
            <input
              value={embedDomain}
              onChange={(e) => setEmbedDomain(e.target.value)}
              placeholder="yourdomain.com"
              className="input-base text-sm flex-1"
            />
            <button
              onClick={() => createEmbed.mutate()}
              disabled={!embedDomain.trim() || createEmbed.isPending}
              className="btn-primary text-sm px-4 shrink-0"
            >
              Create
            </button>
          </div>
          {embeds && embeds.length > 0 && (
            <div className="mt-4 space-y-2">
              {embeds.map((e: { embed_id: string; website_domain: string; script_tag: string }) => (
                <div key={e.embed_id} className="bg-cream-100 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-charcoal-800">{e.website_domain}</span>
                    <ExternalLink size={13} className="text-stone-400" />
                  </div>
                  <code className="text-xs bg-charcoal-800 text-sage-300 px-3 py-2 rounded-lg block overflow-x-auto">
                    {e.script_tag}
                  </code>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Account */}
        <div className="card">
          <h2 className="font-medium text-charcoal-800 mb-4">Account</h2>
          <p className="text-sm text-stone-500 mb-4">{user?.email}</p>
          <button onClick={logout} className="text-sm text-stone-400 hover:text-blush-400 transition-colors">
            Sign out
          </button>
        </div>
      </div>

      {showPricing && <PricingModal onClose={() => setShowPricing(false)} />}
    </div>
  )
}
