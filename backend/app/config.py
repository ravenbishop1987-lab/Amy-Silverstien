from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Amy Chatbot"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"
    WIDGET_URL: str = "http://localhost:5174"
    FANVUE_URL: str = "https://www.fanvue.com/amysilverstein87"
    GOOGLE_CLIENT_ID: str = ""

    # ── Supabase ───────────────────────────────────────────
    SUPABASE_URL: str = ""                 # https://your-ref.supabase.co
    SUPABASE_ANON_KEY: str = ""            # eyJ... (public, safe for frontend)
    SUPABASE_SERVICE_KEY: str = ""         # eyJ... (secret, backend only)
    SUPABASE_DB_PASSWORD: str = ""         # database password from Settings → Database

    # ── Database ───────────────────────────────────────────
    # Leave blank — auto-built from Supabase vars below.
    # Only set manually if NOT using Supabase (e.g. local Docker postgres).
    DATABASE_URL: str = ""
    DATABASE_URL_DIRECT: str = ""

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

    def _supabase_ref(self) -> str:
        """Extract project ref from https://abcxyz.supabase.co → abcxyz"""
        return self.SUPABASE_URL.replace("https://", "").split(".")[0]

    def get_database_url(self) -> str:
        """
        Returns the asyncpg connection URL.
        Priority:
          1. Explicit DATABASE_URL in .env
          2. Auto-built from SUPABASE_URL + SUPABASE_DB_PASSWORD (direct connection)
          3. Local Docker fallback
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        if self.SUPABASE_URL and self.SUPABASE_DB_PASSWORD:
            ref = self._supabase_ref()
            # Direct connection — no region needed, always works
            return (
                f"postgresql+asyncpg://postgres:{self.SUPABASE_DB_PASSWORD}"
                f"@db.{ref}.supabase.co:5432/postgres"
            )

        return "postgresql+asyncpg://amy_user:amy_password@localhost:5432/amy_chatbot"

    def get_database_url_direct(self) -> str:
        """Same direct connection — used by Alembic migrations."""
        return self.get_database_url()

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
