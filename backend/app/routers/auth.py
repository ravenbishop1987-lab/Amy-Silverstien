import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord, SubscriptionTier, AttachmentStyle, CommunicationPreference
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse, UserProfileUpdate, UserProfileResponse
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from app.utils.rate_limiter import cache_delete

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, supa: AsyncClient = Depends(get_supabase)):
    existing = await supa.table("users").select("user_id").eq("email", data.email).maybe_single().execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await supa.table("users").insert({
        "user_id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "subscription_tier": SubscriptionTier.free.value,
        "created_at": now,
        "updated_at": now,
    }).execute()

    await supa.table("user_profiles").insert({
        "profile_id": str(uuid.uuid4()),
        "user_id": user_id,
        "preferred_name": data.preferred_name,
        "attachment_style": AttachmentStyle.unknown.value,
        "communication_preference": CommunicationPreference.text.value,
    }).execute()

    await supa.table("voice_credits").insert({
        "credit_id": str(uuid.uuid4()),
        "user_id": user_id,
        "text_conversations_remaining": 3,
        "voice_conversations_remaining": 0,
    }).execute()

    token = create_access_token(user_id)
    return Token(access_token=token, user_id=user_id, subscription_tier=SubscriptionTier.free)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, supa: AsyncClient = Depends(get_supabase)):
    result = await supa.table("users").select("*").eq("email", data.email).maybe_single().execute()
    user = result.data
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await supa.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()

    token = create_access_token(user["user_id"])
    return Token(
        access_token=token,
        user_id=user["user_id"],
        subscription_tier=SubscriptionTier(user.get("subscription_tier", "free")),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    profile_r = await supa.table("user_profiles").select("*").eq("user_id", str(current_user.user_id)).maybe_single().execute()
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "subscription_tier": current_user.subscription_tier,
        "created_at": current_user.created_at,
        "profile": profile_r.data,
    }


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    update_data = {
        k: (v.value if hasattr(v, "value") else v)
        for k, v in data.model_dump(exclude_none=True).items()
    }

    existing = await supa.table("user_profiles").select("profile_id").eq("user_id", uid).maybe_single().execute()
    if existing.data:
        result = await supa.table("user_profiles").update(update_data).eq("user_id", uid).execute()
        profile = result.data[0] if result.data else existing.data
    else:
        insert_data = {"profile_id": str(uuid.uuid4()), "user_id": uid, **update_data}
        result = await supa.table("user_profiles").insert(insert_data).execute()
        profile = result.data[0] if result.data else insert_data

    await cache_delete(f"memory_context:{uid}")
    return profile


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    await supa.table("users").delete().eq("user_id", str(current_user.user_id)).execute()
