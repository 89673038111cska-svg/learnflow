from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cards, learning, reviews, topics
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import LoggingMiddleware

setup_logging()
logger = get_logger("app")

app = FastAPI(title="LearnFlow API", version="0.1.0")

register_error_handlers(app)
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(
    cards.topic_cards_router, prefix="/api/topics", tags=["cards"]
)
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "learnflow"}
