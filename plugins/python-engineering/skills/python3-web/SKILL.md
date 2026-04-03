---
name: python3-web
description: Python web and API development with strong request boundaries, typed validation, and maintainable service design. Activates on FastAPI, Starlette, Django, Flask, HTTP endpoints, request models, authentication flows, or web framework tasks.
user-invocable: false
---

# Python Web

Load `python3-core` for standing defaults. Load `python3-typing` for request/response modeling. Load `python3-testing` for endpoint and auth tests.

## Quality Checklist

- [ ] Route handlers contain NO business logic — only validation, delegation, response mapping
- [ ] No framework objects (`Request`, `Response`, ORM models) leak into domain layer
- [ ] `model_config = {"strict": True}` on all request models
- [ ] Separate request and response models per endpoint — never reuse ORM models as API schemas
- [ ] Auth resolved at edge; domain functions receive typed identity, never raw tokens
- [ ] Domain exceptions mapped to HTTP status codes at boundary, not scattered through handlers
- [ ] Async handlers use `httpx.AsyncClient` — never `requests` (blocks event loop)
- [ ] Background tasks hold no references to request-scoped objects

## Gotchas

| Trap | What to do instead |
|---|---|
| FastAPI dep ordering assumptions | Dependencies resolve by graph, not definition order — chain explicitly if order matters |
| Pydantic v1/v2 method mixing | v2: `model_dump()`, `model_dump_json()`, `model_validate()` — never `.dict()` / `.json()` |
| `import requests` in async handler | `requests` blocks event loop; use `httpx.AsyncClient` with `async with` |
| Django ORM in async views | Bare `Model.objects.get()` blocks; use `aget()` (Django 4.1+) or `sync_to_async` |
| `allow_origins=["*"]` | Enumerate specific origins — `*` disables credential support, security risk |
| Single model for request + response + DB | Three separate models: `CreateUserRequest`, `UserResponse`, `UserDB` |

## Decision Table: Sync vs Async

| Scenario | Use | Why |
|---|---|---|
| CPU-bound processing | Sync + thread pool | `async` doesn't help CPU work |
| Multiple external API calls | Async + `httpx.AsyncClient` | Concurrent I/O without threads |
| Simple CRUD with sync ORM | Sync handlers | Async adds complexity with no benefit |
| WebSocket connections | Async (required) | Inherently long-lived |

## Layer Separation

```text
HTTP Layer (routes) → validated typed request models
Domain Layer (logic) → typed domain objects
Data Layer (repo/ORM)
```
