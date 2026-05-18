-- ============================================================
-- Amy Chatbot — PostgreSQL Schema
-- Run this in Supabase → SQL Editor to create all tables
-- ============================================================

-- ── Enums ─────────────────────────────────────────────────

CREATE TYPE subscription_tier AS ENUM ('free', 'credits', 'premium');
CREATE TYPE attachment_style AS ENUM ('secure', 'anxious', 'avoidant', 'fearful', 'unknown');
CREATE TYPE communication_preference AS ENUM ('voice', 'text', 'both');
CREATE TYPE event_type AS ENUM ('breakup', 'rejection', 'trauma', 'milestone', 'achievement');
CREATE TYPE goal_category AS ENUM ('confidence', 'boundaries', 'vulnerability', 'communication', 'other');
CREATE TYPE memory_type AS ENUM ('trauma', 'pattern', 'goal', 'sensitivity', 'win', 'insight');
CREATE TYPE subscription_event_type AS ENUM (
    'subscription_started', 'upgraded', 'downgraded', 'canceled', 'renewed', 'payment_failed'
);

-- ── Users ─────────────────────────────────────────────────

CREATE TABLE users (
    user_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL,
    subscription_tier   subscription_tier NOT NULL DEFAULT 'free',
    stripe_customer_id  VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login          TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- ── User Profiles ──────────────────────────────────────────

CREATE TABLE user_profiles (
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
    website_embeds          JSONB NOT NULL DEFAULT '[]'
);

-- ── Conversations ──────────────────────────────────────────

CREATE TABLE conversations (
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

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_date_started ON conversations(date_started DESC);

-- ── Memory Bank ────────────────────────────────────────────

CREATE TABLE life_events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type          event_type NOT NULL,
    description         TEXT NOT NULL,
    date_occurred       TIMESTAMP,
    emotional_weight    INTEGER NOT NULL DEFAULT 5 CHECK (emotional_weight BETWEEN 1 AND 10),
    still_processing    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_life_events_user_id ON life_events(user_id);

CREATE TABLE behavioral_patterns (
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

CREATE INDEX idx_behavioral_patterns_user_id ON behavioral_patterns(user_id);

CREATE TABLE goals (
    goal_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_text           TEXT NOT NULL,
    category            goal_category NOT NULL DEFAULT 'other',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    achieved_date       TIMESTAMP
);

CREATE INDEX idx_goals_user_id ON goals(user_id);

CREATE TABLE sensitivities (
    sensitivity_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    topic               VARCHAR(200) NOT NULL,
    description         TEXT NOT NULL,
    handling_notes      TEXT
);

CREATE INDEX idx_sensitivities_user_id ON sensitivities(user_id);

CREATE TABLE memory_extracts (
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

CREATE INDEX idx_memory_extracts_user_id ON memory_extracts(user_id);
CREATE INDEX idx_memory_extracts_importance ON memory_extracts(user_id, importance_score DESC);

-- ── Subscriptions & Credits ────────────────────────────────

CREATE TABLE subscription_events (
    event_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    event_type          subscription_event_type NOT NULL,
    tier_before         VARCHAR(50),
    tier_after          VARCHAR(50),
    stripe_event_id     VARCHAR(255),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE voice_credits (
    credit_id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                         UUID UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    voice_conversations_remaining   INTEGER NOT NULL DEFAULT 0,
    text_conversations_remaining    INTEGER NOT NULL DEFAULT 3,
    daily_limit_resets_at           TIMESTAMP,
    last_reset_date                 TIMESTAMP,
    updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ── Widget Embeds ──────────────────────────────────────────

CREATE TABLE website_embeds (
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

CREATE TABLE youtube_content (
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

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
