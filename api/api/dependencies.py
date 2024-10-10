import asyncio
import random
from datetime import datetime
from typing import List
from uuid import UUID

import aiobotocore.session
from faker import Faker
from pydantic import BaseModel, Field

from api.config.settings import logger

fake = Faker()


async def get_aiobotocore_session():
    return aiobotocore.session.get_session()


async def random_sleep():
    sleep_time: int = random.randint(1, 10)
    logger.info(f"sleeping for {sleep_time} seconds")
    await asyncio.sleep(sleep_time)


class ItemModel(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PostItemsRequest(BaseModel):
    name: str = Field(default_factory=lambda: fake.slug())
    description: str = Field(default_factory=lambda: fake.bs())

    model_config = {"json_schema_extra": {"examples": [{}]}}


class PaginatedResponse(BaseModel):
    items: List[ItemModel]
    page: int
    page_items: int
    total_items: int
    total_pages: int
