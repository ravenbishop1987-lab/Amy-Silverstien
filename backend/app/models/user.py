import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


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


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, name="subscription_tier", create_type=False),
        default=SubscriptionTier.free, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    life_events: Mapped[list["LifeEvent"]] = relationship("LifeEvent", back_populates="user", cascade="all, delete-orphan")
    behavioral_patterns: Mapped[list["BehavioralPattern"]] = relationship("BehavioralPattern", back_populates="user", cascade="all, delete-orphan")
    goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    sensitivities: Mapped[list["Sensitivity"]] = relationship("Sensitivity", back_populates="user", cascade="all, delete-orphan")
    memory_extracts: Mapped[list["MemoryExtract"]] = relationship("MemoryExtract", back_populates="user", cascade="all, delete-orphan")
    voice_credits: Mapped["VoiceCredit"] = relationship("VoiceCredit", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscription_events: Mapped[list["SubscriptionEvent"]] = relationship("SubscriptionEvent", back_populates="user", cascade="all, delete-orphan")
    website_embeds: Mapped[list["WebsiteEmbed"]] = relationship("WebsiteEmbed", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    relationship_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adhd_severity: Mapped[int | None] = mapped_column(nullable=True)
    attachment_style: Mapped[AttachmentStyle] = mapped_column(
        SAEnum(AttachmentStyle, name="attachment_style", create_type=False),
        default=AttachmentStyle.unknown
    )
    communication_preference: Mapped[CommunicationPreference] = mapped_column(
        SAEnum(CommunicationPreference, name="communication_preference", create_type=False),
        default=CommunicationPreference.text
    )
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website_embeds: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped["User"] = relationship("User", back_populates="profile")
