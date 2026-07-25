"""CRUD тем. Логика — в issue #5, сейчас 501."""
from typing import Any

from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.schemas import ErrorResponse, TopicCreate, TopicResponse, TopicUpdate

router = APIRouter()

NOT_IMPLEMENTED = AppError(501, "not_implemented", "Topics CRUD будет реализован в issue #5")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
}


@router.get("", response_model=list[TopicResponse], responses=ERROR_RESPONSES)
async def list_topics():
    raise NOT_IMPLEMENTED


@router.post("", response_model=TopicResponse, status_code=201, responses=ERROR_RESPONSES)
async def create_topic(_: TopicCreate):
    raise NOT_IMPLEMENTED


@router.get("/{topic_id}", response_model=TopicResponse, responses=ERROR_RESPONSES)
async def get_topic(topic_id: int):
    raise NOT_IMPLEMENTED


@router.patch("/{topic_id}", response_model=TopicResponse, responses=ERROR_RESPONSES)
async def update_topic(topic_id: int, _: TopicUpdate):
    raise NOT_IMPLEMENTED


@router.delete("/{topic_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_topic(topic_id: int):
    raise NOT_IMPLEMENTED
