from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.user import User, SubscriptionTier
from app.models.conversation import Conversation
from app.utils.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_EMAILS = {"kevin.dill@gmail.com"}  # Add admin emails here


def _require_admin(user: User):
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/metrics")
async def get_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)

    total_users = (await db.execute(select(func.count(User.user_id)))).scalar()
    free_users = (await db.execute(select(func.count(User.user_id)).where(User.subscription_tier == SubscriptionTier.free))).scalar()
    credits_users = (await db.execute(select(func.count(User.user_id)).where(User.subscription_tier == SubscriptionTier.credits))).scalar()
    premium_users = (await db.execute(select(func.count(User.user_id)).where(User.subscription_tier == SubscriptionTier.premium))).scalar()
    total_conversations = (await db.execute(select(func.count(Conversation.conversation_id)))).scalar()

    return {
        "users": {
            "total": total_users,
            "free": free_users,
            "credits": credits_users,
            "premium": premium_users,
        },
        "conversations": {
            "total": total_conversations,
        },
    }


@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [
        {
            "user_id": str(u.user_id),
            "email": u.email,
            "tier": u.subscription_tier,
            "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]
