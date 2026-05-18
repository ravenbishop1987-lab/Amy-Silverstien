from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.memory import LifeEvent, BehavioralPattern, Goal, Sensitivity, MemoryExtract
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.user_id

    events = (await db.execute(select(LifeEvent).where(LifeEvent.user_id == uid).order_by(LifeEvent.created_at.desc()))).scalars().all()
    patterns = (await db.execute(select(BehavioralPattern).where(BehavioralPattern.user_id == uid).order_by(BehavioralPattern.importance_score.desc()))).scalars().all()
    goals = (await db.execute(select(Goal).where(Goal.user_id == uid).order_by(Goal.created_at.desc()))).scalars().all()
    sensitivities = (await db.execute(select(Sensitivity).where(Sensitivity.user_id == uid))).scalars().all()
    extracts = (await db.execute(select(MemoryExtract).where(MemoryExtract.user_id == uid).order_by(MemoryExtract.importance_score.desc(), MemoryExtract.date_learned.desc()).limit(50))).scalars().all()

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = LifeEvent(user_id=current_user.user_id, **data.model_dump())
    db.add(event)
    await db.flush()
    await cache_delete(f"memory_context:{current_user.user_id}")
    return event


@router.put("/events/{event_id}", response_model=LifeEventResponse)
async def update_life_event(
    event_id: UUID,
    data: LifeEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LifeEvent).where(LifeEvent.event_id == event_id, LifeEvent.user_id == current_user.user_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    for k, v in data.model_dump().items():
        setattr(event, k, v)
    await cache_delete(f"memory_context:{current_user.user_id}")
    return event


@router.delete("/events/{event_id}", status_code=204)
async def delete_life_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LifeEvent).where(LifeEvent.event_id == event_id, LifeEvent.user_id == current_user.user_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    await cache_delete(f"memory_context:{current_user.user_id}")


# ── Behavioral Patterns ────────────────────────────────────────────────────────

@router.post("/patterns", response_model=BehavioralPatternResponse, status_code=201)
async def create_pattern(
    data: BehavioralPatternCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = BehavioralPattern(user_id=current_user.user_id, **data.model_dump())
    db.add(pattern)
    await db.flush()
    await cache_delete(f"memory_context:{current_user.user_id}")
    return pattern


@router.delete("/patterns/{pattern_id}", status_code=204)
async def delete_pattern(
    pattern_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BehavioralPattern).where(BehavioralPattern.pattern_id == pattern_id, BehavioralPattern.user_id == current_user.user_id))
    pattern = result.scalar_one_or_none()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    await db.delete(pattern)
    await cache_delete(f"memory_context:{current_user.user_id}")


# ── Goals ──────────────────────────────────────────────────────────────────────

@router.post("/goals", response_model=GoalResponse, status_code=201)
async def create_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    goal = Goal(user_id=current_user.user_id, **data.model_dump())
    db.add(goal)
    await db.flush()
    await cache_delete(f"memory_context:{current_user.user_id}")
    return goal


@router.patch("/goals/{goal_id}/achieve", response_model=GoalResponse)
async def mark_goal_achieved(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.achieved_date = datetime.utcnow()
    await cache_delete(f"memory_context:{current_user.user_id}")
    return goal


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Goal).where(Goal.goal_id == goal_id, Goal.user_id == current_user.user_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await cache_delete(f"memory_context:{current_user.user_id}")


# ── Sensitivities ──────────────────────────────────────────────────────────────

@router.post("/sensitivities", response_model=SensitivityResponse, status_code=201)
async def create_sensitivity(
    data: SensitivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = Sensitivity(user_id=current_user.user_id, **data.model_dump())
    db.add(s)
    await db.flush()
    await cache_delete(f"memory_context:{current_user.user_id}")
    return s


@router.delete("/sensitivities/{sensitivity_id}", status_code=204)
async def delete_sensitivity(
    sensitivity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Sensitivity).where(Sensitivity.sensitivity_id == sensitivity_id, Sensitivity.user_id == current_user.user_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Sensitivity not found")
    await db.delete(s)
    await cache_delete(f"memory_context:{current_user.user_id}")


# ── Memory Extracts ────────────────────────────────────────────────────────────

@router.delete("/extracts/{memory_id}", status_code=204)
async def delete_memory_extract(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MemoryExtract).where(MemoryExtract.memory_id == memory_id, MemoryExtract.user_id == current_user.user_id))
    extract = result.scalar_one_or_none()
    if not extract:
        raise HTTPException(status_code=404, detail="Memory extract not found")
    await db.delete(extract)
    await cache_delete(f"memory_context:{current_user.user_id}")
