-- ============================================================
-- Amy Chatbot — PostgreSQL Schema
-- Run this in Supabase → SQL Editor to create all tables
-- Safe to re-run: all statements use IF NOT EXISTS
-- ============================================================

-- ── Enums ─────────────────────────────────────────────────

DO $$ BEGIN
    CREATE TYPE subscription_tier AS ENUM ('free', 'credits', 'premium');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE attachment_style AS ENUM ('secure', 'anxious', 'avoidant', 'fearful', 'unknown');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE communication_preference AS ENUM ('voice', 'text', 'both');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE event_type AS ENUM ('breakup', 'rejection', 'trauma', 'milestone', 'achievement');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE goal_category AS ENUM ('confidence', 'boundaries', 'vulnerability', 'communication', 'other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('trauma', 'pattern', 'goal', 'sensitivity', 'win', 'insight');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE subscription_event_type AS ENUM (
        'subscription_started', 'upgraded', 'downgraded', 'canceled', 'renewed', 'payment_failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Users ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    user_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL DEFAULT '',
    subscription_tier   subscription_tier NOT NULL DEFAULT 'free',
    stripe_customer_id  VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login          TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── Magic Link Tokens ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS magic_login_tokens (
    token_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    token_hash      VARCHAR(64) UNIQUE NOT NULL,
    expires_at      TIMESTAMP NOT NULL,
    used_at         TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_magic_login_tokens_hash ON magic_login_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_magic_login_tokens_email ON magic_login_tokens(email);

-- ── User Profiles ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    age                     INTEGER,
    relationship_status     VARCHAR(100),
    adhd_severity           INTEGER CHECK (adhd_severity BETWEEN 1 AND 10),
    attachment_style        attachment_style NOT NULL DEFAULT 'unknown',
    communication_preference communication_preference NOT NULL DEFAULT 'text',
    timezone                VARCHAR(50),
    preferred_name          VARCHAR(100),
    pronouns                VARCHAR(50),
    website_embeds          JSONB NOT NULL DEFAULT '[]',
    voice_embedding         JSONB,
    voice_enrolled_at       TIMESTAMP
);

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS voice_embedding JSONB;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS voice_enrolled_at TIMESTAMP;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS nickname VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS age_range VARCHAR(20) NOT NULL DEFAULT 'unknown';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS location_general VARCHAR(200);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS has_adhd BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS has_anxiety BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS known_life_stressors JSONB NOT NULL DEFAULT '[]';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS personality_profile JSONB NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS relationship_history JSONB NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS personal_goals JSONB NOT NULL DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS boundaries_and_sensitivities JSONB NOT NULL DEFAULT '{}';

-- ── Conversations ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title               VARCHAR(255),
    messages            JSONB NOT NULL DEFAULT '[]',
    topics_discussed    JSONB NOT NULL DEFAULT '[]',
    date_started        TIMESTAMP NOT NULL DEFAULT NOW(),
    date_ended          TIMESTAMP,
    duration_seconds    INTEGER,
    user_mood_before    INTEGER CHECK (user_mood_before BETWEEN 1 AND 5),
    user_mood_after     INTEGER CHECK (user_mood_after BETWEEN 1 AND 5),
    key_insights        JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_date_started ON conversations(date_started DESC);

-- ── Memory Bank ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS life_events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type          event_type NOT NULL,
    description         TEXT NOT NULL,
    date_occurred       TIMESTAMP,
    emotional_weight    INTEGER NOT NULL DEFAULT 5 CHECK (emotional_weight BETWEEN 1 AND 10),
    still_processing    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_life_events_user_id ON life_events(user_id);

CREATE TABLE IF NOT EXISTS behavioral_patterns (
    pattern_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    pattern_name        VARCHAR(100) NOT NULL,
    description         TEXT NOT NULL,
    frequency_detected  INTEGER NOT NULL DEFAULT 1,
    context             TEXT,
    last_triggered      TIMESTAMP,
    importance_score    INTEGER NOT NULL DEFAULT 5 CHECK (importance_score BETWEEN 1 AND 10),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_behavioral_patterns_user_id ON behavioral_patterns(user_id);

CREATE TABLE IF NOT EXISTS goals (
    goal_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_text           TEXT NOT NULL,
    category            goal_category NOT NULL DEFAULT 'other',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    achieved_date       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id);

CREATE TABLE IF NOT EXISTS sensitivities (
    sensitivity_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    topic               VARCHAR(200) NOT NULL,
    description         TEXT NOT NULL,
    handling_notes      TEXT
);

CREATE INDEX IF NOT EXISTS idx_sensitivities_user_id ON sensitivities(user_id);

CREATE TABLE IF NOT EXISTS memory_extracts (
    memory_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    memory_type             memory_type NOT NULL,
    content                 TEXT NOT NULL,
    source_conversation_id  UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    importance_score        INTEGER NOT NULL DEFAULT 5 CHECK (importance_score BETWEEN 1 AND 10),
    auto_extracted          BOOLEAN NOT NULL DEFAULT TRUE,
    last_referenced         TIMESTAMP,
    date_learned            TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_extracts_user_id ON memory_extracts(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_extracts_importance ON memory_extracts(user_id, importance_score DESC);

-- Advanced Memory Bank + Conversation Logic

CREATE TABLE IF NOT EXISTS relationship_entities (
    person_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name_or_label        VARCHAR(200) NOT NULL,
    relationship_to_user VARCHAR(50) NOT NULL DEFAULT 'unknown',
    current_status       VARCHAR(50) NOT NULL DEFAULT 'unclear',
    summary              TEXT NOT NULL,
    positive_traits      JSONB NOT NULL DEFAULT '[]',
    red_flags            JSONB NOT NULL DEFAULT '[]',
    important_events     JSONB NOT NULL DEFAULT '[]',
    amy_assessment       JSONB NOT NULL DEFAULT '{}',
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_relationship_entities_user_id ON relationship_entities(user_id);
CREATE INDEX IF NOT EXISTS idx_relationship_entities_updated_at ON relationship_entities(user_id, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_relationship_entities_user_label ON relationship_entities(user_id, lower(name_or_label));

CREATE TABLE IF NOT EXISTS emotional_patterns (
    pattern_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    pattern              TEXT NOT NULL,
    seen_count           INTEGER NOT NULL DEFAULT 1,
    first_seen           TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen            TIMESTAMP NOT NULL DEFAULT NOW(),
    recommended_response TEXT,
    common_thought_loops JSONB NOT NULL DEFAULT '[]',
    growth_tracking      JSONB NOT NULL DEFAULT '{}',
    amy_can_reference    JSONB NOT NULL DEFAULT '[]',
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emotional_patterns_user_id ON emotional_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_emotional_patterns_seen_count ON emotional_patterns(user_id, seen_count DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_emotional_patterns_user_pattern ON emotional_patterns(user_id, md5(pattern));

CREATE TABLE IF NOT EXISTS advice_history (
    advice_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id      UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    topic                VARCHAR(120) NOT NULL,
    advice_summary       TEXT NOT NULL,
    exact_phrases_used   JSONB NOT NULL DEFAULT '[]',
    date_given           TIMESTAMP NOT NULL DEFAULT NOW(),
    user_reaction        VARCHAR(50) NOT NULL DEFAULT 'unknown',
    effectiveness        VARCHAR(50) NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_advice_history_user_id ON advice_history(user_id);
CREATE INDEX IF NOT EXISTS idx_advice_history_topic ON advice_history(user_id, topic, date_given DESC);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    summary_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id      UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    summary              TEXT NOT NULL,
    topics               JSONB NOT NULL DEFAULT '[]',
    emotional_arc        JSONB NOT NULL DEFAULT '{}',
    advice_given         JSONB NOT NULL DEFAULT '[]',
    questions_asked      JSONB NOT NULL DEFAULT '[]',
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_id ON conversation_summaries(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS memory_updates (
    update_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id      UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    should_save          BOOLEAN NOT NULL DEFAULT FALSE,
    memory_type          VARCHAR(80) NOT NULL,
    confidence           VARCHAR(20) NOT NULL DEFAULT 'medium',
    memory_text          TEXT NOT NULL,
    expires              VARCHAR(50) NOT NULL DEFAULT 'never',
    created_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_updates_user_id ON memory_updates(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_updates_should_save ON memory_updates(user_id, should_save);

CREATE TABLE IF NOT EXISTS safety_flags (
    flag_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id      UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    risk_level           VARCHAR(50) NOT NULL,
    trigger_text         TEXT,
    response_mode        VARCHAR(80) NOT NULL DEFAULT 'safety_first',
    resolved             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at          TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_safety_flags_user_id ON safety_flags(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_safety_flags_unresolved ON safety_flags(user_id, resolved);

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    responds_to          JSONB NOT NULL DEFAULT '["validation first","direct honesty","gentle encouragement","step-by-step advice","warm reassurance"]',
    avoids               JSONB NOT NULL DEFAULT '["clinical language","generic advice","too many questions","cold logic","judgmental tone"]',
    preferred_length     VARCHAR(20) NOT NULL DEFAULT 'medium',
    preferred_tone       VARCHAR(80) NOT NULL DEFAULT 'girl-next-door',
    humor_preference     VARCHAR(40) NOT NULL DEFAULT 'playful',
    romantic_dynamic     JSONB NOT NULL DEFAULT '{"user_enjoys_teasing": false, "likes_pet_names": false, "comfortable_with_flirting": false, "preferred_style": "sweet", "avoid_styles": ["too aggressive", "too explicit", "graphic sexual detail"]}',
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS romantic_dynamic JSONB NOT NULL DEFAULT '{"user_enjoys_teasing": false, "likes_pet_names": false, "comfortable_with_flirting": false, "preferred_style": "sweet", "avoid_styles": ["too aggressive", "too explicit", "graphic sexual detail"]}';

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- ── Subscriptions & Credits ────────────────────────────────

CREATE TABLE IF NOT EXISTS subscription_events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type          subscription_event_type NOT NULL,
    tier_before         VARCHAR(50),
    tier_after          VARCHAR(50),
    stripe_event_id     VARCHAR(255),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS voice_credits (
    credit_id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                         UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    voice_conversations_remaining   INTEGER NOT NULL DEFAULT 0,
    text_conversations_remaining    INTEGER NOT NULL DEFAULT 3,
    daily_limit_resets_at           TIMESTAMP,
    last_reset_date                 TIMESTAMP,
    updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ── Widget Embeds ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS website_embeds (
    embed_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(user_id) ON DELETE SET NULL,
    website_domain      VARCHAR(255) NOT NULL,
    embed_code          VARCHAR(100) UNIQUE NOT NULL,
    widget_config       JSONB NOT NULL DEFAULT '{}',
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used           TIMESTAMP
);

-- ── YouTube Content ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS youtube_content (
    video_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_url         VARCHAR(500) UNIQUE NOT NULL,
    title               VARCHAR(500) NOT NULL,
    transcript          TEXT,
    topics              JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ── Auto-update updated_at on users ───────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
