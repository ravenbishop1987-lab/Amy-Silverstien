from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserProfile
from app.models.memory import LifeEvent, BehavioralPattern, Goal, Sensitivity, MemoryExtract, MemoryType
from app.models.conversation import Conversation
from app.utils.adult_filter import is_adult_language
from app.utils.rate_limiter import cache_get, cache_set, cache_delete


async def build_memory_context(user_id: UUID, db: AsyncSession) -> str:
    """Assemble all memory tiers into a formatted string for Claude's system prompt."""
    cache_key = f"memory_context:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    sections: list[str] = []

    # Tier 2: User profile
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = profile_result.scalar_one_or_none()
    if profile:
        facts = []
        if profile.preferred_name:
            facts.append(f"Name: {profile.preferred_name}")
        if profile.age:
            facts.append(f"Age: {profile.age}")
        if profile.relationship_status:
            facts.append(f"Relationship status: {profile.relationship_status}")
        if profile.adhd_severity:
            facts.append(f"ADHD severity (self-reported): {profile.adhd_severity}/10")
        if profile.attachment_style and profile.attachment_style != "unknown":
            facts.append(f"Attachment style: {profile.attachment_style}")
        if facts:
            sections.append("ABOUT THEM:\n" + "\n".join(f"- {f}" for f in facts))

    # Tier 3: Life events (most recent + highest weight)
    events_result = await db.execute(
        select(LifeEvent)
        .where(LifeEvent.user_id == user_id)
        .order_by(LifeEvent.emotional_weight.desc(), LifeEvent.created_at.desc())
        .limit(5)
    )
    events = events_result.scalars().all()
    if events:
        event_lines = []
        for e in events:
            processing = " (still processing)" if e.still_processing else ""
            event_lines.append(f"- [{e.event_type.value}] {e.description} (weight: {e.emotional_weight}/10){processing}")
        sections.append("KEY LIFE EVENTS:\n" + "\n".join(event_lines))

    # Tier 4: Behavioral patterns
    patterns_result = await db.execute(
        select(BehavioralPattern)
        .where(BehavioralPattern.user_id == user_id)
        .order_by(BehavioralPattern.importance_score.desc())
        .limit(5)
    )
    patterns = patterns_result.scalars().all()
    if patterns:
        pattern_lines = [f"- {p.pattern_name}: {p.description}" for p in patterns]
        sections.append("BEHAVIORAL PATTERNS:\n" + "\n".join(pattern_lines))

    # Tier 5: Goals and sensitivities
    goals_result = await db.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.achieved_date.is_(None)).limit(5)
    )
    goals = goals_result.scalars().all()
    if goals:
        sections.append("THEIR GOALS:\n" + "\n".join(f"- {g.goal_text}" for g in goals))

    sensitivities_result = await db.execute(
        select(Sensitivity).where(Sensitivity.user_id == user_id).limit(5)
    )
    sensitivities = sensitivities_result.scalars().all()
    if sensitivities:
        sens_lines = [f"- {s.topic}: {s.handling_notes or s.description}" for s in sensitivities]
        sections.append("HANDLE WITH CARE (sensitive topics):\n" + "\n".join(sens_lines))

    # Tier 6: Recent wins
    wins_result = await db.execute(
        select(MemoryExtract)
        .where(MemoryExtract.user_id == user_id, MemoryExtract.memory_type == MemoryType.win)
        .order_by(MemoryExtract.date_learned.desc())
        .limit(3)
    )
    wins = wins_result.scalars().all()
    if wins:
        sections.append("RECENT WINS (celebrate these!):\n" + "\n".join(f"- {w.content}" for w in wins))

    # Auto-extracted memories
    extracts_result = await db.execute(
        select(MemoryExtract)
        .where(
            MemoryExtract.user_id == user_id,
            MemoryExtract.memory_type != MemoryType.win,
        )
        .order_by(MemoryExtract.importance_score.desc(), MemoryExtract.date_learned.desc())
        .limit(15)
    )
    extracts = extracts_result.scalars().all()
    extract_lines: list[str] = []
    if extracts:
        extract_lines = [
            f"- [{e.memory_type.value}] {e.content}"
            for e in extracts
            if not is_adult_language(e.content)
        ]
    if extract_lines:
        sections.append("IMPORTANT CONTEXT FROM PAST CONVERSATIONS:\n" + "\n".join(extract_lines))

    # Recent conversation recall: this gives Amy continuity even before a
    # detail has been promoted into a long-term memory extract.
    recent_convos_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.date_started.desc())
        .limit(5)
    )
    recent_convos = recent_convos_result.scalars().all()
    recent_lines: list[str] = []
    low_signal = ("hello", "hi", "hey", "what's going on", "what did we talk about")
    for convo in recent_convos:
        messages = list(convo.messages or [])
        if not messages:
            continue
        title = convo.title or "Recent chat"
        user_turns = []
        for msg in messages:
            if msg.get("role") != "user" or not msg.get("content"):
                continue
            content = str(msg["content"]).strip()
            if is_adult_language(content):
                continue
            if len(content) < 20 and content.lower() in low_signal:
                continue
            user_turns.append(content)

        meaningful_turns = sorted(user_turns[-6:], key=len, reverse=True)[:3]
        if meaningful_turns:
            joined = " / ".join(turn[:300] for turn in meaningful_turns)
            recent_lines.append(f"- {title}: {joined}")
    if recent_lines:
        sections.append("RECENT CONVERSATION CONTINUITY:\n" + "\n".join(recent_lines[:8]))

    context = "\n\n".join(sections) if sections else ""
    await cache_set(cache_key, context, ttl_seconds=300)
    return context


async def save_extracted_memories(
    user_id: UUID,
    conversation_id: UUID,
    memories: list[dict],
    db: AsyncSession,
) -> None:
    """Persist auto-extracted memories from a conversation."""
    for mem in memories:
        content = str(mem.get("content", "")).strip()
        if not content or is_adult_language(content):
            continue

        existing_result = await db.execute(
            select(MemoryExtract).where(
                MemoryExtract.user_id == user_id,
                MemoryExtract.content == content,
            )
        )
        if existing_result.scalar_one_or_none():
            continue

        memory_type_str = mem.get("type", "insight")
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.insight

        extract = MemoryExtract(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            source_conversation_id=conversation_id,
            importance_score=min(10, max(1, int(mem.get("importance", 5)))),
            auto_extracted=True,
            date_learned=datetime.utcnow(),
        )
        db.add(extract)

    # Invalidate the memory context cache
    await cache_delete(f"memory_context:{user_id}")
    await db.flush()


async def increment_pattern_frequency(user_id: UUID, pattern_name: str, db: AsyncSession):
    """Increment the frequency counter for a detected behavioral pattern."""
    result = await db.execute(
        select(BehavioralPattern)
        .where(BehavioralPattern.user_id == user_id, BehavioralPattern.pattern_name == pattern_name)
    )
    pattern = result.scalar_one_or_none()
    if pattern:
        pattern.frequency_detected += 1
        pattern.last_triggered = datetime.utcnow()
    await cache_delete(f"memory_context:{user_id}")
