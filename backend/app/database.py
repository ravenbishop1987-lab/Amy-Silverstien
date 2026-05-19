import logging
from fastapi import HTTPException
from supabase import create_async_client, AsyncClient
from app.config import settings

logger = logging.getLogger(__name__)

_supabase: AsyncClient | None = None


async def init_supabase() -> None:
    global _supabase
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY is not set — check Render environment variables")
        return
    try:
        _supabase = await create_async_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized")
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")


async def get_supabase() -> AsyncClient:
    if _supabase is None:
        await init_supabase()
    if _supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available — SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment",
        )
    return _supabase
