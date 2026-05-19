from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import SubscriptionTier, AttachmentStyle, CommunicationPreference


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    preferred_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    credential: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    subscription_tier: SubscriptionTier


class UserProfileResponse(BaseModel):
    profile_id: UUID
    age: Optional[int] = None
    relationship_status: Optional[str] = None
    adhd_severity: Optional[int] = None
    attachment_style: AttachmentStyle
    communication_preference: CommunicationPreference
    timezone: Optional[str] = None
    preferred_name: Optional[str] = None
    pronouns: Optional[str] = None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    age: Optional[int] = None
    relationship_status: Optional[str] = None
    adhd_severity: Optional[int] = Field(None, ge=1, le=10)
    attachment_style: Optional[AttachmentStyle] = None
    communication_preference: Optional[CommunicationPreference] = None
    timezone: Optional[str] = None
    preferred_name: Optional[str] = None
    pronouns: Optional[str] = None


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    subscription_tier: SubscriptionTier
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    model_config = {"from_attributes": True}
