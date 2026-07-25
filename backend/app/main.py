from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="LearnFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "learnflow"}


# Routers will be included here:
# from app.api import auth, topics, cards, learning
# app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
# app.include_router(cards.router, prefix="/api/cards", tags=["cards"])
# app.include_router(learning.router, prefix="/api/learning", tags=["learning"])
