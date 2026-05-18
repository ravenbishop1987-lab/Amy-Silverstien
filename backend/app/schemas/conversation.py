from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


class MessageCreate(BaseModel):
    content: str
    voice_used: bool = False


class WSMessage(BaseModel):
    type: str  # "message" | "token" | "done" | "error" | "mood"
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    mood_before: Optional[int] = None
    data: Optional[Any] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    user_mood_before: Optional[int] = None


class ConversationResponse(BaseModel):
    conversation_id: UUID
    user_id: UUID
    title: Optional[str]
    messages: list
    topics_discussed: list
    date_started: datetime
    date_ended: Optional[datetime]
    duration_seconds: Optional[int]
    user_mood_before: Optional[int]
    user_mood_after: Optional[int]
    key_insights: list
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    conversation_id: UUID
    title: Optional[str]
    date_started: datetime
    date_ended: Optional[datetime]
    message_count: int
    topics_discussed: list
    user_mood_before: Optional[int]
    user_mood_after: Optional[int]

    model_config = {"from_attributes": True}


class MoodUpdate(BaseModel):
    mood_after: int
