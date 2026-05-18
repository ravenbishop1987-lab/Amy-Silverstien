import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # JSON array: [{role, content, timestamp, voice_used}]
    messages: Mapped[list] = mapped_column(JSON, default=list)
    topics_discussed: Mapped[list] = mapped_column(JSON, default=list)
    date_started: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    date_ended: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_mood_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_mood_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_insights: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="conversations")
    memory_extracts: Mapped[list["MemoryExtract"]] = relationship(
        "MemoryExtract",
        foreign_keys="MemoryExtract.source_conversation_id",
        cascade="all, delete-orphan",
    )
