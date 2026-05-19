from supabase import create_async_client, AsyncClient
from app.config import settings

_supabase: AsyncClient | None = None


async def init_supabase() -> None:
    global _supabase
    _supabase = await create_async_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_supabase() -> AsyncClient:
    if _supabase is None:
        await init_supabase()
    return _supabase
