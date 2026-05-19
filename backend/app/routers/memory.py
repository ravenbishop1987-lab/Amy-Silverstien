import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient
from app.database import get_supabase
from app.models.user import UserRecord
from app.models.memory import MemoryType
from app.schemas.memory import (
    LifeEventCreate, LifeEventResponse,
    BehavioralPatternCreate, BehavioralPatternResponse,
    GoalCreate, GoalResponse,
    SensitivityCreate, SensitivityResponse,
    MemoryExtractResponse, MemoryBankResponse,
)
from app.utils.auth import get_current_user
from app.utils.rate_limiter import cache_delete

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryBankResponse)
async def get_memory_bank(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)

    events = (await supa.table("life_events").select("*").eq("user_id", uid).order("created_at", desc=True).execute()).data or []
    patterns = (await supa.table("behavioral_patterns").select("*").eq("user_id", uid).order("importance_score", desc=True).execute()).data or []
    goals = (await supa.table("goals").select("*").eq("user_id", uid).order("created_at", desc=True).execute()).data or []
    sensitivities = (await supa.table("sensitivities").select("*").eq("user_id", uid).execute()).data or []
    extracts = (await supa.table("memory_extracts").select("*").eq("user_id", uid).order("importance_score", desc=True).order("date_learned", desc=True).limit(50).execute()).data or []

    return MemoryBankResponse(
        life_events=events,
        behavioral_patterns=patterns,
        goals=goals,
        sensitivities=sensitivities,
        memory_extracts=extracts,
    )


# ── Life Events ────────────────────────────────────────────────────────────────

@router.post("/events", response_model=LifeEventResponse, status_code=201)
async def create_life_event(
    data: LifeEventCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    now = datetime.utcnow().isoformat()
    row = {
        "event_id": str(uuid.uuid4()),
        "user_id": uid,
        "event_type": data.event_type.value,
        "description": data.description,
        "date_occurred": data.date_occurred.isoformat() if data.date_occurred else None,
        "emotional_weight": data.emotional_weight,
        "still_processing": data.still_processing,
        "created_at": now,
    }
    result = await supa.table("life_events").insert(row).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else row


@router.put("/events/{event_id}", response_model=LifeEventResponse)
async def update_life_event(
    event_id: str,
    data: LifeEventCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("life_events").select("event_id").eq("event_id", event_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Event not found")

    update = {
        "event_type": data.event_type.value,
        "description": data.description,
        "date_occurred": data.date_occurred.isoformat() if data.date_occurred else None,
        "emotional_weight": data.emotional_weight,
        "still_processing": data.still_processing,
    }
    result = await supa.table("life_events").update(update).eq("event_id", event_id).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else existing.data


@router.delete("/events/{event_id}", status_code=204)
async def delete_life_event(
    event_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("life_events").select("event_id").eq("event_id", event_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Event not found")
    await supa.table("life_events").delete().eq("event_id", event_id).execute()
    await cache_delete(f"memory_context:{uid}")


# ── Behavioral Patterns ────────────────────────────────────────────────────────

@router.post("/patterns", response_model=BehavioralPatternResponse, status_code=201)
async def create_pattern(
    data: BehavioralPatternCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    now = datetime.utcnow().isoformat()
    row = {
        "pattern_id": str(uuid.uuid4()),
        "user_id": uid,
        "pattern_name": data.pattern_name,
        "description": data.description,
        "context": data.context,
        "importance_score": data.importance_score,
        "frequency_detected": 1,
        "created_at": now,
    }
    result = await supa.table("behavioral_patterns").insert(row).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else row


@router.delete("/patterns/{pattern_id}", status_code=204)
async def delete_pattern(
    pattern_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("behavioral_patterns").select("pattern_id").eq("pattern_id", pattern_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Pattern not found")
    await supa.table("behavioral_patterns").delete().eq("pattern_id", pattern_id).execute()
    await cache_delete(f"memory_context:{uid}")


# ── Goals ──────────────────────────────────────────────────────────────────────

@router.post("/goals", response_model=GoalResponse, status_code=201)
async def create_goal(
    data: GoalCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    now = datetime.utcnow().isoformat()
    row = {
        "goal_id": str(uuid.uuid4()),
        "user_id": uid,
        "goal_text": data.goal_text,
        "category": data.category.value,
        "created_at": now,
    }
    result = await supa.table("goals").insert(row).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else row


@router.patch("/goals/{goal_id}/achieve", response_model=GoalResponse)
async def mark_goal_achieved(
    goal_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("goals").select("goal_id").eq("goal_id", goal_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Goal not found")
    result = await supa.table("goals").update({"achieved_date": datetime.utcnow().isoformat()}).eq("goal_id", goal_id).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else existing.data


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("goals").select("goal_id").eq("goal_id", goal_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Goal not found")
    await supa.table("goals").delete().eq("goal_id", goal_id).execute()
    await cache_delete(f"memory_context:{uid}")


# ── Sensitivities ──────────────────────────────────────────────────────────────

@router.post("/sensitivities", response_model=SensitivityResponse, status_code=201)
async def create_sensitivity(
    data: SensitivityCreate,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    row = {
        "sensitivity_id": str(uuid.uuid4()),
        "user_id": uid,
        "topic": data.topic,
        "description": data.description,
        "handling_notes": data.handling_notes,
    }
    result = await supa.table("sensitivities").insert(row).execute()
    await cache_delete(f"memory_context:{uid}")
    return result.data[0] if result.data else row


@router.delete("/sensitivities/{sensitivity_id}", status_code=204)
async def delete_sensitivity(
    sensitivity_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("sensitivities").select("sensitivity_id").eq("sensitivity_id", sensitivity_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Sensitivity not found")
    await supa.table("sensitivities").delete().eq("sensitivity_id", sensitivity_id).execute()
    await cache_delete(f"memory_context:{uid}")


# ── Memory Extracts ────────────────────────────────────────────────────────────

@router.delete("/extracts/{memory_id}", status_code=204)
async def delete_memory_extract(
    memory_id: str,
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    existing = await supa.table("memory_extracts").select("memory_id").eq("memory_id", memory_id).eq("user_id", uid).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Memory extract not found")
    await supa.table("memory_extracts").delete().eq("memory_id", memory_id).execute()
    await cache_delete(f"memory_context:{uid}")


@router.delete("/extracts", status_code=204)
async def clear_all_memory_extracts(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    await supa.table("memory_extracts").delete().eq("user_id", uid).execute()
    await cache_delete(f"memory_context:{uid}")


@router.delete("/all", status_code=204)
async def clear_all_memory(
    current_user: UserRecord = Depends(get_current_user),
    supa: AsyncClient = Depends(get_supabase),
):
    uid = str(current_user.user_id)
    await supa.table("memory_extracts").delete().eq("user_id", uid).execute()
    await supa.table("life_events").delete().eq("user_id", uid).execute()
    await supa.table("behavioral_patterns").delete().eq("user_id", uid).execute()
    await supa.table("goals").delete().eq("user_id", uid).execute()
    await supa.table("sensitivities").delete().eq("user_id", uid).execute()
    await cache_delete(f"memory_context:{uid}")
