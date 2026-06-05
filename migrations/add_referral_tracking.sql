-- Referral tracking: add attribution columns to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_source TEXT DEFAULT 'Direct';
ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_video_slug TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_video_title TEXT;

-- Referral clicks log
CREATE TABLE IF NOT EXISTS referral_clicks (
  click_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_slug TEXT NOT NULL,
  video_title TEXT,
  clicked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ip_address TEXT,
  user_agent TEXT,
  referer TEXT,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_referral_clicks_slug ON referral_clicks(video_slug);
CREATE INDEX IF NOT EXISTS idx_referral_clicks_clicked_at ON referral_clicks(clicked_at);
CREATE INDEX IF NOT EXISTS idx_users_referrer_source ON users(referrer_source);
CREATE INDEX IF NOT EXISTS idx_users_referrer_slug ON users(referrer_video_slug);
