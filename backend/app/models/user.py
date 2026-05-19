import enum
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


class SubscriptionTier(str, enum.Enum):
    free = "free"
    credits = "credits"
    premium = "premium"


class AttachmentStyle(str, enum.Enum):
    secure = "secure"
    anxious = "anxious"
    avoidant = "avoidant"
    fearful = "fearful"
    unknown = "unknown"


class CommunicationPreference(str, enum.Enum):
    voice = "voice"
    text = "text"
    both = "both"


def _parse_dt(val) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        from dateutil.parser import parse
        return parse(val)
    except Exception:
        return None


@dataclass
class UserRecord:
    """Lightweight user object built from a Supabase row dict."""
    user_id: UUID
    email: str
    password_hash: str
    subscription_tier: SubscriptionTier
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "UserRecord":
        return cls(
            user_id=UUID(str(row["user_id"])),
            email=row["email"],
            password_hash=row["password_hash"],
            subscription_tier=SubscriptionTier(row.get("subscription_tier", "free")),
            stripe_customer_id=row.get("stripe_customer_id"),
            stripe_subscription_id=row.get("stripe_subscription_id"),
            created_at=_parse_dt(row.get("created_at")),
            last_login=_parse_dt(row.get("last_login")),
        )
