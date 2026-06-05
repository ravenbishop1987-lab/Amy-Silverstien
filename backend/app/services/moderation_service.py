"""
Self-harm content detection for Sophie Parker chatbot.
Scans user messages and returns the detected tier (0 = safe, 1/2/3 = escalating risk).
"""

import re
from dataclasses import dataclass

# Tier 1 — ideation / hopelessness (do not block; log + add crisis resources)
_TIER1_PATTERNS = [
    r"\bwant to (?:hurt|harm|kill) (?:my)?self\b",
    r"\bthinking about (?:killing|ending) (?:my)?self\b",
    r"\bsuicidal thoughts?\b",
    r"\bcan'?t do this anymore\b",
    r"\bi want to die\b",
    r"\bno point (?:in living|anymore)\b",
    r"\beveryone would be better off without me\b",
    r"\bi'?m a burden\b",
    r"\bi deserve to suffer\b",
    r"\bdon'?t want to (?:be here|exist|live) anymore\b",
    r"\bwish i (?:was|were) dead\b",
    r"\b(?:feel|feeling) hopeless\b",
    r"\bnothing (?:left|to live for)\b",
    r"\bend it all\b",
]

# Tier 2 — active/ongoing self-harm descriptions (pause + mandatory resources)
_TIER2_PATTERNS = [
    r"\bi (?:cut|cutting|burned|burning|hit|hurt) (?:my)?self\b",
    r"\bi overdosed\b",
    r"\btook (?:too many |a bunch of )?pills\b",
    r"\bi'?m going to (?:cut|hurt|harm|burn|overdose)\b",
    r"\bstarving (?:my)?self\b",
    r"\bstopped eating for\b",
    r"\bself[- ]harm(?:ing|ed)?\b",
    r"\bself[- ]injur(?:y|ing|ed)\b",
    r"\bslitting (?:my )?wrists\b",
    r"\bstarv(?:ing|ation) as (?:punishment|control)\b",
]

# Tier 3 — imminent / specific method + timeline (immediate block)
_TIER3_PATTERNS = [
    r"\bi'?m (?:going to|about to) (?:kill|end) (?:my)?self (?:right now|tonight|today|in \d+)\b",
    r"\bi have .{0,30}(?:pills|gun|knife|rope).{0,30}(?:and i'?m|ready)\b",
    r"\bending (?:this|it all|my life) tonight\b",
    r"\bgoodbye.{0,60}(?:i'?m sorry|forever)\b",
    r"\b(?:in \d+ (?:minutes?|hours?)|right now).{0,30}(?:kill|end|hurt) (?:my)?self\b",
    r"\bfound a method\b",
    r"\b(?:plan|planned) (?:to kill|my suicide)\b",
    r"\bsuicide note\b",
    r"\bmy last (?:message|words?)\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_TIER1 = _compile(_TIER1_PATTERNS)
_TIER2 = _compile(_TIER2_PATTERNS)
_TIER3 = _compile(_TIER3_PATTERNS)

TIER1_SOPHIE_RESPONSE = (
    "Hey, I hear you — and I'm not going anywhere. What you're feeling right now is real and heavy, "
    "and you don't have to carry it alone.\n\n"
    "Before we keep talking, I want to make sure you have this:\n"
    "📞 **988 Suicide & Crisis Lifeline** — call or text 988, free and 24/7\n"
    "💬 **Crisis Text Line** — text HOME to 741741\n"
    "🌐 suicidepreventionlifeline.org\n\n"
    "I'm here to listen, but these people are trained to help in ways I can't. "
    "Will you reach out to one of them?"
)

TIER2_FORCED_MESSAGE = (
    "I care about you and I need to pause our conversation for a second.\n\n"
    "⚠️ **Please get support right now:**\n"
    "📞 **988** — Suicide & Crisis Lifeline (call or text, free, 24/7)\n"
    "💬 **Crisis Text Line** — text HOME to 741741\n"
    "🏥 If you're in immediate danger, please go to the nearest emergency room or call 911.\n\n"
    "You deserve real support. I'll be here when you're ready to talk."
)

TIER3_BLOCK_MESSAGE = (
    "🚨 If you are in immediate danger, please call 911 or go to the nearest emergency room right now.\n\n"
    "📞 **988 Suicide & Crisis Lifeline** — call or text 988\n"
    "💬 **Crisis Text Line** — text HOME to 741741\n\n"
    "Your safety is the most important thing. Help is available right now."
)


@dataclass
class ModerationResult:
    tier: int          # 0 = clean, 1/2/3 = escalating
    trigger: str       # the matched text excerpt
    crisis_response: str | None  # message to inject/return to user


def check_message(text: str) -> ModerationResult:
    """Check a user message. Returns tier 0 if clean."""
    # Check highest tier first
    for pattern in _TIER3:
        m = pattern.search(text)
        if m:
            return ModerationResult(tier=3, trigger=m.group(0), crisis_response=TIER3_BLOCK_MESSAGE)

    for pattern in _TIER2:
        m = pattern.search(text)
        if m:
            return ModerationResult(tier=2, trigger=m.group(0), crisis_response=TIER2_FORCED_MESSAGE)

    for pattern in _TIER1:
        m = pattern.search(text)
        if m:
            return ModerationResult(tier=1, trigger=m.group(0), crisis_response=TIER1_SOPHIE_RESPONSE)

    return ModerationResult(tier=0, trigger="", crisis_response=None)


moderation_service = moderation_service = type("_MS", (), {"check_message": staticmethod(check_message)})()
