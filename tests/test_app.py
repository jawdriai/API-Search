import os
import pytest
import httpx
from fastapi.testclient import TestClient

os.environ.setdefault("EXT_API_BASE_URL", "http://localhost:8099")
os.environ.setdefault("EXT_API_TOKEN", "dev-token-123")


@pytest.fixture(autouse=True)
def patch_external_client(monkeypatch):
    from mock_external.main import app as mock_app
    from app.client import ExternalApiClient
    from app.config import get_settings

    def new_init(self):  # type: ignore[no-redef]
        settings = get_settings()
        self._token = settings.ext_api_token
        # Route all httpx calls to the in-process mock FastAPI app using AsyncClient
        self._client = httpx.AsyncClient(
            base_url="http://testserver",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
            transport=httpx.ASGITransport(app=mock_app),
            timeout=httpx.Timeout(10.0, read=10.0, write=10.0, connect=5.0),
        )

    monkeypatch.setattr(ExternalApiClient, "__init__", new_init, raising=True)


@pytest.fixture()
def web():
    from app.main import app as web_app
    return TestClient(web_app)


def test_health(web: TestClient):
    res = web.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_items_page(web: TestClient):
    res = web.get("/items")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert {"id", "name"}.issubset(set(data[0].keys()))


def test_list_all_items(web: TestClient):
    res = web.get("/items", params={"all": True, "page_size": 40})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 100


def test_create_item(web: TestClient):
    res = web.post("/items", json={"name": "Interview Item"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Interview Item"
    assert isinstance(body["id"], int)

