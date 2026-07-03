from pydantic import BaseModel
from typing import Optional, List


class KnowledgeSourceCreate(BaseModel):
    title: str
    category: str
    content: str


class AssistantCreate(BaseModel):
    name: str
    persona: str
    hallucination_bias: float = 0.15


class ChatRequest(BaseModel):
    assistant_id: int
    prompt: str


class FeedbackCreate(BaseModel):
    conversation_id: int
    rating: str  # "up" or "down"
    comment: Optional[str] = None


class GovernanceReviewUpdate(BaseModel):
    status: str  # "approved" | "rejected" | "pending"
    reviewer_note: Optional[str] = None
