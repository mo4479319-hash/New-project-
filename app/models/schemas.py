"""
Pydantic models for API request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Business ──────────────────────────────────────────────────

class BusinessCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="business")
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    type: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# ── Chat ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    business_id: UUID
    conversation_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    intent: str
    backbone: Optional[dict] = None
    files: Optional[list[dict]] = None


# ── Website Configuration ─────────────────────────────────────

class WebsiteConfigResponse(BaseModel):
    id: UUID
    business_id: UUID
    backbone: dict
    environment: str
    created_at: datetime
    files: Optional[list[dict]] = None


class WebsiteConfigHistoryItem(BaseModel):
    id: UUID
    environment: str
    difference: Optional[list[dict]] = None
    message_id: Optional[UUID] = None
    created_at: datetime


class PublishRequest(BaseModel):
    """Promote staging to production."""
    pass


# ── Internal models ───────────────────────────────────────────

class IntentClassification(BaseModel):
    intent: str  # "create_website", "update_website", "general"
    response: str  # brief acknowledgement


class ParsedLLMResponse(BaseModel):
    description: str
    files: list[dict]  # [{"path": "index.html", "content": "..."}]
    backbone: dict
