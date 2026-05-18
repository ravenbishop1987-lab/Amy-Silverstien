import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class SubscriptionEventType(str, enum.Enum):
    started = "subscription_started"
    upgraded = "upgraded"
    downgraded = "downgraded"
    canceled = "canceled"
    renewed = "renewed"
    payment_failed = "payment_failed"


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    event_type: Mapped[SubscriptionEventType] = mapped_column(
        SAEnum(SubscriptionEventType, name="subscription_event_type", create_type=False), nullable=False
    )
    tier_before: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tier_after: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stripe_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="subscription_events")


class VoiceCredit(Base):
    __tablename__ = "voice_credits"

    credit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, nullable=False)
    voice_conversations_remaining: Mapped[int] = mapped_column(Integer, default=0)
    text_conversations_remaining: Mapped[int] = mapped_column(Integer, default=3)
    daily_limit_resets_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reset_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="voice_credits")


class WebsiteEmbed(Base):
    __tablename__ = "website_embeds"

    embed_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    website_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    embed_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    widget_config: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="website_embeds")


class YouTubeContent(Base):
    __tablename__ = "youtube_content"

    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    transcript: Mapped[str | None] = mapped_column(nullable=True)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
