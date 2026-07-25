from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.models import CardType, CardStatus, CardSource


# Auth
class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Topics
class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TopicResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    cards_total: int = 0
    cards_mastered: int = 0

    class Config:
        from_attributes = True


# Cards
class CardCreate(BaseModel):
    topic_id: int
    type: CardType
    front_content: str
    back_content: str


class CardUpdate(BaseModel):
    front_content: Optional[str] = None
    back_content: Optional[str] = None
    status: Optional[CardStatus] = None


class CardResponse(BaseModel):
    id: int
    topic_id: int
    type: CardType
    status: CardStatus
    source: CardSource
    front_content: str
    back_content: str
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True


# Learning
class ExerciseAttempt(BaseModel):
    card_id: int
    exercise_type: str
    answer: str
    used_hint: bool = False
    response_time_ms: Optional[int] = None


class AttemptResult(BaseModel):
    correct: bool
    consecutive_correct: int
    required_consecutive: int = 3
    exercise_mastered: bool
    card_mastered: bool
    next_card: Optional[CardResponse] = None


class LearningStateResponse(BaseModel):
    topic_id: int
    current_card: Optional[CardResponse]
    next_exercise_type: Optional[str]
    reviews_due: int
    progress_percent: float
