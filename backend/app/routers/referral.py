import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["referral"])

ADMIN_EMAILS = {"ravenbishop1987@gmail.com"}

# Seed data — written to the DB on first use if the table is empty.
_SEED_MAP: dict[str, str] = {
    "let-me-stay-with-you": "Let Me Stay With You Tonight 💤 ADHD Sleep Talk",
    "when-adhd-brain-wont-shut-up": "When Your ADHD Brain Won't Shut Up 🧠 Sleep...",
    "anxious-attachment-2am": "Anxious Attachment & The 2AM Overthrinking Loop",
    "nervous-system-rest": "Let Your Nervous System Rest 💚 ADHD Sleep...",
    "fall-asleep-adhd-girl": "Fall Asleep With An ADHD Girl Who Actually Gets...",
    "fall-asleep-sophie-ep8": "Sleeping With Sophie Ep. 8 | Let Your ADHD Brain...",
    "ill-be-here-when-you-wake-up": "I'll Be Here When You Wake Up 💤 ADHD Guided...",
    "stay-with-me-tonight": "Stay With Me Tonight ❤️ ADHD Sleep Talk Down...",
    "sleep-with-sophie-ep4": "Sleep With Sophie Ep 4 💤 Fall Asleep Beside Me...",
    "come-lay-next-to-me": "Come Lay Next To Me | Sleeping With Sophie Ep...",
    "adhd-girl-who-gets-it": "Fall Asleep With An ADHD Girl Who Actually Gets...",
    "late-night-comfort-talks": "Late Night Comfort Talks 💭 For Overthinkers &...",
    "rainy-night-conversations": "Rainy Night Conversations for ADHD Overthinker...",
    "adhd-relationships-intense": "ADHD Relationships Feel Intense When Someone...",
    "i-dont-care-bad-sleep": "I Don't Care If You Didn't Sleep Well Last Night...",
}


def _slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:60]


async def _get_video_title(slug: str, supa: AsyncClient) -> str | None:
    try:
        r = await supa.table("video_slugs").select("title").eq("slug", slug).limit(1).execute()
        if r.data:
            return r.data[0]["title"]
    except Exception as exc:
        logger.warning("[referral] DB slug lookup failed: %s", exc)
    return _SEED_MAP.get(slug)


async def _ensure_seeded(supa: AsyncClient) -> None:
    """Insert seed rows that don't exist yet — runs once per cold start."""
    try:
        r = await supa.table("video_slugs").select("slug", count="exact").execute()
        if (r.count or 0) > 0:
            return
        rows = [{"slug": k, "title": v} for k, v in _SEED_MAP.items()]
        await supa.table("video_slugs").upsert(rows, on_conflict="slug").execute()
    except Exception as exc:
        logger.warning("[referral] seed failed: %s", exc)


class ReferralClickBody(BaseModel):
    video_slug: str
    video_title: Optional[str] = None
    referer: Optional[str] = None
    user_agent: Optional[str] = None


class AttributeReferralBody(BaseModel):
    video_slug: str
    video_title: str


class AddSlugBody(BaseModel):
    title: str
    slug: Optional[str] = None  # auto-generated from title if omitted


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("/yt/{video_slug}")
async def youtube_referral_redirect(
    video_slug: str,
    request: Request,
    supa: AsyncClient = Depends(get_supabase),
):
    """Clean URL pinned in YouTube comments. Logs click, redirects to homepage."""
    slug = video_slug.lower().strip()
    video_title = await _get_video_title(slug, supa)

    if video_title:
        try:
            await supa.table("referral_clicks").insert({
                "video_slug": slug,
                "video_title": video_title,
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "referer": request.headers.get("referer"),
            }).execute()
        except Exception as exc:
            logger.warning("[referral] click log failed for %s: %s", slug, exc)

    from app.config import settings
    frontend = settings.FRONTEND_URL.rstrip("/")
    if video_title:
        return RedirectResponse(url=f"{frontend}/?ref={slug}", status_code=302)
    return RedirectResponse(url=frontend, status_code=302)


@router.post("/referral/click")
async def log_referral_click(
    body: ReferralClickBody,
    request: Request,
    supa: AsyncClient = Depends(get_supabase),
):
    slug = body.video_slug.lower().strip()
    video_title = body.video_title or await _get_video_title(slug, supa)

    if not video_title:
        return {"ok": True, "known": False}

    try:
        await supa.table("referral_clicks").insert({
            "video_slug": slug,
            "video_title": video_title,
            "ip_address": request.client.host if request.client else None,
            "user_agent": body.user_agent or request.headers.get("user-agent"),
            "referer": body.referer,
        }).execute()
    except Exception as exc:
        logger.warning("[referral] frontend click log failed for %s: %s", slug, exc)

    return {"ok": True, "known": True, "video_title": video_title}


@router.post("/referral/attribute")
async def attribute_referral(
    body: AttributeReferralBody,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    slug = body.video_slug.lower().strip()
    video_title = body.video_title or await _get_video_title(slug, supa)
    if not video_title:
        return {"ok": False, "reason": "unknown slug"}

    try:
        existing = await supa.table("users").select("referrer_source").eq(
            "user_id", str(current_user.user_id)
        ).single().execute()
        if existing.data and existing.data.get("referrer_source") not in (None, "Direct", ""):
            return {"ok": False, "reason": "already attributed"}
    except Exception:
        pass

    try:
        await supa.table("users").update({
            "referrer_source": "YouTube",
            "referrer_video_slug": slug,
            "referrer_video_title": video_title,
        }).eq("user_id", str(current_user.user_id)).execute()
    except Exception as exc:
        logger.warning("[referral] attribute update failed: %s", exc)
        return {"ok": False, "reason": str(exc)}

    return {"ok": True}


@router.get("/referral/video-map")
async def get_video_map(supa: AsyncClient = Depends(get_supabase)):
    """Returns slug→title map for the frontend."""
    await _ensure_seeded(supa)
    try:
        r = await supa.table("video_slugs").select("slug, title").order("created_at").execute()
        return {row["slug"]: row["title"] for row in (r.data or [])}
    except Exception:
        return _SEED_MAP


# ── Admin slug management ─────────────────────────────────────────────────────

def _require_admin(user: UserRecord):
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/admin/referral/slugs")
async def list_slugs(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)
    await _ensure_seeded(supa)
    r = await supa.table("video_slugs").select("slug, title, created_at").order("created_at", desc=True).execute()
    return r.data or []


@router.post("/admin/referral/slugs")
async def add_slug(
    body: AddSlugBody,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)
    slug = (body.slug or _slugify(body.title)).lower().strip()
    if not slug:
        raise HTTPException(status_code=400, detail="Could not generate slug from title")

    try:
        await supa.table("video_slugs").insert({"slug": slug, "title": body.title.strip()}).execute()
    except Exception as exc:
        err = str(exc)
        if "duplicate" in err.lower() or "unique" in err.lower():
            raise HTTPException(status_code=409, detail=f"Slug '{slug}' already exists")
        raise HTTPException(status_code=500, detail=f"DB error: {err}")

    return {"ok": True, "slug": slug, "title": body.title.strip()}


@router.delete("/admin/referral/slugs/{slug}")
async def delete_slug(
    slug: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)
    await supa.table("video_slugs").delete().eq("slug", slug).execute()
    return {"ok": True}


# ── Admin analytics endpoints ─────────────────────────────────────────────────

@router.get("/admin/referral/stats")
async def referral_stats(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    clicks_r = await supa.table("referral_clicks").select("*", count="exact").execute()
    total_clicks = clicks_r.count or 0

    yt_users_r = await supa.table("users").select("*", count="exact").eq("referrer_source", "YouTube").execute()
    total_signups = yt_users_r.count or 0

    yt_premium_r = await supa.table("users").select("*", count="exact").eq("referrer_source", "YouTube").eq("subscription_tier", "premium").execute()
    total_premium = yt_premium_r.count or 0

    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    new_week_r = await supa.table("users").select("*", count="exact").eq("referrer_source", "YouTube").gte("created_at", week_ago).execute()

    return {
        "total_clicks": total_clicks,
        "total_signups": total_signups,
        "new_signups_this_week": new_week_r.count or 0,
        "total_premium_from_yt": total_premium,
        "conversion_rate": round(100.0 * total_premium / total_signups, 1) if total_signups else 0,
        "mrr_from_yt": total_premium * 10,
    }


@router.get("/admin/referral/videos")
async def referral_videos(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    clicks_r = await supa.table("referral_clicks").select("video_slug, video_title").execute()
    click_counts: dict[str, dict] = {}
    for row in (clicks_r.data or []):
        slug = row["video_slug"]
        if slug not in click_counts:
            click_counts[slug] = {"video_slug": slug, "video_title": row.get("video_title") or slug, "clicks": 0}
        click_counts[slug]["clicks"] += 1

    users_r = await supa.table("users").select(
        "referrer_video_slug, referrer_video_title, subscription_tier"
    ).eq("referrer_source", "YouTube").execute()

    signup_counts: dict[str, dict] = {}
    for row in (users_r.data or []):
        slug = row.get("referrer_video_slug") or ""
        if not slug:
            continue
        if slug not in signup_counts:
            signup_counts[slug] = {"video_slug": slug, "video_title": row.get("referrer_video_title") or slug, "signups": 0, "premium": 0}
        signup_counts[slug]["signups"] += 1
        if row.get("subscription_tier") == "premium":
            signup_counts[slug]["premium"] += 1

    all_slugs = set(click_counts) | set(signup_counts)
    results = []
    for slug in all_slugs:
        cc = click_counts.get(slug, {})
        sc = signup_counts.get(slug, {})
        clicks = cc.get("clicks", 0)
        signups = sc.get("signups", 0)
        premium = sc.get("premium", 0)
        results.append({
            "video_slug": slug,
            "video_title": cc.get("video_title") or sc.get("video_title") or slug,
            "clicks": clicks,
            "signups": signups,
            "premium_subs": premium,
            "click_to_signup_rate": round(100.0 * signups / clicks, 1) if clicks else 0,
            "conversion_rate": round(100.0 * premium / signups, 1) if signups else 0,
            "mrr": premium * 10,
        })

    results.sort(key=lambda x: x["mrr"], reverse=True)
    return results


@router.get("/admin/referral/trends")
async def referral_trends(
    days: int = Query(30, ge=1, le=90),
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    clicks_r = await supa.table("referral_clicks").select("clicked_at").gte("clicked_at", since).execute()
    signups_r = await supa.table("users").select("created_at").eq("referrer_source", "YouTube").gte("created_at", since).execute()

    click_by_day: dict[str, int] = {}
    for row in (clicks_r.data or []):
        day = str(row["clicked_at"])[:10]
        click_by_day[day] = click_by_day.get(day, 0) + 1

    signup_by_day: dict[str, int] = {}
    for row in (signups_r.data or []):
        day = str(row["created_at"])[:10]
        signup_by_day[day] = signup_by_day.get(day, 0) + 1

    result = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": day, "clicks": click_by_day.get(day, 0), "signups": signup_by_day.get(day, 0)})

    return result
