from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Amy Chatbot"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"
    WIDGET_URL: str = "http://localhost:5174"
    FANVUE_URL: str = "https://www.fanvue.com/amysilverstein87"
    GOOGLE_CLIENT_ID: str = ""
    MAGIC_LINK_EXPIRE_MINUTES: int = 15
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Amy"

    # ── Supabase ───────────────────────────────────────────
    SUPABASE_URL: str = ""                 # https://your-ref.supabase.co
    SUPABASE_ANON_KEY: str = ""            # eyJ... (public, safe for frontend)
    SUPABASE_SERVICE_KEY: str = ""         # eyJ... (secret, backend only)
    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── AI Services ────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""
    OPENAI_API_KEY: str = ""

    # ── Stripe ─────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PREMIUM_MONTHLY: str = ""
    STRIPE_PRICE_CREDITS_SINGLE: str = ""
    STRIPE_PRICE_CREDITS_BULK: str = ""

    # ── Pinecone ───────────────────────────────────────────
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "amy-memories"

    # ── Limits ─────────────────────────────────────────────
    FREE_DAILY_CONVERSATIONS: int = 3
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
