import re
import uuid
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from supabase import AsyncClient

from app.utils.adult_filter import is_adult_language
from app.utils.rate_limiter import cache_delete


MOODS = {
    "sad": ("sad", "hurt", "heartbroken", "cry", "crying", "miss"),
    "happy": ("happy", "good", "great", "proud", "relieved"),
    "angry": ("angry", "mad", "furious", "pissed", "annoyed"),
    "confused": ("confused", "mixed signals", "don't know", "idk", "unclear"),
    "hopeful": ("hopeful", "maybe", "excited", "could work"),
    "lonely": ("lonely", "alone", "nobody", "isolated"),
    "anxious": ("anxious", "panic", "spiral", "overthink", "worried", "scared"),
    "excited": ("excited", "can't wait", "butterflies", "amazing"),
}

TOPICS = {
    "ghosting": ("ghost", "left on read", "not replying", "didn't reply", "no response"),
    "dating": ("date", "dating", "crush", "talking stage", "texting", "boyfriend", "girlfriend"),
    "breakup": ("breakup", "broke up", "dumped", "ex", "heartbreak"),
    "self-worth": ("not enough", "too much", "worth", "ugly", "unlovable"),
    "ADHD": ("adhd", "focus", "executive", "procrastinate", "rsd"),
    "loneliness": ("lonely", "alone", "no friends"),
    "conflict": ("fight", "argument", "mad at me", "conflict"),
    "anxiety": ("anxious", "panic", "spiral", "worried", "overthink"),
}

RELATIONSHIP_CONTEXT = {
    "crush": ("crush", "talking stage", "guy", "girl", "person i'm seeing"),
    "ex": ("ex", "my ex", "old boyfriend", "old girlfriend"),
    "partner": ("partner", "boyfriend", "girlfriend", "husband", "wife"),
    "friend": ("friend", "bestie"),
    "family": ("mom", "dad", "sister", "brother", "parent", "family"),
    "work": ("boss", "coworker", "work", "job"),
}

CRISIS_SIGNALS = (
    "kill myself", "end my life", "suicide", "self harm", "hurt myself",
    "he hit me", "she hit me", "abuse", "stalking", "stalker", "threatened me",
    "not safe", "danger", "coerced", "forced me",
)

ADVICE_TOPICS = {
    "texting": ("text", "message", "reply", "respond", "send"),
    "boundaries": ("boundary", "boundaries", "space", "no contact"),
    "self_worth": ("worth", "deserve", "enough", "too much"),
    "emotional_regulation": ("breathe", "ground", "slow down", "nervous system", "body"),
    "clarity": ("clarity", "ask", "honest conversation", "communicate"),
    "red_flags": ("red flag", "inconsistent", "hot and cold", "actions"),
}

FLIRT_MODE_LABELS = {
    0: "supportive only",
    1: "warm and friendly",
    2: "light teasing",
    3: "emotionally intimate",
    4: "playfully suggestive",
}

FLIRT_POSITIVE_SIGNALS = (
    "flirt", "tease me", "be playful", "call me", "cute", "you like me",
    "i like when you", "keep talking like that", "pet name", "sweetheart",
    "babe", "baby", "romantic", "make me blush",
)

FLIRT_NEGATIVE_SIGNALS = (
    "don't flirt", "dont flirt", "stop flirting", "too much", "creepy",
    "uncomfortable", "don't call me", "dont call me", "no pet names",
)


def _contains_any(text: str, signals: tuple[str, ...]) -> bool:
    return any(signal in text for signal in signals)


def _first_match(mapping: dict[str, tuple[str, ...]], text: str, default: str) -> str:
    for label, signals in mapping.items():
        if _contains_any(text, signals):
            return label
    return default


def _all_matches(mapping: dict[str, tuple[str, ...]], text: str) -> list[str]:
    return [label for label, signals in mapping.items() if _contains_any(text, signals)]


def _message_content(message: dict[str, Any]) -> str:
    return str(message.get("content") or "").strip()


def _summarize(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def analyze_current_message(user_message: str) -> dict[str, Any]:
    lower = user_message.lower()
    questiony = "?" in user_message or lower.startswith(("what", "how", "why", "should", "do i", "can i"))
    asks_advice = questiony or _contains_any(lower, ("advice", "what do i do", "should i", "help me"))
    crisis = _contains_any(lower, CRISIS_SIGNALS)
    anxious_count = sum(1 for word in ("panic", "spiral", "can't breathe", "freaking out", "right now") if word in lower)
    emotional_intensity = "high" if crisis or anxious_count or len(re.findall(r"[!?]", user_message)) >= 3 else "medium"
    if len(user_message) < 80 and not anxious_count and not crisis:
        emotional_intensity = "low"

    intent = "venting"
    if crisis:
        intent = "crisis"
    elif _contains_any(lower, ("flirt", "cute", "hot", "do you like me")):
        intent = "flirting"
    elif asks_advice:
        intent = "advice"
    elif _contains_any(lower, ("comfort", "reassure", "tell me i'm", "i need you")):
        intent = "comfort"
    elif _contains_any(lower, ("confused", "clarity", "mixed signals", "what does it mean")):
        intent = "clarity"

    hidden_need = "validation"
    if _contains_any(lower, ("should i", "is it okay", "can i")):
        hidden_need = "permission"
    elif _contains_any(lower, ("what do i do", "how do i", "advice")):
        hidden_need = "strategy"
    elif _contains_any(lower, ("panic", "spiral", "can't stop", "calm")):
        hidden_need = "calming"
    elif _contains_any(lower, ("does he", "does she", "am i", "do they")):
        hidden_need = "reassurance"

    mood = _first_match(MOODS, lower, "confused" if questiony else "sad")
    topics = _all_matches(TOPICS, lower)
    relationship_context = _first_match(RELATIONSHIP_CONTEXT, lower, "self")
    flirt_mode = _flirt_mode_for(lower, intent, mood, emotional_intensity, crisis)

    return {
        "user_intent": intent,
        "emotional_intensity": emotional_intensity,
        "main_topic": topics[0] if topics else "self",
        "topics_mentioned": topics,
        "hidden_need": hidden_need,
        "risk_level": "crisis" if crisis else ("sensitive" if emotional_intensity == "high" else "normal"),
        "sentiment": mood,
        "emotional_state": _infer_emotional_state(lower, mood, intent),
        "relationship_context": relationship_context,
        "urgency_level": "crisis" if crisis else ("high" if emotional_intensity == "high" else "medium"),
        "current_user_need": _current_user_need(hidden_need, emotional_intensity, intent),
        "flirt_mode": flirt_mode,
    }


def _flirt_mode_for(text: str, intent: str, mood: str, intensity: str, crisis: bool) -> dict[str, Any]:
    comfort_only = (
        crisis
        or intensity == "high"
        or mood in ("sad", "angry", "anxious", "lonely")
        or _contains_any(text, ("cry", "panic", "spiral", "trauma", "hurt myself", "abuse"))
    )
    if comfort_only:
        level = 0
    elif intent == "flirting" and _contains_any(text, ("suggestive", "tension", "romantic", "make me blush")):
        level = 4
    elif intent == "flirting":
        level = 3
    elif _contains_any(text, ("cute", "tease", "playful", "mysterious", "blush")):
        level = 2
    elif mood in ("happy", "hopeful", "excited") or _contains_any(text, ("lol", "haha", "funny")):
        level = 1
    else:
        level = 1

    return {
        "level": level,
        "mode": FLIRT_MODE_LABELS[level],
        "safe_to_flirt": level > 0,
        "comfort_only": level == 0,
        "reason": "lowered for vulnerable or serious emotional context" if level == 0 else "stable enough for warm companion energy",
    }


def _infer_emotional_state(text: str, mood: str, intent: str) -> str:
    if intent == "crisis":
        return "spiraling"
    if _contains_any(text, ("spiral", "panic", "can't stop", "obsessing")):
        return "spiraling"
    if _contains_any(text, ("am i wrong", "is it my fault", "too much")):
        return "seeking_validation"
    if mood in ("angry", "confused"):
        return "frustrated"
    if mood in ("sad", "lonely", "anxious"):
        return "vulnerable"
    if intent in ("clarity", "advice"):
        return "curious"
    return "calm"


def _current_user_need(hidden_need: str, intensity: str, intent: str) -> dict[str, str]:
    primary = {
        "reassurance": "comfort",
        "permission": "clarity",
        "strategy": "strategy",
        "calming": "calming_down",
        "validation": "validation",
    }.get(hidden_need, "validation")
    style = "gentle_tough_love" if intent == "advice" and intensity != "high" else "soft"
    if intent == "crisis":
        style = "protective"
    elif primary == "strategy":
        style = "direct"
    return {
        "primary_need": primary,
        "secondary_need": "emotional_grounding" if intensity == "high" else "next_steps",
        "best_response_style": style,
    }


def build_immediate_context(
    conversation_id: str,
    user_id: UUID,
    started_at: str | None,
    messages: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    advice_given: list[str] = []
    questions_asked: list[str] = []
    validations_given: list[str] = []
    action_steps: list[str] = []

    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = _message_content(msg)
        lower = content.lower()
        for topic, signals in ADVICE_TOPICS.items():
            if _contains_any(lower, signals) and topic not in advice_given:
                advice_given.append(topic)
        questions_asked.extend(re.findall(r"([^?]{8,140}\?)", content))
        if _contains_any(lower, ("makes sense", "i get why", "of course", "that hurts", "you're not crazy")):
            validations_given.append(_summarize(content, 120))
        if _contains_any(lower, ("try", "wait", "text", "ask", "write", "drink water", "breathe")):
            action_steps.append(_summarize(content, 120))

    return {
        "conversation_id": conversation_id,
        "user_id": str(user_id),
        "started_at": started_at,
        "last_updated": now,
        "messages": [
            {
                "message_id": msg.get("message_id") or str(uuid.uuid4()),
                "timestamp": msg.get("timestamp"),
                "sender": "amy" if msg.get("role") == "assistant" else "user",
                "content": _message_content(msg),
                "summary": _summarize(_message_content(msg)),
            }
            for msg in messages[-12:]
        ],
        "conversation_flow": {
            "advice_given": advice_given,
            "questions_asked": questions_asked[-8:],
            "reframes_offered": [],
            "validations_given": validations_given[-6:],
            "warnings_given": [a for a in advice_given if a == "red_flags"],
            "action_steps_suggested": action_steps[-6:],
            "emotional_support_given": validations_given[-6:],
        },
        "topics_to_avoid_repeating": [
            f"Do not repeat {topic.replace('_', ' ')} advice unless using a deeper new angle"
            for topic in advice_given[-5:]
        ],
        "current_user_need": analysis["current_user_need"],
    }


async def build_conversation_intelligence(
    user_id: UUID,
    conversation_id: str,
    user_message: str,
    conversation_messages: list[dict[str, Any]],
    supa: AsyncClient,
    started_at: str | None = None,
) -> dict[str, Any]:
    analysis = analyze_current_message(user_message)
    immediate = build_immediate_context(conversation_id, user_id, started_at, conversation_messages, analysis)
    uid = str(user_id)

    advice_history = await _safe_select(
        supa.table("advice_history").select("*").eq("user_id", uid).order("date_given", desc=True).limit(20)
    )
    emotional_patterns = await _safe_select(
        supa.table("emotional_patterns").select("*").eq("user_id", uid).order("seen_count", desc=True).limit(10)
    )
    relationship_entities = await _safe_select(
        supa.table("relationship_entities").select("*").eq("user_id", uid).order("updated_at", desc=True).limit(10)
    )
    preferences = await _safe_select(
        supa.table("user_preferences").select("*").eq("user_id", uid).limit(1)
    )

    repeat_check = _repeat_check(user_message, analysis, immediate, advice_history)
    prompt_context = _format_prompt_context(
        analysis,
        immediate,
        repeat_check,
        advice_history,
        emotional_patterns,
        relationship_entities,
        preferences[0] if preferences else None,
    )

    return {
        "analysis": analysis,
        "immediate_context": immediate,
        "repeat_check": repeat_check,
        "advice_history": advice_history,
        "emotional_patterns": emotional_patterns,
        "relationship_entities": relationship_entities,
        "prompt_context": prompt_context,
    }


def _repeat_check(
    user_message: str,
    analysis: dict[str, Any],
    immediate: dict[str, Any],
    advice_history: list[dict[str, Any]],
) -> dict[str, Any]:
    current_topics = set(analysis.get("topics_mentioned") or [analysis.get("main_topic")])
    immediate_advice = set(immediate["conversation_flow"]["advice_given"])
    topic_hits = [
        item for item in advice_history
        if str(item.get("topic") or "").lower() in current_topics
    ]
    best_similarity = 0.0
    for item in topic_hits:
        candidate = str(item.get("advice_summary") or item.get("content") or "")
        best_similarity = max(best_similarity, SequenceMatcher(None, user_message.lower(), candidate.lower()).ratio())

    repeated_topic = bool(topic_hits or immediate_advice.intersection(current_topics))
    too_repetitive = repeated_topic and (best_similarity >= 0.45 or bool(immediate_advice))
    new_angle = "focus on emotional regulation before tactics"
    if "emotional_regulation" in immediate_advice:
        new_angle = "name the pattern and offer one concrete next step"
    elif "texting" in immediate_advice or "ghosting" in current_topics:
        new_angle = "separate facts from fear instead of another texting script"
    elif "boundaries" in immediate_advice:
        new_angle = "connect the boundary to self-worth without using the same wording"

    return {
        "has_advice_been_given_before": repeated_topic,
        "similarity_score": round(best_similarity, 2),
        "too_repetitive": too_repetitive,
        "rewrite_required": too_repetitive,
        "new_angle_needed": new_angle if too_repetitive else "personalize from memory and keep moving forward",
    }


def _format_prompt_context(
    analysis: dict[str, Any],
    immediate: dict[str, Any],
    repeat_check: dict[str, Any],
    advice_history: list[dict[str, Any]],
    emotional_patterns: list[dict[str, Any]],
    relationship_entities: list[dict[str, Any]],
    preferences: dict[str, Any] | None,
) -> str:
    lines = [
        "ADVANCED CONVERSATION LOGIC:",
        f"- Current intent: {analysis['user_intent']}; topic: {analysis['main_topic']}; hidden need: {analysis['hidden_need']}; risk: {analysis['risk_level']}.",
        f"- Current emotional state: {analysis['emotional_state']} / {analysis['sentiment']}; intensity: {analysis['emotional_intensity']}.",
        f"- Best response style: {analysis['current_user_need']['best_response_style']}; primary need: {analysis['current_user_need']['primary_need']}.",
    ]
    if immediate["conversation_flow"]["advice_given"]:
        lines.append("- Already covered this chat: " + ", ".join(immediate["conversation_flow"]["advice_given"]))
    if immediate["topics_to_avoid_repeating"]:
        lines.append("- Avoid repeating: " + "; ".join(immediate["topics_to_avoid_repeating"]))
    if repeat_check["rewrite_required"]:
        lines.append(f"- Repetition warning: use a new angle now: {repeat_check['new_angle_needed']}.")
    if advice_history:
        snippets = [
            f"{a.get('topic')}: {a.get('advice_summary')} (reaction: {a.get('user_reaction') or 'unknown'})"
            for a in advice_history[:5]
        ]
        lines.append("- Recent advice history: " + " | ".join(snippets))
    if emotional_patterns:
        snippets = [
            f"{p.get('pattern')} seen {p.get('seen_count', 1)}x; guidance: {p.get('recommended_response') or 'validate first, then go deeper'}"
            for p in emotional_patterns[:4]
        ]
        lines.append("- Repeated emotional patterns: " + " | ".join(snippets))
    if relationship_entities:
        snippets = [
            f"{p.get('name_or_label')} ({p.get('relationship_to_user')}): {p.get('summary')}"
            for p in relationship_entities[:4]
        ]
        lines.append("- People user has mentioned: " + " | ".join(snippets))
    if preferences:
        lines.append(
            "- User response preferences: "
            + str(preferences.get("responds_to") or "validation first, warm directness")
            + "; avoid "
            + str(preferences.get("avoids") or "generic advice")
        )
        romantic_dynamic = preferences.get("romantic_dynamic") or {}
        if romantic_dynamic:
            lines.append(
                "- Romantic dynamic memory: "
                + f"comfortable_with_flirting={romantic_dynamic.get('comfortable_with_flirting')}; "
                + f"likes_pet_names={romantic_dynamic.get('likes_pet_names')}; "
                + f"preferred_style={romantic_dynamic.get('preferred_style') or 'sweet/playful'}; "
                + f"avoid_styles={romantic_dynamic.get('avoid_styles') or ['too aggressive', 'too explicit']}."
            )
    flirt = analysis.get("flirt_mode") or {"level": 0, "mode": "supportive only", "safe_to_flirt": False}
    lines.append(
        f"- Flirty companion layer: level {flirt['level']} ({flirt['mode']}); "
        f"safe_to_flirt={flirt['safe_to_flirt']}; reason: {flirt['reason']}."
    )
    if flirt["level"] == 0:
        lines.append("- Flirt behavior: comfort only. No teasing, suggestive language, jealousy jokes, or pet-name-heavy replies.")
    elif flirt["level"] == 1:
        lines.append("- Flirt behavior: warm/friendly only; affectionate but mostly supportive.")
    elif flirt["level"] == 2:
        lines.append("- Flirt behavior: one light tease or playful observation is allowed if it fits; keep it non-explicit.")
    elif flirt["level"] == 3:
        lines.append("- Flirt behavior: emotionally intimate warmth is allowed; make the user feel seen, not sexualized.")
    else:
        lines.append("- Flirt behavior: playfully suggestive/coy is allowed, but never explicit, pornographic, aggressive, or manipulative.")
    if analysis["risk_level"] == "crisis":
        lines.append("- SAFETY MODE: stay calm, validate, prioritize immediate safety/support, no flirtation or roleplay.")
    lines.append("- Response formula: validate, reference memory if relevant, add a new insight, give one practical next step, close warmly.")
    return "\n".join(lines)


async def save_turn_intelligence(
    user_id: UUID,
    conversation_id: str,
    user_message: str,
    amy_response: str,
    intelligence: dict[str, Any],
    supa: AsyncClient,
) -> None:
    uid = str(user_id)
    now = datetime.utcnow().isoformat()
    analysis = intelligence.get("analysis") or analyze_current_message(user_message)

    if is_adult_language(user_message):
        return

    await _safe_insert(supa.table("memory_updates"), {
        "update_id": str(uuid.uuid4()),
        "user_id": uid,
        "conversation_id": conversation_id,
        "should_save": _should_save_memory(user_message, analysis),
        "memory_type": _memory_type_for(analysis),
        "confidence": "medium",
        "memory_text": _build_memory_update_text(user_message, analysis),
        "expires": "never" if analysis["risk_level"] != "normal" else "90_days",
        "created_at": now,
    })

    for topic in _detect_advice_topics(amy_response, analysis):
        await _safe_insert(supa.table("advice_history"), {
            "advice_id": str(uuid.uuid4()),
            "user_id": uid,
            "conversation_id": conversation_id,
            "topic": topic,
            "advice_summary": _summarize(amy_response, 220),
            "exact_phrases_used": _extract_phrases(amy_response),
            "date_given": now,
            "user_reaction": "unknown",
            "effectiveness": "unknown",
        })

    await _upsert_emotional_pattern(uid, user_message, analysis, supa, now)
    await _maybe_update_romantic_dynamic(uid, user_message, analysis, supa, now)
    await _maybe_save_relationship_entity(uid, user_message, analysis, supa, now)
    await _maybe_save_safety_flag(uid, conversation_id, user_message, analysis, supa, now)
    await _update_conversation_summary(uid, conversation_id, intelligence, supa, now)
    await cache_delete(f"memory_context:{uid}")


def _should_save_memory(user_message: str, analysis: dict[str, Any]) -> bool:
    lower = user_message.lower()
    return (
        analysis["risk_level"] != "normal"
        or bool(analysis.get("topics_mentioned"))
        or _contains_any(lower, (
            "my name is", "call me", "i have adhd", "i have anxiety", "my ex",
            "my boyfriend", "my girlfriend", "my partner", "i always", "i keep",
            "i want to", "my goal", "remember", "flirt", "tease me", "pet name",
        ))
    )


def _memory_type_for(analysis: dict[str, Any]) -> str:
    if analysis["relationship_context"] != "self":
        return "relationship_entity"
    if analysis["main_topic"] in ("self-worth", "anxiety", "ghosting"):
        return "emotional_pattern"
    if analysis["hidden_need"] == "strategy":
        return "advice_history"
    if analysis.get("user_intent") == "flirting":
        return "preference"
    return "user_profile"


def _build_memory_update_text(user_message: str, analysis: dict[str, Any]) -> str:
    topic = analysis.get("main_topic", "personal context")
    state = analysis.get("emotional_state", "unclear")
    return f"User shared {topic} context while feeling {state}: {_summarize(user_message, 260)}"


def _detect_advice_topics(amy_response: str, analysis: dict[str, Any]) -> list[str]:
    lower = amy_response.lower()
    topics = _all_matches(ADVICE_TOPICS, lower)
    main_topic = analysis.get("main_topic")
    if main_topic and main_topic != "self":
        topics.append(main_topic)
    return list(dict.fromkeys(topics))[:4]


def _extract_phrases(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [_summarize(s, 120) for s in sentences if 25 <= len(s) <= 140][:4]


async def _upsert_emotional_pattern(
    uid: str,
    user_message: str,
    analysis: dict[str, Any],
    supa: AsyncClient,
    now: str,
) -> None:
    pattern = _pattern_label(user_message, analysis)
    if not pattern:
        return
    existing = await _safe_select(
        supa.table("emotional_patterns").select("*").eq("user_id", uid).eq("pattern", pattern).limit(1)
    )
    if existing:
        row = existing[0]
        await _safe_update(
            supa.table("emotional_patterns").update({
                "seen_count": int(row.get("seen_count") or 1) + 1,
                "last_seen": now,
                "recommended_response": _recommended_response(pattern),
            }).eq("pattern_id", row["pattern_id"])
        )
    else:
        await _safe_insert(supa.table("emotional_patterns"), {
            "pattern_id": str(uuid.uuid4()),
            "user_id": uid,
            "pattern": pattern,
            "seen_count": 1,
            "first_seen": now,
            "last_seen": now,
            "recommended_response": _recommended_response(pattern),
            "common_thought_loops": _thought_loops(user_message),
            "growth_tracking": {"wins": [], "progress_noticed": [], "skills_practiced": [], "setbacks": []},
            "amy_can_reference": [],
            "created_at": now,
            "updated_at": now,
        })


def _pattern_label(user_message: str, analysis: dict[str, Any]) -> str | None:
    lower = user_message.lower()
    if analysis["risk_level"] == "crisis":
        return "user may be in immediate safety distress"
    if _contains_any(lower, ("didn't text", "not replying", "left on read", "ghost")):
        return "user assumes rejection or danger when replies are delayed"
    if _contains_any(lower, ("too much", "not enough", "unlovable", "always ruin")):
        return "user turns relationship uncertainty into self-blame"
    if _contains_any(lower, ("panic", "spiral", "obsessing", "can't stop thinking")):
        return "user spirals when uncertainty feels unresolved"
    if _contains_any(lower, ("i always", "i keep", "every time")):
        return f"user reports a recurring {analysis['main_topic']} pattern"
    return None


def _recommended_response(pattern: str) -> str:
    if "replies are delayed" in pattern:
        return "validate first, separate facts from fear, then slow the body before texting"
    if "self-blame" in pattern:
        return "protect self-worth, name responsibility gently, avoid shame"
    if "spirals" in pattern:
        return "ground nervous system first, keep advice short and concrete"
    if "safety" in pattern:
        return "switch to safety-first support and encourage immediate real-world help"
    return "validate first, then reality-check gently"


def _thought_loops(user_message: str) -> list[str]:
    loops = re.findall(r"([^.?!]*(?:always|never|hate me|too much|not enough|ruin)[^.?!]*)", user_message, re.I)
    return [_summarize(loop, 120) for loop in loops[:5]]


async def _maybe_update_romantic_dynamic(
    uid: str,
    user_message: str,
    analysis: dict[str, Any],
    supa: AsyncClient,
    now: str,
) -> None:
    lower = user_message.lower()
    positive = _contains_any(lower, FLIRT_POSITIVE_SIGNALS) or analysis.get("user_intent") == "flirting"
    negative = _contains_any(lower, FLIRT_NEGATIVE_SIGNALS)
    if not positive and not negative:
        return

    existing = await _safe_select(
        supa.table("user_preferences").select("*").eq("user_id", uid).limit(1)
    )
    current = existing[0] if existing else {}
    dynamic = dict(current.get("romantic_dynamic") or {})
    avoid_styles = list(dynamic.get("avoid_styles") or ["too aggressive", "too explicit"])

    if negative:
        dynamic.update({
            "comfortable_with_flirting": False,
            "user_enjoys_teasing": False,
            "likes_pet_names": False if _contains_any(lower, ("pet names", "call me", "babe", "baby", "sweetheart")) else dynamic.get("likes_pet_names", False),
            "preferred_style": dynamic.get("preferred_style") or "sweet",
        })
        if "too much flirting" not in avoid_styles:
            avoid_styles.append("too much flirting")
    else:
        dynamic.update({
            "comfortable_with_flirting": True,
            "user_enjoys_teasing": dynamic.get("user_enjoys_teasing", False) or _contains_any(lower, ("tease", "playful", "mysterious")),
            "likes_pet_names": dynamic.get("likes_pet_names", False) or _contains_any(lower, ("pet name", "call me", "sweetheart", "babe", "baby")),
            "preferred_style": _preferred_flirt_style(lower, dynamic.get("preferred_style")),
        })

    dynamic["avoid_styles"] = avoid_styles
    row = {
        "responds_to": current.get("responds_to") or ["validation first", "direct honesty", "gentle encouragement", "step-by-step advice", "warm reassurance"],
        "avoids": current.get("avoids") or ["clinical language", "generic advice", "too many questions", "cold logic", "judgmental tone"],
        "preferred_length": current.get("preferred_length") or "medium",
        "preferred_tone": current.get("preferred_tone") or "girl-next-door",
        "humor_preference": current.get("humor_preference") or "playful",
        "romantic_dynamic": dynamic,
        "updated_at": now,
    }

    if current.get("preference_id"):
        await _safe_update(
            supa.table("user_preferences").update(row).eq("preference_id", current["preference_id"])
        )
    else:
        row.update({"preference_id": str(uuid.uuid4()), "user_id": uid})
        await _safe_insert(supa.table("user_preferences"), row)


def _preferred_flirt_style(text: str, current: str | None) -> str:
    if "country" in text:
        return "country_girl"
    if _contains_any(text, ("soft", "gentle", "sweet")):
        return "soft"
    if _contains_any(text, ("dominant", "confident", "bossy")):
        return "dominant"
    if _contains_any(text, ("tease", "playful", "joke")):
        return "playful"
    return current or "sweet"


async def _maybe_save_relationship_entity(
    uid: str,
    user_message: str,
    analysis: dict[str, Any],
    supa: AsyncClient,
    now: str,
) -> None:
    relationship = analysis.get("relationship_context")
    if relationship == "self":
        return
    label = _extract_person_label(user_message, relationship)
    existing = await _safe_select(
        supa.table("relationship_entities").select("*").eq("user_id", uid).eq("name_or_label", label).limit(1)
    )
    event = {
        "date": now,
        "event": _summarize(user_message, 220),
        "user_emotion": analysis.get("sentiment"),
    }
    if existing:
        row = existing[0]
        events = list(row.get("important_events") or [])[-9:] + [event]
        await _safe_update(
            supa.table("relationship_entities").update({
                "relationship_to_user": relationship,
                "current_status": _infer_relationship_status(user_message),
                "summary": _summarize(user_message, 260),
                "important_events": events,
                "amy_assessment": _amy_assessment(user_message, analysis),
                "updated_at": now,
            }).eq("person_id", row["person_id"])
        )
    else:
        await _safe_insert(supa.table("relationship_entities"), {
            "person_id": str(uuid.uuid4()),
            "user_id": uid,
            "name_or_label": label,
            "relationship_to_user": relationship,
            "current_status": _infer_relationship_status(user_message),
            "summary": _summarize(user_message, 260),
            "positive_traits": [],
            "red_flags": _red_flags(user_message),
            "important_events": [event],
            "amy_assessment": _amy_assessment(user_message, analysis),
            "created_at": now,
            "updated_at": now,
        })


def _extract_person_label(user_message: str, relationship: str) -> str:
    named = re.search(r"\b(?:his|her|their|my)?\s*name is ([A-Z][a-zA-Z]{1,30})", user_message)
    if named:
        return named.group(1)
    cap = re.search(r"\b([A-Z][a-zA-Z]{2,30})\b", user_message)
    if cap and cap.group(1).lower() not in ("i", "amy"):
        return cap.group(1)
    return f"my {relationship}"


def _infer_relationship_status(user_message: str) -> str:
    lower = user_message.lower()
    if _contains_any(lower, ("no contact", "blocked", "ended", "broke up")):
        return "no_contact" if "no contact" in lower or "blocked" in lower else "ended"
    if _contains_any(lower, ("still talking", "texting", "seeing", "dating")):
        return "active"
    return "unclear"


def _red_flags(user_message: str) -> list[str]:
    lower = user_message.lower()
    flags = []
    if _contains_any(lower, ("ghost", "left on read", "not replying")):
        flags.append("inconsistent communication")
    if _contains_any(lower, ("lied", "cheated")):
        flags.append("dishonesty")
    if _contains_any(lower, ("hot and cold", "mixed signals")):
        flags.append("hot and cold behavior")
    return flags


def _amy_assessment(user_message: str, analysis: dict[str, Any]) -> dict[str, str]:
    flags = _red_flags(user_message)
    return {
        "healthy_for_user": "mixed" if flags else "unknown",
        "risk_level": "high" if analysis["risk_level"] == "crisis" else ("medium" if flags else "low"),
        "recommended_guidance": "help user slow down and watch consistency" if flags else "validate and gather more context",
    }


async def _maybe_save_safety_flag(
    uid: str,
    conversation_id: str,
    user_message: str,
    analysis: dict[str, Any],
    supa: AsyncClient,
    now: str,
) -> None:
    if analysis["risk_level"] != "crisis":
        return
    await _safe_insert(supa.table("safety_flags"), {
        "flag_id": str(uuid.uuid4()),
        "user_id": uid,
        "conversation_id": conversation_id,
        "risk_level": "crisis",
        "trigger_text": _summarize(user_message, 500),
        "response_mode": "safety_first",
        "resolved": False,
        "created_at": now,
    })


async def _update_conversation_summary(
    uid: str,
    conversation_id: str,
    intelligence: dict[str, Any],
    supa: AsyncClient,
    now: str,
) -> None:
    analysis = intelligence.get("analysis") or {}
    immediate = intelligence.get("immediate_context") or {}
    messages = immediate.get("messages") or []
    topics = analysis.get("topics_mentioned") or [analysis.get("main_topic", "self")]
    await _safe_insert(supa.table("conversation_summaries"), {
        "summary_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "user_id": uid,
        "summary": _summarize(" / ".join(m.get("summary", "") for m in messages[-4:]), 600),
        "topics": [t for t in topics if t],
        "emotional_arc": {
            "current_state": analysis.get("emotional_state"),
            "sentiment": analysis.get("sentiment"),
            "intensity": analysis.get("emotional_intensity"),
        },
        "advice_given": immediate.get("conversation_flow", {}).get("advice_given", []),
        "questions_asked": immediate.get("conversation_flow", {}).get("questions_asked", []),
        "updated_at": now,
    })


async def _safe_select(query: Any) -> list[dict[str, Any]]:
    try:
        result = await query.execute()
        return result.data or []
    except Exception:
        return []


async def _safe_insert(query: Any, row: dict[str, Any]) -> None:
    try:
        await query.insert(row).execute()
    except Exception:
        return


async def _safe_update(query: Any) -> None:
    try:
        await query.execute()
    except Exception:
        return


def summarize_advice_mix(advice_history: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("topic") or "unknown") for item in advice_history)
    return dict(counts.most_common(8))
