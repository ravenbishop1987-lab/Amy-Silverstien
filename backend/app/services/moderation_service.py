"""
Self-harm content detection + email alerting for Sophie Parker chatbot.
Tiers: 0 = clean, 1 = ideation/warning, 2 = active harm/quarantine, 3 = imminent/block.
"""

import re
import asyncio
import smtplib
import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Tier 1 — Ideation / Hopelessness ──────────────────────────────────────────
_TIER1_PATTERNS = [
    r"\bwant to (?:hurt|harm|kill) (?:my)?self\b",
    r"\bthinking about (?:killing|ending|suicide|suiciding) (?:my)?self\b",
    r"\bsuicidal(?: thoughts?| ideation)?\b",
    r"\bsuicide(?: thoughts?| ideation| attempt)?\b",
    r"\bcan'?t do this anymore\b",
    r"\bi want to die\b",
    r"\bi don'?t want to (?:live|be here|exist)(?: anymore)?\b",
    r"\bno (?:point|reason) (?:in living|to live|for living)\b",
    r"\beveryone would be better off without me\b",
    r"\bi'?m a (?:burden|mistake|waste)\b",
    r"\bi'?m worthless\b",
    r"\bi don'?t deserve to live\b",
    r"\bi deserve to (?:suffer|die|hurt)\b",
    r"\bdon'?t want to (?:be here|exist|live) anymore\b",
    r"\bwish i (?:was|were) dead\b",
    r"\b(?:feel|feeling|felt) hopeless\b",
    r"\bnothing (?:left|to live for)\b",
    r"\bshould just end it\b",
    r"\bnobody (?:cares about me|would miss me|needs me)\b",
    r"\bgiving up on (?:my)?self\b",
    r"\bgive up on (?:my)?self\b",
    r"\bi'?m done(?: with life| with everything| with it all)\b",
    r"\bcan'?t take (?:this|it) anymore\b",
    r"\blife (?:isn'?t worth|not worth) (?:it|living)\b",
    r"\bready to (?:die|give up)\b",
    r"\bi'?m going to (?:hurt|harm) myself\b",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bend it all\b",
    r"\bno one would care if i (?:died|was gone|disappeared)\b",
]

# ── Tier 2 — Active Self-Harm Description ─────────────────────────────────────
_TIER2_PATTERNS = [
    r"\bi (?:cut|'?m cutting|'?m going to cut) (?:my)?self\b",
    r"\bcutting (?:my)?self\b",
    r"\bi (?:burned|'?m burning|burn) (?:my)?self\b",
    r"\bi (?:scratched|'?m scratching|scratch) (?:my)?self\b",
    r"\bi (?:hit|'?m hitting|hits) (?:my)?self\b",
    r"\bi (?:choked|'?m choking|choke) (?:my)?self\b",
    r"\bi (?:poisoned|'?m poisoning) (?:my)?self\b",
    r"\bi (?:overdosed|overdose|'?m overdosing)\b",
    r"\btook (?:too many|a (?:bunch|lot) of) pills\b",
    r"\bi (?:starved|starve|'?m starving) (?:my)?self\b",
    r"\bstopped eating\b",
    r"\bself[- ]harm(?:ing|ed|s)?\b",
    r"\bself[- ]injur(?:y|ing|ed|ies)\b",
    r"\bslitt?ing (?:my )?wrists?\b",
    r"\bi'?m going to (?:cut|burn|hurt|harm|overdose|poison|choke) (?:my)?self\b",
    r"\bi have (?:\d+|several|some|a (?:lot|bunch) of) (?:pills|drugs)\b",
    r"\b(?:scars?|wounds?|marks?|blood|bleeding) (?:from|on my)\b",
    r"\bi (?:purge|'?m purging|purged)\b",
    r"\bstarv(?:ing|ation) as (?:punishment|control)\b",
    r"\bmy (?:scars?|wounds?|cuts?|burns?)\b",
]

# ── Tier 3 — Imminent / Active Emergency ──────────────────────────────────────
_TIER3_PATTERNS = [
    r"\bi'?m (?:going to|about to) (?:kill|end) (?:my)?self (?:right now|tonight|today|now|in \d+)\b",
    r"\bi'?m (?:going to|about to) (?:cut|burn|overdose|poison|hang|shoot) myself (?:right now|tonight|now)\b",
    r"\bi have .{0,40}(?:pills|gun|knife|rope|weapon).{0,40}(?:and i'?m|i'?m ready|ready to)\b",
    r"\bending (?:this|it all|my life) (?:tonight|now|right now|today)\b",
    r"\bgoodbye.{0,80}(?:i'?m sorry|forever|this is it|last)\b",
    r"\bthis is (?:my last|goodbye)\b",
    r"\b(?:in \d+ (?:minutes?|hours?))[^\n]{0,30}(?:kill|end|hurt|harm) (?:my)?self\b",
    r"\b(?:right now|doing it now|it'?s time)[^\n]{0,30}(?:kill|end|hurt|harm) (?:my)?self\b",
    r"\bfound (?:a |my )?method\b",
    r"\b(?:planned?|planning) (?:my |to )suicide\b",
    r"\bsuicide note\b",
    r"\bmy last (?:message|words?|night|day)\b",
    r"\bi'?ve already (?:cut|burned|hurt|overdosed|poisoned|harmed) (?:my)?self\b",
    r"\bwhen (?:everyone'?s asleep|i get home|the clock hits|they'?re gone).{0,30}(?:kill|end|hurt)\b",
    r"\b(?:countdown|counting down).{0,20}(?:die|death|end|kill)\b",
    r"\bi'?m in .{0,30} with .{0,20}(?:pills|gun|knife|rope)\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_TIER1 = _compile(_TIER1_PATTERNS)
_TIER2 = _compile(_TIER2_PATTERNS)
_TIER3 = _compile(_TIER3_PATTERNS)

# ── Crisis Response Text ───────────────────────────────────────────────────────

TIER1_SOPHIE_RESPONSE = (
    "Hey, I hear you — and I'm not going anywhere. What you're feeling right now is real and heavy, "
    "and you don't have to carry it alone.\n\n"
    "Before we keep talking, I want to make sure you have this:\n"
    "📞 Call or text 988 (Suicide & Crisis Lifeline) — free, 24/7\n"
    "💬 Text HOME to 741741 (Crisis Text Line)\n"
    "🌐 suicidepreventionlifeline.org\n\n"
    "I'm here to listen, but these people are trained to help in ways I can't. "
    "Will you reach out to one of them? I'll still be here."
)

TIER2_FORCED_MESSAGE = (
    "I care about you and I need to pause for a second.\n\n"
    "I noticed you mentioned self-harm, and I want to make sure you have real support right now.\n\n"
    "📞 988 — Suicide & Crisis Lifeline (call or text, free, 24/7)\n"
    "💬 Text HOME to 741741 (Crisis Text Line)\n"
    "🏥 If you're in immediate danger, go to the nearest emergency room or call 911.\n\n"
    "You deserve real support. Please reach out to one of these before we continue."
)

TIER3_BLOCK_MESSAGE = (
    "If you are in immediate danger, please call 911 or go to the nearest emergency room right now.\n\n"
    "📞 988 — Suicide & Crisis Lifeline (call or text, free, 24/7)\n"
    "💬 Text HOME to 741741 (Crisis Text Line)\n"
    "🚑 Call 911 for immediate emergency help\n\n"
    "Your safety is the most important thing. Help is available right now."
)


@dataclass
class ModerationResult:
    tier: int
    trigger: str
    crisis_response: str | None


def check_message(text: str) -> ModerationResult:
    """Check a user message. Returns tier 0 if clean. Checks highest tier first."""
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


# ── Email Alerts ──────────────────────────────────────────────────────────────

def _send_email_sync(subject: str, body: str) -> None:
    """Synchronous email send — called via run_in_executor."""
    from app.config import settings
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.warning("SMTP not configured — skipping moderation email alert")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = "ravenbishop1987@gmail.com"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, "ravenbishop1987@gmail.com", msg.as_string())
        logger.info(f"Moderation alert email sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send moderation email: {e}")


async def send_moderation_alert(
    tier: int,
    user_email: str,
    user_id: str,
    trigger: str,
    conversation_messages: list,
    conversation_id: str | None = None,
) -> None:
    """Fire-and-forget email alert to admin."""
    tier_labels = {1: "Tier 1 — Ideation", 2: "🚨 TIER 2 — Active Self-Harm", 3: "🚨🚨 TIER 3 EMERGENCY"}
    tier_actions = {
        1: "Crisis resources injected. Conversation continues. Manual review recommended.",
        2: "Conversation PAUSED. User shown mandatory resources. Review required before unlock.",
        3: "User BLOCKED immediately. Chat access revoked. Emergency resources displayed.",
    }

    # Format recent messages for email
    recent = conversation_messages[-10:] if conversation_messages else []
    thread = ""
    for m in recent:
        role = "User" if m.get("role") == "user" else "Sophie"
        content = (m.get("content") or "")[:500]
        thread += f"{role}: {content}\n\n"

    subject = f"[Sophie Admin] {tier_labels.get(tier, f'Tier {tier}')} Flag — {user_email}"
    body = f"""MODERATION ALERT — {tier_labels.get(tier, f'Tier {tier}')}
{'='*60}

User: {user_email}
User ID: {user_id}
Conversation ID: {conversation_id or 'N/A'}
Detected At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Trigger phrase: "{trigger}"

Action taken: {tier_actions.get(tier, 'Unknown')}

{'='*60}
RECENT CONVERSATION:
{'='*60}

{thread or 'No prior messages.'}

{'='*60}
NEXT STEPS:
Review this flag in your admin dashboard:
  https://amy-silverstien-1.onrender.com/admin

{'For Tier 2: Decide whether to unlock the user or maintain block.' if tier == 2 else ''}
{'For Tier 3: Consider contacting local authorities if you have user contact info.' if tier == 3 else ''}

Crisis resources active:
  988 Suicide & Crisis Lifeline
  Crisis Text Line: Text HOME to 741741
"""

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_email_sync, subject, body)
