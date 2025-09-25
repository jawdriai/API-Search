from typing import Any, Dict, AsyncIterator, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel
from .config import get_settings


class ExternalItem(BaseModel):
    id: int
    name: str


class ExternalListResponse(BaseModel):
    items: List[ExternalItem]
    next_cursor: Optional[int] = None
    count: int


class ExternalApiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.ext_api_token
        self._client = httpx.AsyncClient(
            base_url=str(settings.ext_api_base_url),
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            timeout=httpx.Timeout(10.0, read=10.0, write=10.0, connect=5.0),
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        response = await self._client.get(path, params=params)
        if response.status_code in {500, 502, 503, 504, 429}:
            response.raise_for_status()
        if not response.is_success:
            response.raise_for_status()
        return response

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def _post(self, path: str, json: Dict[str, Any]) -> httpx.Response:
        response = await self._client.post(path, json=json)
        if response.status_code in {500, 502, 503, 504, 429}:
            response.raise_for_status()
        if not response.is_success:
            response.raise_for_status()
        return response

    async def list_items_page(self, page_size: int = 25, cursor: Optional[int] = None) -> ExternalListResponse:
        params: Dict[str, Any] = {"page_size": page_size}
        if cursor is not None:
            params["cursor"] = cursor
        res = await self._get("/items", params=params)
        return ExternalListResponse.model_validate(res.json())

    async def list_all_items(self, page_size: int = 50) -> AsyncIterator[ExternalItem]:
        next_cursor: Optional[int] = None
        while True:
            page = await self.list_items_page(page_size=page_size, cursor=next_cursor)
            for item in page.items:
                yield item
            if page.next_cursor is None:
                break
            next_cursor = page.next_cursor

    async def create_item(self, name: str) -> ExternalItem:
        res = await self._post("/items", json={"name": name})
        return ExternalItem.model_validate(res.json())

