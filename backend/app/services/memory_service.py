import uuid
from uuid import UUID
from datetime import datetime
from supabase import AsyncClient
from app.models.memory import MemoryType
from app.utils.adult_filter import is_adult_language
from app.utils.rate_limiter import cache_get, cache_set, cache_delete


async def build_memory_context(user_id: UUID, supa: AsyncClient) -> str:
    """Assemble all memory tiers into a formatted string for Claude's system prompt."""
    cache_key = f"memory_context:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    uid = str(user_id)
    sections: list[str] = []

    # Tier 2: User profile
    profile_r = await supa.table("user_profiles").select("*").eq("user_id", uid).limit(1).execute()
    profile = profile_r.data[0] if profile_r and profile_r.data else None
    if profile:
        facts = []
        if profile.get("preferred_name"):
            facts.append(f"Name: {profile['preferred_name']}")
        if profile.get("age"):
            facts.append(f"Age: {profile['age']}")
        if profile.get("relationship_status"):
            facts.append(f"Relationship status: {profile['relationship_status']}")
        if profile.get("adhd_severity"):
            facts.append(f"ADHD severity (self-reported): {profile['adhd_severity']}/10")
        style = profile.get("attachment_style", "unknown")
        if style and style != "unknown":
            facts.append(f"Attachment style: {style}")
        if facts:
            sections.append("ABOUT THEM:\n" + "\n".join(f"- {f}" for f in facts))

    # Tier 3: Life events (highest weight, most recent)
    events_r = await supa.table("life_events").select("*").eq("user_id", uid).order("emotional_weight", desc=True).order("created_at", desc=True).limit(5).execute()
    events = events_r.data or []
    if events:
        event_lines = []
        for e in events:
            processing = " (still processing)" if e.get("still_processing") else ""
            event_lines.append(f"- [{e['event_type']}] {e['description']} (weight: {e['emotional_weight']}/10){processing}")
        sections.append("KEY LIFE EVENTS:\n" + "\n".join(event_lines))

    # Tier 4: Behavioral patterns
    patterns_r = await supa.table("behavioral_patterns").select("*").eq("user_id", uid).order("importance_score", desc=True).limit(5).execute()
    patterns = patterns_r.data or []
    if patterns:
        sections.append("BEHAVIORAL PATTERNS:\n" + "\n".join(f"- {p['pattern_name']}: {p['description']}" for p in patterns))

    # Tier 5: Goals (unachieved) and sensitivities
    goals_r = await supa.table("goals").select("*").eq("user_id", uid).is_("achieved_date", "null").limit(5).execute()
    goals = goals_r.data or []
    if goals:
        sections.append("THEIR GOALS:\n" + "\n".join(f"- {g['goal_text']}" for g in goals))

    sens_r = await supa.table("sensitivities").select("*").eq("user_id", uid).limit(5).execute()
    sensitivities = sens_r.data or []
    if sensitivities:
        sens_lines = [f"- {s['topic']}: {s.get('handling_notes') or s['description']}" for s in sensitivities]
        sections.append("HANDLE WITH CARE (sensitive topics):\n" + "\n".join(sens_lines))

    # Tier 6: Recent wins
    wins_r = await supa.table("memory_extracts").select("*").eq("user_id", uid).eq("memory_type", MemoryType.win.value).order("date_learned", desc=True).limit(3).execute()
    wins = wins_r.data or []
    if wins:
        sections.append("RECENT WINS (celebrate these!):\n" + "\n".join(f"- {w['content']}" for w in wins))

    # Auto-extracted memories (non-wins), highest importance first
    extracts_r = await supa.table("memory_extracts").select("*").eq("user_id", uid).neq("memory_type", MemoryType.win.value).order("importance_score", desc=True).order("date_learned", desc=True).limit(15).execute()
    extracts = extracts_r.data or []
    extract_lines = [
        f"- [{e['memory_type']}] {e['content']}"
        for e in extracts
        if not is_adult_language(e["content"])
    ]
    if extract_lines:
        sections.append("IMPORTANT CONTEXT FROM PAST CONVERSATIONS:\n" + "\n".join(extract_lines))

    # Advanced emotional pattern memory
    try:
        emotional_r = await supa.table("emotional_patterns").select("*").eq("user_id", uid).order("seen_count", desc=True).order("last_seen", desc=True).limit(8).execute()
        emotional_patterns = emotional_r.data or []
    except Exception:
        emotional_patterns = []
    if emotional_patterns:
        lines = []
        for pattern in emotional_patterns:
            response = pattern.get("recommended_response") or "validate first, then reality-check gently"
            lines.append(f"- {pattern.get('pattern')} (seen {pattern.get('seen_count', 1)}x): {response}")
        sections.append("LONG-TERM EMOTIONAL PATTERNS:\n" + "\n".join(lines))

    # Advice history so Amy can go deeper instead of restarting
    try:
        advice_r = await supa.table("advice_history").select("*").eq("user_id", uid).order("date_given", desc=True).limit(12).execute()
        advice_history = advice_r.data or []
    except Exception:
        advice_history = []
    if advice_history:
        lines = []
        for advice in advice_history:
            lines.append(
                f"- {advice.get('topic')}: {advice.get('advice_summary')} "
                f"(reaction: {advice.get('user_reaction') or 'unknown'}, effectiveness: {advice.get('effectiveness') or 'unknown'})"
            )
        sections.append("ADVICE ALREADY GIVEN (avoid repeating wording; build on it):\n" + "\n".join(lines))

    # Relationship entity memory
    try:
        people_r = await supa.table("relationship_entities").select("*").eq("user_id", uid).order("updated_at", desc=True).limit(10).execute()
        people = people_r.data or []
    except Exception:
        people = []
    if people:
        lines = []
        for person in people:
            assessment = person.get("amy_assessment") or {}
            guidance = assessment.get("recommended_guidance") or "watch consistency and protect the user's self-worth"
            lines.append(
                f"- {person.get('name_or_label')} ({person.get('relationship_to_user')}, {person.get('current_status')}): "
                f"{person.get('summary')} Guidance: {guidance}"
            )
        sections.append("PEOPLE THEY TALK ABOUT:\n" + "\n".join(lines))

    # Communication preferences and sensitivities that do not fit older profile columns
    try:
        prefs_r = await supa.table("user_preferences").select("*").eq("user_id", uid).limit(1).execute()
        prefs = prefs_r.data[0] if prefs_r and prefs_r.data else None
    except Exception:
        prefs = None
    if prefs:
        sections.append(
            "HOW TO TALK TO THEM:\n"
            f"- Responds to: {', '.join(prefs.get('responds_to') or [])}\n"
            f"- Avoids: {', '.join(prefs.get('avoids') or [])}\n"
            f"- Preferred length: {prefs.get('preferred_length') or 'medium'}\n"
            f"- Preferred tone: {prefs.get('preferred_tone') or 'girl-next-door'}"
        )

    # Recent conversation continuity
    convos_r = await supa.table("conversations").select("title,messages").eq("user_id", uid).order("date_started", desc=True).limit(5).execute()
    recent_convos = convos_r.data or []
    recent_lines: list[str] = []
    low_signal = ("hello", "hi", "hey", "what's going on", "what did we talk about")
    for convo in recent_convos:
        messages = convo.get("messages") or []
        if not messages:
            continue
        title = convo.get("title") or "Recent chat"
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
    conversation_id: str,
    memories: list[dict],
    supa: AsyncClient,
) -> None:
    """Persist auto-extracted memories from a conversation."""
    uid = str(user_id)
    now = datetime.utcnow().isoformat()

    for mem in memories:
        content = str(mem.get("content", "")).strip()
        if not content or is_adult_language(content):
            continue

        existing = await supa.table("memory_extracts").select("memory_id").eq("user_id", uid).eq("content", content).limit(1).execute()
        if existing and existing.data:
            continue

        memory_type_str = mem.get("type", "insight")
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.insight

        await supa.table("memory_extracts").insert({
            "memory_id": str(uuid.uuid4()),
            "user_id": uid,
            "memory_type": memory_type.value,
            "content": content,
            "source_conversation_id": conversation_id,
            "importance_score": min(10, max(1, int(mem.get("importance", 5)))),
            "auto_extracted": True,
            "date_learned": now,
            "created_at": now,
        }).execute()

    await cache_delete(f"memory_context:{user_id}")
