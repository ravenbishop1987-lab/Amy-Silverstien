-- Run this in Supabase SQL Editor to add 'blocked' to the subscription_tier enum
-- and create the safety_flags reviewer_notes column if not present.

-- Add 'blocked' to subscription_tier enum
ALTER TYPE subscription_tier ADD VALUE IF NOT EXISTS 'blocked';

-- Add reviewer_notes to safety_flags if not present
ALTER TABLE safety_flags ADD COLUMN IF NOT EXISTS reviewer_notes TEXT;
ALTER TABLE safety_flags ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;
