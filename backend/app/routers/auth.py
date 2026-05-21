import logging
import hashlib
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from supabase import AsyncClient

from app.config import settings
from app.database import get_supabase
from app.models.user import UserRecord, SubscriptionTier
from app.schemas.user import (
    GoogleLogin,
    MagicLinkRequest,
    MagicLinkVerify,
    SupabaseSessionLogin,
    Token,
    UserCreate,
    UserLogin,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
)
from app.utils.auth import create_access_token, get_current_user, hash_password, verify_password
from app.utils.rate_limiter import cache_delete

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_magic_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        from dateutil.parser import parse
        return parse(str(value)).replace(tzinfo=None)
    except Exception:
        return None


def _frontend_magic_link(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/magic-login?token={token}"


def _send_magic_link_email(email: str, link: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning("[magic-link] SMTP is not configured. Login link for %s: %s", email, link)
        return

    message = EmailMessage()
    message["Subject"] = "Your Amy sign-in link"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = email
    message.set_content(
        "Use this secure link to sign in to Amy:\n\n"
        f"{link}\n\n"
        f"This link expires in {settings.MAGIC_LINK_EXPIRE_MINUTES} minutes."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def _get_supabase_auth_user(access_token: str) -> dict:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured")

    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)
    except Exception as exc:
        logger.exception("[supabase-auth] user lookup request failed: %s", exc)
        raise HTTPException(status_code=503, detail="Could not verify Supabase login")

    if response.status_code != 200:
        logger.warning("[supabase-auth] user lookup failed with status %s: %s", response.status_code, response.text[:300])
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase login")

    return response.json()


def _token_payload(user_id: str, email: str, tier: str | None = None) -> dict:
    try:
        subscription_tier = SubscriptionTier(tier or SubscriptionTier.free.value)
    except ValueError:
        subscription_tier = SubscriptionTier.free

    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
        "subscription_tier": subscription_tier.value,
    }


async def _create_default_profile_and_credits(
    supa: AsyncClient,
    user_id: str,
    preferred_name: str | None = None,
    log_prefix: str = "auth",
) -> None:
    try:
        profile_row: dict = {
            "profile_id": str(uuid.uuid4()),
            "user_id": user_id,
        }
        if preferred_name:
            profile_row["preferred_name"] = preferred_name
        await supa.table("user_profiles").insert(profile_row).execute()
        logger.info("[%s] user_profiles row created", log_prefix)
    except Exception as exc:
        logger.warning("[%s] user_profiles insert skipped: %s: %s", log_prefix, type(exc).__name__, exc)

    try:
        await supa.table("voice_credits").insert({
            "credit_id": str(uuid.uuid4()),
            "user_id": user_id,
            "text_conversations_remaining": 3,
            "voice_conversations_remaining": 0,
        }).execute()
        logger.info("[%s] voice_credits row created", log_prefix)
    except Exception as exc:
        logger.warning("[%s] voice_credits insert skipped: %s: %s", log_prefix, type(exc).__name__, exc)


async def _get_or_create_user_for_email(supa: AsyncClient, email: str, log_prefix: str) -> dict:
    try:
        result = await supa.table("users").select("*").eq("email", email).limit(1).execute()
    except Exception as exc:
        logger.exception("[%s] user lookup failed for %s: %s", log_prefix, email, exc)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    existing = result.data[0] if result and result.data else None
    if existing:
        return existing

    user_id = str(uuid.uuid4())
    logger.info("[%s] creating user %s for %s", log_prefix, user_id, email)
    try:
        insert = await supa.table("users").insert({
            "user_id": user_id,
            "email": email,
            "password_hash": "",
        }).execute()
    except Exception as exc:
        logger.exception("[%s] users insert failed for %s: %s: %s", log_prefix, email, type(exc).__name__, exc)
        raise HTTPException(status_code=503, detail="Could not create account - please try again")

    await _create_default_profile_and_credits(supa, user_id, None, log_prefix)
    return (insert.data or [{}])[0] or {
        "user_id": user_id,
        "email": email,
        "subscription_tier": SubscriptionTier.free.value,
    }


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, supa: AsyncClient = Depends(get_supabase)):
    try:
        logger.info(f"[register] attempt: {data.email}")

        try:
            existing = await supa.table("users").select("user_id").eq("email", data.email).limit(1).execute()
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"[register] email-check DB error for {data.email}: {exc}")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        if existing and existing.data:
            logger.info(f"[register] duplicate email: {data.email}")
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())
        logger.info(f"[register] inserting user {user_id}")

        try:
            await supa.table("users").insert({
                "user_id": user_id,
                "email": data.email,
                "password_hash": hash_password(data.password),
            }).execute()
            logger.info("[register] users row created")
        except Exception as exc:
            logger.exception(f"[register] users insert failed for {data.email}: {type(exc).__name__}: {exc}")
            raise HTTPException(status_code=503, detail="Registration failed - please try again")

        await _create_default_profile_and_credits(supa, user_id, data.preferred_name, "register")

        logger.info(f"[register] success for {data.email}")
        return _token_payload(user_id, data.email)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"[register] unexpected failure for {data.email}: {exc}")
        raise HTTPException(status_code=503, detail="Registration failed - please try again")


@router.post("/login", response_model=Token)
async def login(data: UserLogin, supa: AsyncClient = Depends(get_supabase)):
    try:
        try:
            result = await supa.table("users").select("*").eq("email", data.email).limit(1).execute()
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"[login] query failed for {data.email}: {exc}")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        user = result.data[0] if result and result.data else None
        if not user or not verify_password(data.password, user.get("password_hash")):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        try:
            await supa.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()
        except Exception as exc:
            logger.warning(f"[login] last_login update skipped for {user['user_id']}: {type(exc).__name__}: {exc}")

        try:
            tier = SubscriptionTier(user.get("subscription_tier", "free"))
        except ValueError:
            tier = SubscriptionTier.free

        return _token_payload(user["user_id"], user["email"], tier.value)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"[login] unexpected failure for {data.email}: {exc}")
        raise HTTPException(status_code=503, detail="Login failed - please try again")


@router.post("/magic-link")
async def request_magic_link(data: MagicLinkRequest, supa: AsyncClient = Depends(get_supabase)):
    email = data.email.strip().lower()
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_magic_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)
    link = _frontend_magic_link(raw_token)

    try:
        await supa.table("magic_login_tokens").insert({
            "token_id": str(uuid.uuid4()),
            "email": email,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
        }).execute()
    except Exception as exc:
        logger.exception("[magic-link] token insert failed for %s: %s: %s", email, type(exc).__name__, exc)
        raise HTTPException(status_code=503, detail="Could not create sign-in link - please try again")

    try:
        _send_magic_link_email(email, link)
    except Exception as exc:
        logger.exception("[magic-link] email send failed for %s: %s: %s", email, type(exc).__name__, exc)
        raise HTTPException(status_code=503, detail="Could not send sign-in email - please try again")

    response = {"detail": "Check your email for your sign-in link"}
    if settings.ENVIRONMENT != "production" and (not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL):
        response["magic_link"] = link
    return response


@router.post("/magic-link/verify", response_model=Token)
async def verify_magic_link(data: MagicLinkVerify, supa: AsyncClient = Depends(get_supabase)):
    token = data.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Missing sign-in token")

    token_hash = _hash_magic_token(token)
    try:
        result = await supa.table("magic_login_tokens").select("*").eq("token_hash", token_hash).limit(1).execute()
    except Exception as exc:
        logger.exception("[magic-link] token lookup failed: %s", exc)
        raise HTTPException(status_code=503, detail="Could not verify sign-in link")

    row = result.data[0] if result and result.data else None
    if not row:
        raise HTTPException(status_code=401, detail="This sign-in link is invalid or has already been used")

    expires_at = _parse_dt(row.get("expires_at"))
    if row.get("used_at") or not expires_at or expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="This sign-in link has expired")

    email = str(row["email"]).strip().lower()
    user = await _get_or_create_user_for_email(supa, email, "magic-link")

    try:
        await supa.table("magic_login_tokens").update({"used_at": datetime.utcnow().isoformat()}).eq("token_hash", token_hash).execute()
    except Exception as exc:
        logger.warning("[magic-link] could not mark token used for %s: %s: %s", email, type(exc).__name__, exc)

    try:
        await supa.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()
    except Exception as exc:
        logger.warning("[magic-link] last_login update skipped for %s: %s: %s", user["user_id"], type(exc).__name__, exc)

    return _token_payload(user["user_id"], user["email"], user.get("subscription_tier"))


@router.post("/google", response_model=Token)
async def google_login(data: GoogleLogin, supa: AsyncClient = Depends(get_supabase)):
    if not settings.GOOGLE_CLIENT_ID:
        logger.error("[google-login] GOOGLE_CLIENT_ID is not configured")
        raise HTTPException(status_code=503, detail="Google login is not configured")

    try:
        claims = google_id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        logger.warning(f"[google-login] invalid Google credential: {exc}")
        raise HTTPException(status_code=401, detail="Invalid Google login")
    except Exception as exc:
        logger.exception(f"[google-login] verification failed: {exc}")
        raise HTTPException(status_code=503, detail="Google login failed - please try again")

    email = str(claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    preferred_name = str(claims.get("given_name") or claims.get("name") or "").strip() or None

    user = await _get_or_create_user_for_email(supa, email, "google-login")
    if preferred_name:
        try:
            existing_profile = await supa.table("user_profiles").select("profile_id,preferred_name").eq("user_id", user["user_id"]).limit(1).execute()
            ep = existing_profile.data[0] if existing_profile and existing_profile.data else None
            if ep and not ep.get("preferred_name"):
                await supa.table("user_profiles").update({"preferred_name": preferred_name}).eq("user_id", user["user_id"]).execute()
        except Exception as exc:
            logger.warning("[google-login] preferred_name update skipped for %s: %s: %s", user["user_id"], type(exc).__name__, exc)

    try:
        await supa.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()
    except Exception as exc:
        logger.warning(f"[google-login] last_login update skipped for {user['user_id']}: {type(exc).__name__}: {exc}")

    return _token_payload(user["user_id"], user["email"], user.get("subscription_tier"))


@router.post("/supabase-session", response_model=Token)
async def supabase_session_login(data: SupabaseSessionLogin, supa: AsyncClient = Depends(get_supabase)):
    auth_user = await _get_supabase_auth_user(data.access_token)
    email = str(auth_user.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Supabase account has no email")

    metadata = auth_user.get("user_metadata") or {}
    preferred_name = str(metadata.get("name") or metadata.get("full_name") or "").strip() or None
    user = await _get_or_create_user_for_email(supa, email, "supabase-auth")

    if preferred_name:
        try:
            existing_profile = await supa.table("user_profiles").select("profile_id,preferred_name").eq("user_id", user["user_id"]).limit(1).execute()
            ep = existing_profile.data[0] if existing_profile and existing_profile.data else None
            if ep and not ep.get("preferred_name"):
                await supa.table("user_profiles").update({"preferred_name": preferred_name}).eq("user_id", user["user_id"]).execute()
        except Exception as exc:
            logger.warning("[supabase-auth] preferred_name update skipped for %s: %s: %s", user["user_id"], type(exc).__name__, exc)

    try:
        await supa.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()
    except Exception as exc:
        logger.warning("[supabase-auth] last_login update skipped for %s: %s: %s", user["user_id"], type(exc).__name__, exc)

    return _token_payload(user["user_id"], user["email"], user.get("subscription_tier"))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    profile_r = await supa.table("user_profiles").select("*").eq("user_id", str(current_user.user_id)).limit(1).execute()
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "subscription_tier": current_user.subscription_tier,
        "created_at": current_user.created_at,
        "profile": profile_r.data[0] if profile_r and profile_r.data else None,
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

    existing = await supa.table("user_profiles").select("profile_id").eq("user_id", uid).limit(1).execute()
    if existing and existing.data:
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
