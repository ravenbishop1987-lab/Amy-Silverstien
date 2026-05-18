"""
Test your Supabase connection before starting the app:
  python test_db.py
"""
import asyncio
import sys
from sqlalchemy import text


async def test():
    from app.config import settings
    from app.database import engine

    url = settings.get_database_url()
    preview = url[:70] + "..." if len(url) > 70 else url
    print(f"\nConnecting to: {preview}")

    if not settings.SUPABASE_URL or "your-project-ref" in settings.SUPABASE_URL:
        print("\n❌  SUPABASE_URL still has placeholder text.")
        print("    Open backend/.env and fill in your Supabase credentials.\n")
        sys.exit(1)

    if not settings.SUPABASE_DB_PASSWORD or settings.SUPABASE_DB_PASSWORD == "your-database-password":
        print("\n❌  SUPABASE_DB_PASSWORD not set.")
        print("    Go to Supabase → Settings → Database → Database password\n")
        sys.exit(1)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"\n✅  Connected to Supabase!")
            print(f"    PostgreSQL: {version[:50]}\n")
    except Exception as e:
        print(f"\n❌  Connection failed: {e}\n")
        sys.exit(1)


asyncio.run(test())
