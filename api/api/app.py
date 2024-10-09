import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID, uuid4

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi import status as fastapi_status
from fastapi.middleware import Middleware

from api.config.logger import LoggerMiddleware
from api.config.psql import get_psql_conn
from api.config.settings import env, logger
from api.dependencies import (
    ItemModel,
    PaginatedResponse,
    PostItemsRequest,
    random_sleep,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"FastAPI running on http://{env.HOST}:{env.PORT} (Press CTRL+C to quit)"
    )
    yield
    logger.info("FastAPI shutdown complete")


app = FastAPI(
    description="The API description goes here",
    lifespan=lifespan,
    middleware=[
        Middleware(CorrelationIdMiddleware),
        Middleware(LoggerMiddleware, logger=logger),
    ],
    title=f"{env.APP_NAME} FastAPI",
    version=env.APP_VERSION,
)


@app.post("/items/")
async def post_items(
    item: PostItemsRequest | None = None,
    sleep: bool = True,
    psql_conn=Depends(get_psql_conn),
):
    if sleep:
        await random_sleep()

    if item is None:
        logger.debug("item is None and creating a random item")
        item = PostItemsRequest()

    new_item = ItemModel(
        id=uuid4(),
        name=item.name,
        description=item.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    logger.info("new_item", extra={"new_item": new_item})

    new_value = await psql_conn.fetch(
        "insert into items (id, name, description, created_at, updated_at) values ($1, $2, $3, $4, $5) returning *",
        new_item.id,
        new_item.name,
        new_item.description,
        new_item.created_at,
        new_item.updated_at,
    )
    logger.info("new_value", extra={"new_value": new_value})

    return new_value[0]


@app.get("/items/{id}")
async def get_items_id(id: UUID, sleep: bool = True, psql_conn=Depends(get_psql_conn)):
    if sleep:
        await random_sleep()

    value = await psql_conn.fetch("select * from items where id = $1", id)
    logger.info("get_items_id", extra={"id": id, "item": value})

    if not value:
        logger.error(f"item not found: {id}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND, detail="item not found"
        )

    return value[0]


@app.get("/items/")
async def get_items(
    sleep: bool = True,
    page: int = Query(1, ge=1, description="Page number"),
    page_items: int = Query(10, ge=1, le=100, description="Items per page"),
    psql_conn=Depends(get_psql_conn),
):
    if sleep:
        await random_sleep()

    offset = (page - 1) * page_items

    values = await psql_conn.fetch(
        "select * from items order by created_at limit $1 offset $2", page_items, offset
    )
    logger.info("get_items", extra={"items": values})

    total_items = await psql_conn.fetchval("select count(*) from items")
    total_pages = math.ceil(total_items / page_items)

    items = [
        ItemModel(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in values
    ]

    paginated_response = PaginatedResponse(
        items=items,
        page=page,
        page_items=page_items,
        total_items=total_items,
        total_pages=total_pages,
    )
    logger.info("paginated_response", extra={"paginated_response": paginated_response})

    return paginated_response


@app.get("/health", status_code=fastapi_status.HTTP_204_NO_CONTENT)
async def health():
    pass
