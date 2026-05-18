import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class EventType(str, enum.Enum):
    breakup = "breakup"
    rejection = "rejection"
    trauma = "trauma"
    milestone = "milestone"
    achievement = "achievement"


class PatternName(str, enum.Enum):
    overthinks = "overthinks"
    avoids_conflict = "avoids_conflict"
    anxious_attachment = "anxious_attachment"
    people_pleasing = "people_pleasing"
    self_sabotage = "self_sabotage"
    other = "other"


class GoalCategory(str, enum.Enum):
    confidence = "confidence"
    boundaries = "boundaries"
    vulnerability = "vulnerability"
    communication = "communication"
    other = "other"


class MemoryType(str, enum.Enum):
    trauma = "trauma"
    pattern = "pattern"
    goal = "goal"
    sensitivity = "sensitivity"
    win = "win"
    insight = "insight"


class LifeEvent(Base):
    __tablename__ = "life_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, name="event_type", create_type=False), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date_occurred: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    emotional_weight: Mapped[int] = mapped_column(default=5)
    still_processing: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="life_events")


class BehavioralPattern(Base):
    __tablename__ = "behavioral_patterns"

    pattern_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency_detected: Mapped[int] = mapped_column(default=1)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    importance_score: Mapped[int] = mapped_column(default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="behavioral_patterns")


class Goal(Base):
    __tablename__ = "goals"

    goal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[GoalCategory] = mapped_column(
        SAEnum(GoalCategory, name="goal_category", create_type=False), default=GoalCategory.other
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    achieved_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="goals")


class Sensitivity(Base):
    __tablename__ = "sensitivities"

    sensitivity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    handling_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sensitivities")


class MemoryExtract(Base):
    __tablename__ = "memory_extracts"

    memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(
        SAEnum(MemoryType, name="memory_type", create_type=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id"), nullable=True)
    importance_score: Mapped[int] = mapped_column(default=5)
    auto_extracted: Mapped[bool] = mapped_column(Boolean, default=True)
    last_referenced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_learned: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="memory_extracts")
