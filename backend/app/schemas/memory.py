from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.memory import EventType, GoalCategory, MemoryType


class LifeEventCreate(BaseModel):
    event_type: EventType
    description: str
    date_occurred: Optional[datetime] = None
    emotional_weight: int = Field(default=5, ge=1, le=10)
    still_processing: bool = True


class LifeEventResponse(BaseModel):
    event_id: UUID
    event_type: EventType
    description: str
    date_occurred: Optional[datetime]
    emotional_weight: int
    still_processing: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BehavioralPatternCreate(BaseModel):
    pattern_name: str
    description: str
    context: Optional[str] = None
    importance_score: int = Field(default=5, ge=1, le=10)


class BehavioralPatternResponse(BaseModel):
    pattern_id: UUID
    pattern_name: str
    description: str
    frequency_detected: int
    context: Optional[str]
    last_triggered: Optional[datetime]
    importance_score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    goal_text: str
    category: GoalCategory = GoalCategory.other


class GoalResponse(BaseModel):
    goal_id: UUID
    goal_text: str
    category: GoalCategory
    created_at: datetime
    achieved_date: Optional[datetime]

    model_config = {"from_attributes": True}


class SensitivityCreate(BaseModel):
    topic: str
    description: str
    handling_notes: Optional[str] = None


class SensitivityResponse(BaseModel):
    sensitivity_id: UUID
    topic: str
    description: str
    handling_notes: Optional[str]

    model_config = {"from_attributes": True}


class MemoryExtractResponse(BaseModel):
    memory_id: UUID
    memory_type: MemoryType
    content: str
    importance_score: int
    auto_extracted: bool
    last_referenced: Optional[datetime]
    date_learned: datetime

    model_config = {"from_attributes": True}


class RelationshipEntityResponse(BaseModel):
    person_id: UUID
    name_or_label: str
    relationship_to_user: str
    current_status: str
    summary: str
    positive_traits: list = []
    red_flags: list = []
    important_events: list = []
    amy_assessment: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmotionalPatternResponse(BaseModel):
    pattern_id: UUID
    pattern: str
    seen_count: int
    first_seen: datetime
    last_seen: datetime
    recommended_response: Optional[str]
    common_thought_loops: list = []
    growth_tracking: dict = {}
    amy_can_reference: list = []

    model_config = {"from_attributes": True}


class AdviceHistoryResponse(BaseModel):
    advice_id: UUID
    topic: str
    advice_summary: str
    exact_phrases_used: list = []
    date_given: datetime
    user_reaction: str
    effectiveness: str

    model_config = {"from_attributes": True}


class MemoryUpdateResponse(BaseModel):
    update_id: UUID
    should_save: bool
    memory_type: str
    confidence: str
    memory_text: str
    expires: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryBankResponse(BaseModel):
    life_events: list[LifeEventResponse]
    behavioral_patterns: list[BehavioralPatternResponse]
    goals: list[GoalResponse]
    sensitivities: list[SensitivityResponse]
    memory_extracts: list[MemoryExtractResponse]
    relationship_entities: list[RelationshipEntityResponse] = []
    emotional_patterns: list[EmotionalPatternResponse] = []
    advice_history: list[AdviceHistoryResponse] = []
    memory_updates: list[MemoryUpdateResponse] = []
