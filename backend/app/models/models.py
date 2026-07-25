import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CardType(str, enum.Enum):
    TERM = "term"
    COMMAND = "command"
    PROCEDURE = "procedure"


class CardStatus(str, enum.Enum):
    DRAFT = "draft"
    LEARNING = "learning"
    MASTERED = "mastered"


class CardSource(str, enum.Enum):
    MANUAL = "manual"
    AI = "ai"
    MCP = "mcp"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    topics: Mapped[list["Topic"]] = relationship(back_populates="user")


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="topics")
    cards: Mapped[list["Card"]] = relationship(back_populates="topic", order_by="Card.order_index")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    type: Mapped[CardType] = mapped_column(Enum(CardType))
    status: Mapped[CardStatus] = mapped_column(Enum(CardStatus), default=CardStatus.DRAFT)
    source: Mapped[CardSource] = mapped_column(Enum(CardSource), default=CardSource.MANUAL)
    front_content: Mapped[str] = mapped_column(Text)  # вопрос / термин / задача
    back_content: Mapped[str] = mapped_column(Text)   # ответ / определение / решение (JSON для сложных типов)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    topic: Mapped["Topic"] = relationship(back_populates="cards")
    progress: Mapped[list["CardProgress"]] = relationship(back_populates="card")
    reviews: Mapped[list["Review"]] = relationship(back_populates="card")


class CardProgress(Base):
    """Прогресс по каждому типу упражнения для карточки."""
    __tablename__ = "card_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    exercise_type: Mapped[str] = mapped_column(String(64))  # multiple_choice, text_input, fill_blank, ...
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_session_id: Mapped[int | None] = mapped_column(ForeignKey("learning_sessions.id"), nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    card: Mapped["Card"] = relationship(back_populates="progress")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)

    card: Mapped["Card"] = relationship(back_populates="reviews")


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
