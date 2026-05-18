from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserProfile, SubscriptionTier
from app.models.subscription import VoiceCredit
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse, UserProfileUpdate, UserProfileResponse
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        subscription_tier=SubscriptionTier.free,
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(user_id=user.user_id, preferred_name=data.preferred_name)
    db.add(profile)

    voice_credit = VoiceCredit(user_id=user.user_id, text_conversations_remaining=3)
    db.add(voice_credit)

    token = create_access_token(str(user.user_id))
    return Token(access_token=token, user_id=str(user.user_id), subscription_tier=user.subscription_tier)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.last_login = datetime.utcnow()
    token = create_access_token(str(user.user_id))
    return Token(access_token=token, user_id=str(user.user_id), subscription_tier=user.subscription_tier)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.refresh(current_user, ["profile"])
    return current_user


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=current_user.user_id)
        db.add(profile)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    from app.utils.rate_limiter import cache_delete
    await cache_delete(f"memory_context:{current_user.user_id}")
    return profile


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.delete(current_user)
