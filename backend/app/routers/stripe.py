from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
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
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    url = await stripe_service.create_subscription_checkout(current_user, supa)
    return CheckoutResponse(checkout_url=url)


@router.post("/credits/single", response_model=CheckoutResponse)
async def buy_single_credits(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    url = await stripe_service.create_credits_checkout(current_user, bulk=False, supa=supa)
    return CheckoutResponse(checkout_url=url)


@router.post("/credits/bulk", response_model=CheckoutResponse)
async def buy_bulk_credits(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    url = await stripe_service.create_credits_checkout(current_user, bulk=True, supa=supa)
    return CheckoutResponse(checkout_url=url)


@router.post("/gifts/checkout", response_model=CheckoutResponse)
async def create_gift_checkout(
    data: GiftCheckoutRequest,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    try:
        url = await stripe_service.create_gift_checkout(
            current_user,
            data.gift_type,
            data.personal_message.strip(),
            data.conversation_id,
            supa,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CheckoutResponse(checkout_url=url)


@router.post("/gifts/confirm")
async def confirm_gift_checkout(
    data: GiftConfirmRequest,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    try:
        gift = await stripe_service.confirm_gift_checkout(data.session_id, current_user, supa)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return gift


@router.delete("/subscription", status_code=204)
async def cancel_subscription(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    success = await stripe_service.cancel_subscription(current_user, supa)
    if not success:
        raise HTTPException(status_code=400, detail="No active subscription found")


@router.get("/status")
async def subscription_status(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    vc_r = await supa.table("voice_credits").select("*").eq("user_id", str(current_user.user_id)).limit(1).execute()
    vc = vc_r.data

    return {
        "tier": current_user.subscription_tier,
        "voice_conversations_remaining": vc["voice_conversations_remaining"] if vc else 0,
        "text_conversations_remaining": vc["text_conversations_remaining"] if vc else 0,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, supa: AsyncClient = Depends(get_supabase)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result = await stripe_service.handle_webhook(payload, sig_header, supa)
    if result.get("status") == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    return result
