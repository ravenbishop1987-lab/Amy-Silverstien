from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.subscription import VoiceCredit
from app.services.stripe_service import stripe_service
from app.utils.auth import get_current_user

router = APIRouter(prefix="/stripe", tags=["stripe"])


class CheckoutResponse(BaseModel):
    checkout_url: str


class GiftCheckoutRequest(BaseModel):
    gift_type: str
    personal_message: str = ""
    conversation_id: str | None = None


class GiftConfirmRequest(BaseModel):
    session_id: str


@router.post("/subscribe", response_model=CheckoutResponse)
async def create_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_subscription_checkout(current_user, db)
    return CheckoutResponse(checkout_url=url)


@router.post("/credits/single", response_model=CheckoutResponse)
async def buy_single_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_credits_checkout(current_user, bulk=False, db=db)
    return CheckoutResponse(checkout_url=url)


@router.post("/credits/bulk", response_model=CheckoutResponse)
async def buy_bulk_credits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_credits_checkout(current_user, bulk=True, db=db)
    return CheckoutResponse(checkout_url=url)


@router.post("/gifts/checkout", response_model=CheckoutResponse)
async def create_gift_checkout(
    data: GiftCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        url = await stripe_service.create_gift_checkout(
            current_user,
            data.gift_type,
            data.personal_message.strip(),
            data.conversation_id,
            db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CheckoutResponse(checkout_url=url)


@router.post("/gifts/confirm")
async def confirm_gift_checkout(
    data: GiftConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        gift = await stripe_service.confirm_gift_checkout(data.session_id, current_user, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return gift


@router.delete("/subscription", status_code=204)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await stripe_service.cancel_subscription(current_user, db)
    if not success:
        raise HTTPException(status_code=400, detail="No active subscription found")


@router.get("/status")
async def subscription_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vc_result = await db.execute(select(VoiceCredit).where(VoiceCredit.user_id == current_user.user_id))
    vc = vc_result.scalar_one_or_none()

    return {
        "tier": current_user.subscription_tier,
        "voice_conversations_remaining": vc.voice_conversations_remaining if vc else 0,
        "text_conversations_remaining": vc.text_conversations_remaining if vc else 0,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result = await stripe_service.handle_webhook(payload, sig_header, db)
    if result.get("status") == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    return result
