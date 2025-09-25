from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock External API")


class Item(BaseModel):
    id: int
    name: str


FAKE_DB = [
    {"id": i, "name": f"Item {i}"} for i in range(1, 101)
]

EXPECTED_TOKEN = "dev-token-123"


def _require_bearer_token(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/items")
def list_items(
    authorization: Optional[str] = Header(None),
    page_size: int = 25,
    cursor: Optional[int] = None,
):
    _require_bearer_token(authorization)

    start_index = 0
    if cursor is not None:
        # cursor is the index to resume from
        start_index = cursor

    end_index = min(start_index + page_size, len(FAKE_DB))
    items = FAKE_DB[start_index:end_index]
    next_cursor = end_index if end_index < len(FAKE_DB) else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "count": len(items),
    }


class CreateItemRequest(BaseModel):
    name: str


@app.post("/items", status_code=201)
def create_item(payload: CreateItemRequest, authorization: Optional[str] = Header(None)):
    _require_bearer_token(authorization)

    new_id = len(FAKE_DB) + 1
    item = {"id": new_id, "name": payload.name}
    FAKE_DB.append(item)
    return item

