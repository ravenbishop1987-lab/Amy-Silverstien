import io
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
from app.utils.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_EMAILS = {"ravenbishop1987@gmail.com"}


def _require_admin(user: UserRecord):
    if user.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=7)).isoformat()
    month_start = (now - timedelta(days=30)).isoformat()

    # User counts
    total_r = await supa.table("users").select("*", count="exact").execute()
    free_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "free").execute()
    credits_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "credits").execute()
    premium_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "premium").execute()
    blocked_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "blocked").execute()

    # New users
    new_today_r = await supa.table("users").select("*", count="exact").gte("created_at", today_start).execute()
    new_week_r = await supa.table("users").select("*", count="exact").gte("created_at", week_start).execute()
    new_month_r = await supa.table("users").select("*", count="exact").gte("created_at", month_start).execute()

    # Conversation counts
    convos_total_r = await supa.table("conversations").select("*", count="exact").execute()
    convos_today_r = await supa.table("conversations").select("*", count="exact").gte("created_at", today_start).execute()
    convos_month_r = await supa.table("conversations").select("*", count="exact").gte("created_at", month_start).execute()

    # Safety flags
    flags_total_r = await supa.table("safety_flags").select("*", count="exact").execute()
    flags_open_r = await supa.table("safety_flags").select("*", count="exact").eq("resolved", False).execute()
    flags_tier2_r = await supa.table("safety_flags").select("*", count="exact").eq("risk_level", "tier2").eq("resolved", False).execute()
    flags_tier3_r = await supa.table("safety_flags").select("*", count="exact").eq("risk_level", "tier3").eq("resolved", False).execute()

    premium_count = premium_r.count or 0
    mrr = premium_count * 9.99

    return {
        "users": {
            "total": total_r.count or 0,
            "free": free_r.count or 0,
            "credits": credits_r.count or 0,
            "premium": premium_count,
            "blocked": blocked_r.count or 0,
            "new_today": new_today_r.count or 0,
            "new_week": new_week_r.count or 0,
            "new_month": new_month_r.count or 0,
        },
        "conversations": {
            "total": convos_total_r.count or 0,
            "today": convos_today_r.count or 0,
            "this_month": convos_month_r.count or 0,
        },
        "revenue": {
            "mrr": round(mrr, 2),
            "premium_subscribers": premium_count,
        },
        "safety": {
            "flags_total": flags_total_r.count or 0,
            "flags_open": flags_open_r.count or 0,
            "tier2_open": flags_tier2_r.count or 0,
            "tier3_open": flags_tier3_r.count or 0,
        },
    }


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_all_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    flagged_only: bool = False,
    user_id: Optional[str] = None,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    query = supa.table("conversations").select(
        "conversation_id,user_id,title,date_started,date_ended,duration_seconds,messages,created_at"
    ).order("created_at", desc=True).range(skip, skip + limit - 1)

    if user_id:
        query = query.eq("user_id", user_id)

    result = await query.execute()
    rows = result.data or []

    # If flagged_only, filter to conversations that have a safety flag
    if flagged_only:
        flags_r = await supa.table("safety_flags").select("conversation_id").eq("resolved", False).execute()
        flagged_ids = {f["conversation_id"] for f in (flags_r.data or []) if f.get("conversation_id")}
        rows = [r for r in rows if r["conversation_id"] in flagged_ids]

    # Enrich with user email and message count
    user_ids = list({r["user_id"] for r in rows})
    users_map: dict = {}
    if user_ids:
        users_r = await supa.table("users").select("user_id,email,subscription_tier").in_("user_id", user_ids).execute()
        users_map = {u["user_id"]: u for u in (users_r.data or [])}

    # Get flag info for these conversations
    convo_ids = [r["conversation_id"] for r in rows]
    flags_map: dict = {}
    if convo_ids:
        flags_r = await supa.table("safety_flags").select("conversation_id,risk_level,resolved,created_at").in_("conversation_id", convo_ids).order("created_at", desc=True).execute()
        for f in (flags_r.data or []):
            cid = f["conversation_id"]
            if cid not in flags_map:
                flags_map[cid] = f

    out = []
    for r in rows:
        msgs = r.get("messages") or []
        u = users_map.get(r["user_id"], {})
        flag = flags_map.get(r["conversation_id"])
        out.append({
            "conversation_id": r["conversation_id"],
            "user_id": r["user_id"],
            "user_email": u.get("email", "unknown"),
            "user_tier": u.get("subscription_tier", "free"),
            "title": r.get("title"),
            "date_started": r.get("date_started"),
            "date_ended": r.get("date_ended"),
            "message_count": len(msgs),
            "flagged": flag is not None,
            "flag_tier": flag["risk_level"] if flag else None,
            "flag_resolved": flag["resolved"] if flag else None,
        })

    return out


@router.get("/conversations/{conversation_id}")
async def get_conversation_admin(
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    r = await supa.table("conversations").select("*").eq("conversation_id", conversation_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="Not found")

    convo = r.data[0]
    user_r = await supa.table("users").select("email,subscription_tier").eq("user_id", convo["user_id"]).limit(1).execute()
    user_info = user_r.data[0] if user_r.data else {}

    flags_r = await supa.table("safety_flags").select("*").eq("conversation_id", conversation_id).order("created_at", desc=True).execute()

    return {
        **convo,
        "user_email": user_info.get("email"),
        "user_tier": user_info.get("subscription_tier"),
        "safety_flags": flags_r.data or [],
    }


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 50,
    tier: Optional[str] = None,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    query = supa.table("users").select(
        "user_id,email,subscription_tier,created_at,last_login,updated_at"
    ).order("created_at", desc=True).range(skip, skip + limit - 1)

    if tier:
        query = query.eq("subscription_tier", tier)

    result = await query.execute()
    users = result.data or []

    # Add conversation count for each user
    user_ids = [u["user_id"] for u in users]
    conv_counts: dict = {}
    if user_ids:
        for uid in user_ids:
            cr = await supa.table("conversations").select("*", count="exact").eq("user_id", uid).execute()
            conv_counts[uid] = cr.count or 0

    flag_counts: dict = {}
    if user_ids:
        for uid in user_ids:
            fr = await supa.table("safety_flags").select("*", count="exact").eq("user_id", uid).execute()
            flag_counts[uid] = fr.count or 0

    return [
        {
            "user_id": u["user_id"],
            "email": u["email"],
            "tier": u["subscription_tier"],
            "created_at": u["created_at"],
            "last_login": u.get("last_login"),
            "conversation_count": conv_counts.get(u["user_id"], 0),
            "flag_count": flag_counts.get(u["user_id"], 0),
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user_admin(
    user_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    r = await supa.table("users").select("*").eq("user_id", user_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = r.data[0]
    convos_r = await supa.table("conversations").select("conversation_id,title,date_started,messages").eq("user_id", user_id).order("date_started", desc=True).limit(20).execute()
    flags_r = await supa.table("safety_flags").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

    convos = [
        {
            "conversation_id": c["conversation_id"],
            "title": c.get("title"),
            "date_started": c["date_started"],
            "message_count": len(c.get("messages") or []),
        }
        for c in (convos_r.data or [])
    ]

    return {
        **user,
        "conversations": convos,
        "safety_flags": flags_r.data or [],
    }


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    r = await supa.table("users").select("user_id").eq("user_id", user_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="User not found")

    await supa.table("users").update({"subscription_tier": "blocked"}).eq("user_id", user_id).execute()
    return {"status": "blocked", "user_id": user_id}


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    r = await supa.table("users").select("user_id").eq("user_id", user_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="User not found")

    await supa.table("users").update({"subscription_tier": "free"}).eq("user_id", user_id).execute()
    return {"status": "unblocked", "user_id": user_id}


@router.delete("/users/{user_id}")
async def delete_user_data(
    user_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    r = await supa.table("users").select("user_id").eq("user_id", user_id).limit(1).execute()
    if not r.data:
        raise HTTPException(status_code=404, detail="User not found")

    # CASCADE on delete will remove related rows
    await supa.table("users").delete().eq("user_id", user_id).execute()
    return {"status": "deleted", "user_id": user_id}


# ── Moderation ────────────────────────────────────────────────────────────────

@router.get("/moderation/flags")
async def get_flags(
    skip: int = 0,
    limit: int = 50,
    resolved: Optional[bool] = None,
    tier: Optional[str] = None,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    query = supa.table("safety_flags").select("*").order("created_at", desc=True).range(skip, skip + limit - 1)

    if resolved is not None:
        query = query.eq("resolved", resolved)
    if tier:
        query = query.eq("risk_level", tier)

    result = await query.execute()
    flags = result.data or []

    # Enrich with user email and conversation snippet
    user_ids = list({f["user_id"] for f in flags if f.get("user_id")})
    users_map: dict = {}
    if user_ids:
        ur = await supa.table("users").select("user_id,email").in_("user_id", user_ids).execute()
        users_map = {u["user_id"]: u["email"] for u in (ur.data or [])}

    convo_ids = list({f["conversation_id"] for f in flags if f.get("conversation_id")})
    convos_map: dict = {}
    if convo_ids:
        cr = await supa.table("conversations").select("conversation_id,messages").in_("conversation_id", convo_ids).execute()
        for c in (cr.data or []):
            msgs = c.get("messages") or []
            # Get last few user messages as snippet
            user_msgs = [m for m in msgs if m.get("role") == "user"]
            snippet = user_msgs[-1]["content"][:200] if user_msgs else ""
            convos_map[c["conversation_id"]] = snippet

    return [
        {
            **f,
            "user_email": users_map.get(f.get("user_id", ""), "unknown"),
            "conversation_snippet": convos_map.get(f.get("conversation_id", ""), ""),
        }
        for f in flags
    ]


@router.get("/revenue/breakdown")
async def get_revenue_breakdown(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    # ── Subscriptions ──────────────────────────────────────
    premium_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "premium").execute()
    premium_count = premium_r.count or 0

    # ── Credits users ──────────────────────────────────────
    credits_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "credits").execute()
    credits_count = credits_r.count or 0
    # Each credits user bought the bulk pack ($2.99) at minimum
    credits_revenue = round(credits_count * 2.99, 2)

    # ── Gifts ─────────────────────────────────────────────
    GIFT_PRICES = {
        "rose": 2.99,
        "sweet note": 1.99,
        "kiss": 1.49,
        "hug": 1.49,
        "smile": 0.99,
    }

    # Messages with gift_session_id are gift transactions
    convos_r = await supa.table("conversations").select("messages").execute()
    gift_counts: dict = {k: 0 for k in GIFT_PRICES}
    gift_total = 0.0

    for convo in (convos_r.data or []):
        for msg in (convo.get("messages") or []):
            if not isinstance(msg, dict):
                continue
            if not msg.get("gift_session_id"):
                continue
            if msg.get("role") != "user":
                continue
            content = (msg.get("content") or "").lower()
            for label, price in GIFT_PRICES.items():
                if label in content:
                    gift_counts[label] = gift_counts.get(label, 0) + 1
                    gift_total += price
                    break

    gift_breakdown = [
        {"label": label.title(), "count": count, "revenue": round(count * GIFT_PRICES[label], 2)}
        for label, count in gift_counts.items()
        if count > 0
    ]

    return {
        "subscriptions": {
            "count": premium_count,
            "revenue": round(premium_count * 9.99, 2),
            "mrr": round(premium_count * 9.99, 2),
        },
        "credits": {
            "count": credits_count,
            "revenue": credits_revenue,
        },
        "gifts": {
            "total_revenue": round(gift_total, 2),
            "total_count": sum(gift_counts.values()),
            "breakdown": gift_breakdown,
        },
        "total_estimated_revenue": round(premium_count * 9.99 + credits_revenue + gift_total, 2),
    }


@router.get("/revenue")
async def get_revenue(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    import asyncio
    import stripe as _stripe
    from app.config import settings as _settings

    _stripe.api_key = _settings.STRIPE_SECRET_KEY

    if not _settings.STRIPE_SECRET_KEY:
        return {
            "mrr": 0, "premium_subscribers": 0, "revenue_today": 0,
            "revenue_month": 0, "revenue_alltime": 0, "recent_transactions": [],
            "error": "STRIPE_SECRET_KEY not configured",
        }

    now = datetime.utcnow()
    month_start_ts = int(datetime(now.year, now.month, 1).timestamp())
    today_start_ts = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    def _fetch_stripe_data():
        charges_month = _stripe.Charge.list(limit=100, created={"gte": month_start_ts})
        charges_today = _stripe.Charge.list(limit=100, created={"gte": today_start_ts})
        charges_all = _stripe.Charge.list(limit=100)
        return charges_month, charges_today, charges_all, None

    # Get subscriber count from Supabase (source of truth)
    premium_r = await supa.table("users").select("*", count="exact").eq("subscription_tier", "premium").execute()
    sub_count = premium_r.count or 0

    try:
        loop = asyncio.get_event_loop()
        charges_month, charges_today, charges_all, _ = await loop.run_in_executor(None, _fetch_stripe_data)

        def sum_paid(charge_list) -> float:
            return round(sum(
                c["amount"] / 100.0
                for c in (charge_list.data or [])
                if c.get("paid") and not c.get("refunded")
            ), 2)

        recent = []
        for c in (charges_month.data or [])[:20]:
            if c.get("paid") and not c.get("refunded"):
                recent.append({
                    "id": c["id"],
                    "amount": c["amount"] / 100.0,
                    "date": datetime.utcfromtimestamp(c["created"]).isoformat(),
                    "description": c.get("description") or c.get("calculated_statement_descriptor") or "Payment",
                    "customer_email": (c.get("billing_details") or {}).get("email") or "",
                })

        return {
            "mrr": round(sub_count * 9.99, 2),
            "premium_subscribers": sub_count,
            "revenue_today": sum_paid(charges_today),
            "revenue_month": sum_paid(charges_month),
            "revenue_alltime": sum_paid(charges_all),
            "recent_transactions": recent,
        }
    except Exception as e:
        return {
            "mrr": round(sub_count * 9.99, 2),
            "premium_subscribers": sub_count,
            "revenue_today": 0,
            "revenue_month": 0,
            "revenue_alltime": 0,
            "recent_transactions": [],
            "error": f"{type(e).__name__}: {e}",
        }


@router.post("/moderation/flags/{flag_id}/resolve")
async def resolve_flag(
    flag_id: str,
    notes: str = "",
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    await supa.table("safety_flags").update({
        "resolved": True,
        "resolved_at": datetime.utcnow().isoformat(),
        "response_mode": notes or "reviewed",
    }).eq("flag_id", flag_id).execute()

    return {"status": "resolved", "flag_id": flag_id}


# ── PDF Export ────────────────────────────────────────────────────────────────

def _build_moderation_pdf(flags: list, date_label: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Sophie Parker — Moderation Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Period: {date_label}", ln=True)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
    pdf.ln(4)

    # Summary
    t1 = sum(1 for f in flags if f.get("risk_level") == "tier1")
    t2 = sum(1 for f in flags if f.get("risk_level") == "tier2")
    t3 = sum(1 for f in flags if f.get("risk_level") == "tier3")
    resolved = sum(1 for f in flags if f.get("resolved"))

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for label, val in [
        ("Total flags", len(flags)),
        ("Tier 1 (Ideation)", t1),
        ("Tier 2 (Active self-harm)", t2),
        ("Tier 3 (Emergency)", t3),
        ("Resolved", resolved),
        ("Pending review", len(flags) - resolved),
    ]:
        pdf.cell(0, 7, f"  {label}: {val}", ln=True)
    pdf.ln(4)

    # Detailed flags
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Flag Details", ln=True)
    pdf.set_font("Helvetica", "", 10)

    for f in flags:
        tier = f.get("risk_level", "unknown").upper()
        ts = f.get("created_at", "")[:16].replace("T", " ")
        user = f.get("user_email", f.get("user_id", "unknown"))
        trigger = (f.get("trigger_text") or "")[:120]
        status = "Resolved" if f.get("resolved") else "Pending"
        notes = (f.get("response_mode") or "")[:80]

        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"[{tier}] {ts} — {user}", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 10)
        if trigger:
            # safe_encode to latin-1
            safe = trigger.encode("latin-1", errors="replace").decode("latin-1")
            pdf.cell(0, 6, f'  Trigger: "{safe}"', ln=True)
        pdf.cell(0, 6, f"  Status: {status}  |  Action: {f.get('response_mode', 'safety_first')}", ln=True)
        if notes and notes != "safety_first":
            safe_notes = notes.encode("latin-1", errors="replace").decode("latin-1")
            pdf.cell(0, 6, f"  Notes: {safe_notes}", ln=True)
        pdf.ln(2)

    # Footer
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 6, "This report is for internal use only. Retain for legal compliance.", ln=True)
    pdf.cell(0, 6, "Crisis resources: 988 Suicide & Crisis Lifeline | Text HOME to 741741", ln=True)

    return bytes(pdf.output())


@router.get("/export/moderation-report")
async def export_moderation_report(
    days: int = Query(30, ge=1, le=365),
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    flags_r = await supa.table("safety_flags").select("*").gte("created_at", since).order("created_at", desc=True).execute()
    flags = flags_r.data or []

    # Enrich with emails
    user_ids = list({f["user_id"] for f in flags if f.get("user_id")})
    users_map: dict = {}
    if user_ids:
        ur = await supa.table("users").select("user_id,email").in_("user_id", user_ids).execute()
        users_map = {u["user_id"]: u["email"] for u in (ur.data or [])}
    for f in flags:
        f["user_email"] = users_map.get(f.get("user_id", ""), "unknown")

    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    date_label = f"Last {days} days (since {since[:10]})"
    pdf_bytes = await loop.run_in_executor(None, _build_moderation_pdf, flags, date_label)

    filename = f"Sophie_Moderation_Report_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/conversation/{conversation_id}")
async def export_conversation_pdf(
    conversation_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    _require_admin(current_user)

    convo_r = await supa.table("conversations").select("*").eq("conversation_id", conversation_id).limit(1).execute()
    if not convo_r.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo = convo_r.data[0]

    user_r = await supa.table("users").select("email").eq("user_id", convo["user_id"]).limit(1).execute()
    user_email = user_r.data[0]["email"] if user_r.data else "unknown"

    flags_r = await supa.table("safety_flags").select("*").eq("conversation_id", conversation_id).execute()
    flags = flags_r.data or []

    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Conversation Export — Sophie Parker", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"User: {user_email}", ln=True)
    pdf.cell(0, 6, f"Conversation ID: {conversation_id}", ln=True)
    pdf.cell(0, 6, f"Started: {str(convo.get('date_started', ''))[:16]}", ln=True)
    pdf.cell(0, 6, f"Safety flags: {len(flags)}", ln=True)
    pdf.ln(4)

    flagged_msg_ids = {f.get("trigger_text", "") for f in flags}

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Conversation Thread", ln=True)

    for msg in (convo.get("messages") or []):
        role = msg.get("role", "unknown")
        content = (msg.get("content") or "")[:800]
        ts = str(msg.get("timestamp", ""))[:16].replace("T", " ")
        safe_content = content.encode("latin-1", errors="replace").decode("latin-1")

        pdf.set_font("Helvetica", "B", 10)
        label = "User" if role == "user" else "Sophie"
        pdf.set_fill_color(230, 240, 255) if role == "user" else pdf.set_fill_color(245, 245, 245)
        pdf.cell(0, 6, f"{label} [{ts}]", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, safe_content)
        pdf.ln(2)

    if flags:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Moderation Flags", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for f in flags:
            tier = f.get("risk_level", "unknown").upper()
            trigger = (f.get("trigger_text") or "")[:120]
            safe_t = trigger.encode("latin-1", errors="replace").decode("latin-1")
            pdf.cell(0, 6, f"[{tier}] Trigger: \"{safe_t}\"", ln=True)
            pdf.cell(0, 6, f"  Status: {'Resolved' if f.get('resolved') else 'Pending'}", ln=True)
            pdf.ln(2)

    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 6, "Internal use only. Sophie Parker AI companion moderation log.", ln=True)

    pdf_bytes = bytes(pdf.output())
    filename = f"Conversation_{conversation_id[:8]}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
