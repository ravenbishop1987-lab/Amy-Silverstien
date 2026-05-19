from fastapi import APIRouter, Depends, HTTPException
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
from app.utils.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_EMAILS = {"kevin.dill@gmail.com"}


def _require_admin(user: UserRecord):
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/metrics")
async def get_metrics(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    total_r = await supa.table("users").select("*", count="exact").execute()
    free_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "free").execute()
    credits_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "credits").execute()
    premium_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "premium").execute()
    convos_r = await supa.table("conversations").select("*", count="exact").execute()

    return {
        "users": {
            "total": total_r.count or 0,
            "free": free_r.count or 0,
            "credits": credits_r.count or 0,
            "premium": premium_r.count or 0,
        },
        "conversations": {
            "total": convos_r.count or 0,
        },
    }


@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)
    result = await supa.table("users").select("user_id,email,subscription_tier,created_at,last_login").order("created_at", desc=True).range(skip, skip + limit - 1).execute()
    return [
        {
            "user_id": u["user_id"],
            "email": u["email"],
            "tier": u["subscription_tier"],
            "created_at": u["created_at"],
            "last_login": u.get("last_login"),
        }
        for u in (result.data or [])
    ]
