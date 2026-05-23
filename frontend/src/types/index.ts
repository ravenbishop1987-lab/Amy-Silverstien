export type SubscriptionTier = 'free' | 'credits' | 'premium'
export type AttachmentStyle = 'secure' | 'anxious' | 'avoidant' | 'fearful' | 'unknown'
export type CommunicationPreference = 'voice' | 'text' | 'both'
export type EventType = 'breakup' | 'rejection' | 'trauma' | 'milestone' | 'achievement'
export type GoalCategory = 'confidence' | 'boundaries' | 'vulnerability' | 'communication' | 'other'
export type MemoryType = 'trauma' | 'pattern' | 'goal' | 'sensitivity' | 'win' | 'insight'

export interface UserProfile {
  profile_id: string
  age: number | null
  relationship_status: string | null
  adhd_severity: number | null
  attachment_style: AttachmentStyle
  communication_preference: CommunicationPreference
  timezone: string | null
  preferred_name: string | null
  pronouns: string | null
  voice_enrolled_at: string | null
}

export interface User {
  user_id: string
  email: string
  subscription_tier: SubscriptionTier
  created_at: string
  profile: UserProfile | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  voice_used: boolean
}

export interface Conversation {
  conversation_id: string
  user_id: string
  title: string | null
  messages: ChatMessage[]
  topics_discussed: string[]
  date_started: string
  date_ended: string | null
  duration_seconds: number | null
  user_mood_before: number | null
  user_mood_after: number | null
  key_insights: string[]
  created_at: string
}

export interface ConversationSummary {
  conversation_id: string
  title: string | null
  date_started: string
  date_ended: string | null
  message_count: number
  topics_discussed: string[]
  user_mood_before: number | null
  user_mood_after: number | null
}

export interface LifeEvent {
  event_id: string
  event_type: EventType
  description: string
  date_occurred: string | null
  emotional_weight: number
  still_processing: boolean
  created_at: string
}

export interface BehavioralPattern {
  pattern_id: string
  pattern_name: string
  description: string
  frequency_detected: number
  context: string | null
  last_triggered: string | null
  importance_score: number
  created_at: string
}

export interface Goal {
  goal_id: string
  goal_text: string
  category: GoalCategory
  created_at: string
  achieved_date: string | null
}

export interface Sensitivity {
  sensitivity_id: string
  topic: string
  description: string
  handling_notes: string | null
}

export interface MemoryExtract {
  memory_id: string
  memory_type: MemoryType
  content: string
  importance_score: number
  auto_extracted: boolean
  last_referenced: string | null
  date_learned: string
}

export interface RelationshipEntity {
  person_id: string
  name_or_label: string
  relationship_to_user: string
  current_status: string
  summary: string
  positive_traits: string[]
  red_flags: string[]
  important_events: Array<Record<string, unknown>>
  amy_assessment: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface EmotionalPattern {
  pattern_id: string
  pattern: string
  seen_count: number
  first_seen: string
  last_seen: string
  recommended_response: string | null
  common_thought_loops: string[]
  growth_tracking: Record<string, unknown>
  amy_can_reference: string[]
}

export interface AdviceHistory {
  advice_id: string
  topic: string
  advice_summary: string
  exact_phrases_used: string[]
  date_given: string
  user_reaction: string
  effectiveness: string
}

export interface MemoryUpdate {
  update_id: string
  should_save: boolean
  memory_type: string
  confidence: string
  memory_text: string
  expires: string
  created_at: string
}

export interface MemoryBank {
  life_events: LifeEvent[]
  behavioral_patterns: BehavioralPattern[]
  goals: Goal[]
  sensitivities: Sensitivity[]
  memory_extracts: MemoryExtract[]
  relationship_entities: RelationshipEntity[]
  emotional_patterns: EmotionalPattern[]
  advice_history: AdviceHistory[]
  memory_updates: MemoryUpdate[]
}

export interface WSMessage {
  type: 'token' | 'done' | 'error' | 'message' | 'redirect'
  content?: string
  conversation_id?: string
  full_response?: string
  message?: string
  url?: string
}

export interface SubscriptionStatus {
  tier: SubscriptionTier
  voice_conversations_remaining: number
  text_conversations_remaining: number
}
