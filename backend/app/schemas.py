from datetime import datetime, date
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    email_verified: bool

    class Config:
        from_attributes = True


class MembershipOut(BaseModel):
    organization_id: str
    role: str


class OrganizationCreate(BaseModel):
    name: str


class OrganizationOut(BaseModel):
    id: str
    name: str
    autopilot_enabled: bool

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    autopilot_enabled: bool = False


class ProjectOut(BaseModel):
    id: str
    name: str
    autopilot_enabled: bool
    organization_id: str

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: str
    slot_date: date
    slot_index: int
    status: str
    approved: bool
    locked: bool
    project_id: str

    class Config:
        from_attributes = True


class PromptVersionOut(BaseModel):
    name: str
    version: int
    body: str
    organization_id: str

    class Config:
        from_attributes = True


class VideoAssetOut(BaseModel):
    id: str
    organization_id: str | None = None
    project_id: str | None = None
    plan_id: str | None = None
    status: str
    video_path: str
    thumbnail_path: str
    publish_response: str | None = None
    created_at: datetime | None = None
    signed_video_url: str | None = None
    signed_thumbnail_url: str | None = None

    class Config:
        from_attributes = True


class JobRunOut(BaseModel):
    status: str
    message: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    type: str
    status: str
    payload: str | None = None
    created_at: datetime
    runs: List[JobRunOut] = []

    class Config:
        from_attributes = True


class MetricOut(BaseModel):
    metric: str
    value: int
    created_at: datetime

    class Config:
        from_attributes = True


class CalendarSlot(BaseModel):
    date: date
    slots: List[PlanOut]


class CredentialCreate(BaseModel):
    provider: str
    name: str
    secret: str


class CredentialOut(BaseModel):
    id: str
    provider: str
    name: str
    version: int

    class Config:
        from_attributes = True


class KnowledgeDocOut(BaseModel):
    id: str
    title: str
    content: str

    class Config:
        from_attributes = True


class SocialAccountOut(BaseModel):
    id: str
    platform: str
    handle: str

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class VerificationRequest(BaseModel):
    email: EmailStr


class VerificationConfirm(BaseModel):
    token: str
