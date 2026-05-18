"""Run once: adds voice_embedding and voice_enrolled_at to user_profiles."""
import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE user_profiles "
            "ADD COLUMN IF NOT EXISTS voice_embedding JSONB, "
            "ADD COLUMN IF NOT EXISTS voice_enrolled_at TIMESTAMP"
        ))
    print("Migration complete.")

asyncio.run(migrate())
