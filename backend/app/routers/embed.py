import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
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
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    embed_code = str(uuid.uuid4()).replace("-", "")[:16]
    config = {**DEFAULT_WIDGET_CONFIG, **(data.widget_config or {})}
    embed_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await supa.table("website_embeds").insert({
        "embed_id": embed_id,
        "user_id": str(current_user.user_id),
        "website_domain": data.website_domain,
        "embed_code": embed_code,
        "widget_config": config,
        "active": True,
        "created_at": now,
    }).execute()

    from app.config import settings
    script_tag = f'<script src="{settings.FRONTEND_URL}/widget.js?embed_id={embed_code}" defer></script>'

    return EmbedResponse(
        embed_id=embed_id,
        embed_code=embed_code,
        website_domain=data.website_domain,
        widget_config=config,
        script_tag=script_tag,
        active=True,
    )


@router.get("/list", response_model=list[EmbedResponse])
async def list_embeds(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    result = await supa.table("website_embeds").select("*").eq("user_id", str(current_user.user_id)).execute()
    from app.config import settings
    return [
        EmbedResponse(
            embed_id=e["embed_id"],
            embed_code=e["embed_code"],
            website_domain=e["website_domain"],
            widget_config=e["widget_config"],
            script_tag=f'<script src="{settings.FRONTEND_URL}/widget.js?embed_id={e["embed_code"]}" defer></script>',
            active=e["active"],
        )
        for e in (result.data or [])
    ]


@router.get("/config/{embed_code}")
async def get_embed_config(embed_code: str, supa: AsyncClient = Depends(get_supabase)):
    """Called by the widget to fetch its configuration."""
    result = await supa.table("website_embeds").select("*").eq("embed_code", embed_code).limit(1).execute()
    embed = result.data[0] if result and result.data else None
    if not embed or not embed.get("active"):
        raise HTTPException(status_code=404, detail="Embed not found")

    await supa.table("website_embeds").update({"last_used": datetime.utcnow().isoformat()}).eq("embed_code", embed_code).execute()
    return embed["widget_config"]
