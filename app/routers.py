from typing import List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from .client import ExternalApiClient, ExternalItem


router = APIRouter()


class CreateItemRequest(BaseModel):
    name: str


@router.get("/items", response_model=List[ExternalItem])
async def list_items(all: bool = Query(default=False), page_size: int = Query(default=25)):
    client = ExternalApiClient()
    if all:
        items: List[ExternalItem] = []
        async for it in client.list_all_items(page_size=page_size):
            items.append(it)
        return items
    page = await client.list_items_page(page_size=page_size)
    return page.items


@router.post("/items", response_model=ExternalItem, status_code=201)
async def create_item(payload: CreateItemRequest):
    client = ExternalApiClient()
    return await client.create_item(payload.name)

