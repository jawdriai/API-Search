## FastAPI External API Practice

This is a small practice project to simulate an interview-style task: build a service that interacts with an external API securely and robustly.

### Features
- FastAPI app exposing endpoints to list and create items
- `httpx` client with timeouts and retries
- Mock external API with bearer auth and cursor pagination
- Pydantic-based validation
- Minimal tests

### Getting started
1. Create a `.env` from the example:
   ```bash
   cp .env.example .env
   ```
2. Create and activate a virtualenv (recommended) and install deps:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the mock external API and the app in separate shells:
   ```bash
   uvicorn mock_external.main:app --reload --port 8099
   uvicorn app.main:app --reload --port 8000
   ```

### Environment variables
- `EXT_API_BASE_URL`: Base URL of the external API (default `http://localhost:8099`)
- `EXT_API_TOKEN`: Bearer token used to authenticate against the external API

### Endpoints (our app)
- `GET /items`: Lists items by calling the external API, follows pagination when `all=true`
- `POST /items`: Creates an item through the external API

### Tests
```bash
pytest -q
```

