import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.subscription import WebsiteEmbed
from app.utils.auth import get_current_user

router = APIRouter(prefix="/embed", tags=["embed"])

DEFAULT_WIDGET_CONFIG = {
    "position": "bottom-right",
    "primaryColor": "#8FAF8F",
    "greeting": "Hey, I'm Amy. Pull up a chair — what's on your mind?",
    "size": "medium",
    "darkMode": False,
}


class EmbedCreate(BaseModel):
    website_domain: str
    widget_config: Optional[dict] = None


class EmbedResponse(BaseModel):
    embed_id: str
    embed_code: str
    website_domain: str
    widget_config: dict
    script_tag: str
    active: bool


@router.post("/create", response_model=EmbedResponse)
async def create_embed(
    data: EmbedCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    embed_code = str(uuid.uuid4()).replace("-", "")[:16]
    config = {**DEFAULT_WIDGET_CONFIG, **(data.widget_config or {})}

    embed = WebsiteEmbed(
        user_id=current_user.user_id,
        website_domain=data.website_domain,
        embed_code=embed_code,
        widget_config=config,
        active=True,
    )
    db.add(embed)
    await db.flush()

    from app.config import settings
    script_tag = f'<script src="{settings.FRONTEND_URL}/widget.js?embed_id={embed_code}" defer></script>'

    return EmbedResponse(
        embed_id=str(embed.embed_id),
        embed_code=embed_code,
        website_domain=embed.website_domain,
        widget_config=config,
        script_tag=script_tag,
        active=True,
    )


@router.get("/list", response_model=list[EmbedResponse])
async def list_embeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebsiteEmbed).where(WebsiteEmbed.user_id == current_user.user_id)
    )
    embeds = result.scalars().all()
    from app.config import settings
    return [
        EmbedResponse(
            embed_id=str(e.embed_id),
            embed_code=e.embed_code,
            website_domain=e.website_domain,
            widget_config=e.widget_config,
            script_tag=f'<script src="{settings.FRONTEND_URL}/widget.js?embed_id={e.embed_code}" defer></script>',
            active=e.active,
        )
        for e in embeds
    ]


@router.get("/config/{embed_code}")
async def get_embed_config(embed_code: str, db: AsyncSession = Depends(get_db)):
    """Called by the widget to fetch its configuration."""
    result = await db.execute(select(WebsiteEmbed).where(WebsiteEmbed.embed_code == embed_code))
    embed = result.scalar_one_or_none()
    if not embed or not embed.active:
        raise HTTPException(status_code=404, detail="Embed not found")

    embed.last_used = datetime.utcnow()
    return embed.widget_config
