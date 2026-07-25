"""Pydantic-схемы — API-контракт между фронтендом и бэкендом.

Источник истины для issue #2. Все endpoints MVP описаны здесь;
OpenAPI генерируется из этих схем, TS-типы — из OpenAPI.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.models.models import CardType, CardStatus, CardSource


# ---------------------------------------------------------------------------
# Errors (единый формат: {"detail": str, "code": str})
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    code: str = Field(
        description="Машиночитаемый код ошибки, напр. 'card_not_found', 'invalid_credentials'"
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    login: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: Optional[str] = None


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
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


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

class CardCreate(BaseModel):
    """Ручное создание карточки — сразу попадает в конец очереди learning."""
    topic_id: int
    type: CardType
    front_content: str = Field(min_length=1)
    back_content: str = Field(min_length=1)


class CardUpdate(BaseModel):
    front_content: Optional[str] = Field(default=None, min_length=1)
    back_content: Optional[str] = Field(default=None, min_length=1)


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


class DraftActionResponse(BaseModel):
    """Ответ на approve/reject черновика."""
    id: int
    status: CardStatus
    message: str


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------

class Exercise(BaseModel):
    """Сгенерированное упражнение для текущей карточки.

    kind: тип упражнения (см. ExerciseKind в фронтовых типах).
    payload: структура зависит от kind —
      multiple_choice: {"options": [...], "prompt": str}
      text_input: {"prompt": str}
      fill_blank: {"template": "git {{blank}} origin", "answer_length": int}
      order_steps: {"shuffled_steps": [...]}
      и т.д.
    """
    kind: str
    payload: dict[str, Any]


class ExerciseAttempt(BaseModel):
    card_id: int
    exercise_kind: str
    answer: Any = Field(description="str для текстовых, list[str] для order_steps и т.п.")
    used_hint: bool = False
    response_time_ms: Optional[int] = None


class AttemptResult(BaseModel):
    correct: bool
    consecutive_correct: int
    required_consecutive: int = 3
    exercise_mastered: bool
    card_mastered: bool
    correct_answer: Optional[Any] = Field(
        default=None, description="Правильный ответ (возвращается при ошибке)"
    )
    next_exercise: Optional[Exercise] = None


class LearningStateResponse(BaseModel):
    topic_id: int
    current_card: Optional[CardResponse]
    exercise: Optional[Exercise] = Field(
        default=None, description="Текущее упражнение для current_card"
    )
    reviews_due: int = 0
    cards_total: int = 0
    cards_mastered: int = 0
    progress_percent: float = 0.0


# ---------------------------------------------------------------------------
# Reviews (интервальные повторения)
# ---------------------------------------------------------------------------

class ReviewResponse(BaseModel):
    id: int
    card_id: int
    scheduled_at: datetime
    interval_days: int
    card: Optional[CardResponse] = None

    class Config:
        from_attributes = True


class ReviewCompleteRequest(BaseModel):
    success: bool
    response_time_ms: Optional[int] = None


class ReviewCompleteResponse(BaseModel):
    id: int
    card_id: int
    success: bool
    next_review_at: Optional[datetime] = Field(
        default=None, description="При success — дата следующего повтора"
    )
    card_returned_to_learning: bool = Field(
        default=False, description="При fail — карточка вернулась в обучение"
    )
