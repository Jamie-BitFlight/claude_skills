# FastAPI

| Field         | Value                                                              |
| ------------- | ------------------------------------------------------------------ |
| Research Date | 2026-02-05                                                         |
| Primary URL   | <https://fastapi.tiangolo.com/>                                    |
| GitHub        | <https://github.com/fastapi/fastapi>                               |
| PyPI          | <https://pypi.org/project/fastapi/>                                |
| Version       | 0.128.1 (released 2026-02-04)                                      |
| License       | MIT                                                                |
| Author        | Sebastian Ramirez (tiangolo)                                       |
| Discord       | <https://discord.gg/VQjSZaeJmf>                                    |
| Discussions   | <https://github.com/fastapi/fastapi/discussions>                   |
| Managed       | <https://fastapicloud.com/> (FastAPI Cloud - official hosting)     |

---

## Overview

FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. Built on Starlette (ASGI framework) and Pydantic (data validation), FastAPI achieves performance comparable to NodeJS and Go while providing automatic API documentation, data validation, and editor support through Python's type system.

---

## Problem Addressed

| Problem                                           | Solution                                                                     |
| ------------------------------------------------- | ---------------------------------------------------------------------------- |
| API development requires verbose boilerplate      | Declare types once; get validation, docs, serialization automatically        |
| Manual API documentation gets out of sync         | Automatic OpenAPI/Swagger UI and ReDoc generated from code                   |
| Data validation requires custom code              | Pydantic models validate request/response data with Python types             |
| Async support in Python frameworks is complex     | Native async/await with Starlette's ASGI foundation                          |
| Editor support for API development is limited     | Type hints enable autocomplete, type checking, and refactoring               |
| Learning new framework syntax is time-consuming   | Uses standard Python types - no framework-specific DSL to learn              |
| Security patterns (OAuth2, JWT) need manual impl  | Built-in security utilities with OpenAPI integration                         |
| Dependency injection requires external libraries  | Native dependency injection system with hierarchical scopes                  |

---

## Key Statistics

| Metric            | Value                     | Date Gathered |
| ----------------- | ------------------------- | ------------- |
| GitHub Stars      | 94,804                    | 2026-02-05    |
| GitHub Forks      | 8,628                     | 2026-02-05    |
| Open Issues       | 202                       | 2026-02-05    |
| Contributors      | 460+                      | 2026-02-05    |
| Primary Language  | Python                    | 2026-02-05    |
| Repository Age    | Since December 2018       | 2026-02-05    |
| Python Versions   | 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 | 2026-02-05 |

---

## Key Features

### Core Framework

- **Type-Based Validation**: Declare parameter types with Python type hints; automatic validation and serialization
- **Automatic Documentation**: Swagger UI at `/docs`, ReDoc at `/redoc` - always in sync with code
- **OpenAPI Standard**: Full OpenAPI 3.x and JSON Schema compliance for interoperability
- **ASGI Foundation**: Built on Starlette for high-performance async request handling
- **Pydantic Integration**: Deep integration with Pydantic v2 for data models and settings

### Performance

- **High Throughput**: Performance comparable to Go and NodeJS (Starlette + uvloop)
- **Async Native**: Full async/await support for concurrent I/O operations
- **Efficient Serialization**: Pydantic v2's Rust-based core for fast validation

### Developer Experience

- **Editor Support**: Autocomplete, type checking, inline errors in IDEs (VS Code, PyCharm)
- **Minimal Boilerplate**: ~200-300% faster development vs traditional frameworks (per internal studies)
- **Standards-Based**: No new syntax to learn - uses standard Python type hints
- **FastAPI CLI**: Development server with auto-reload (`fastapi dev`) and production mode (`fastapi run`)

### Dependency Injection

- **Hierarchical DI**: Declare dependencies as function parameters; automatic resolution
- **Scoped Dependencies**: Request-scope, session-scope, and application-scope support
- **Testability**: Easy dependency override for testing without mocking

### Security

- **OAuth2 Flows**: Built-in support for password, client credentials, authorization code flows
- **JWT/Bearer**: Token-based authentication with OpenAPI integration
- **API Keys**: Header, query, and cookie-based API key support
- **CORS**: Configurable Cross-Origin Resource Sharing middleware

### Request/Response Handling

- **Path Parameters**: Type-validated URL path extraction
- **Query Parameters**: Optional/required query strings with defaults
- **Request Bodies**: JSON body parsing with Pydantic validation
- **Form Data**: multipart/form-data and application/x-www-form-urlencoded
- **File Uploads**: Single and multiple file handling with streaming
- **Response Models**: Automatic serialization and filtering of output data
- **Status Codes**: Declarative HTTP status code handling
- **Background Tasks**: Queue tasks to run after response is sent

### WebSocket Support

- **WebSocket Routes**: Native WebSocket endpoint handling
- **Connection Management**: Accept, receive, send, close lifecycle
- **Dependency Injection**: Same DI system works for WebSocket routes

### Testing

- **TestClient**: Starlette's test client for synchronous testing
- **HTTPX Integration**: Async testing with HTTPX's AsyncClient
- **Dependency Override**: Replace dependencies during tests

---

## Technical Architecture

### Stack Components

| Component       | Technology                                                 |
| --------------- | ---------------------------------------------------------- |
| ASGI Server     | Uvicorn (with uvloop for performance)                      |
| Web Framework   | Starlette (routing, middleware, WebSocket)                 |
| Data Validation | Pydantic v2 (Rust-based core)                              |
| Type Hints      | Python typing module + typing-extensions                   |
| Serialization   | Pydantic's JSON encoder + orjson optional                  |
| Documentation   | OpenAPI 3.x spec generation                                |

### Request Flow

```text
Client Request
      |
  Uvicorn (ASGI Server)
      |
  Starlette Middleware Stack
      |
  FastAPI Router
      |
  Dependency Resolution
      |
  Parameter Extraction & Validation (Pydantic)
      |
  Endpoint Function Execution
      |
  Response Model Validation (Pydantic)
      |
  JSON Serialization
      |
Client Response
```

### Core Dependencies

```text
fastapi
├── starlette>=0.40.0    # ASGI framework (routing, middleware, WebSocket)
├── pydantic>=2.7.0      # Data validation and settings
├── typing-extensions    # Backported typing features
└── annotated-doc        # Documentation extraction from Annotated types
```

### Optional Dependencies (standard extra)

```text
fastapi[standard]
├── uvicorn[standard]    # ASGI server with uvloop
├── httpx                # Test client
├── jinja2               # HTML templates
├── python-multipart     # Form/file uploads
├── email-validator      # Email field validation
├── pydantic-settings    # Environment-based settings
└── fastapi-cli          # Dev/prod server commands
```

---

## Installation and Usage

### Installation

```bash
# Basic installation
pip install fastapi

# With standard dependencies (recommended)
pip install "fastapi[standard]"

# Using uv
uv pip install "fastapi[standard]"

# Add to pyproject.toml
dependencies = ["fastapi[standard]>=0.128.0"]
```

### Minimal Example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
```

### Running the Server

```bash
# Development mode (auto-reload)
fastapi dev main.py

# Production mode
fastapi run main.py

# Or directly with Uvicorn
uvicorn main:app --reload
```

### Request Body with Pydantic

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.post("/items/")
def create_item(item: Item):
    return {"item_name": item.name, "price": item.price}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_id": item_id, **item.model_dump()}
```

### Dependency Injection

```python
from fastapi import FastAPI, Depends
from typing import Annotated

app = FastAPI()

async def get_db():
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Annotated[Database, Depends(get_db)]):
    return db.get_user(user_id)
```

### OAuth2 with JWT

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Validate credentials, return JWT
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(token: Annotated[str, Depends(oauth2_scheme)]):
    user = decode_token(token)
    return user
```

### Background Tasks

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

def send_notification(email: str, message: str):
    # Send email in background
    pass

@app.post("/notify/{email}")
async def notify(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_notification, email, "Welcome!")
    return {"message": "Notification queued"}
```

### WebSocket Endpoint

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

---

## Relevance to Claude Code Development

### Direct Applications

1. **MCP Server Foundation**: FastMCP and many MCP server implementations use FastAPI as their HTTP layer. Understanding FastAPI patterns is essential for building and debugging MCP servers.

2. **Tool Backend Development**: When Claude Code skills need to call external services, those services are frequently FastAPI applications. Knowing the framework aids in integration and troubleshooting.

3. **Ray Serve Integration**: Ray Serve has native FastAPI integration for model serving. FastAPI deployments pattern directly translate to Ray Serve MCP gateways.

4. **Pydantic Alignment**: FastAPI's Pydantic-based data validation aligns with Claude Code's Python conventions. Pydantic models defined for FastAPI can be reused in skills and agents.

5. **API Documentation for Agents**: FastAPI's automatic OpenAPI generation provides machine-readable API specs that AI agents can consume for tool discovery.

### Patterns Worth Adopting

1. **Type Hints as Specification**: FastAPI's approach of using Python types as the single source of truth for validation, serialization, and documentation is applicable to skill parameter definitions.

2. **Dependency Injection Pattern**: FastAPI's DI system provides clean patterns for managing resources (database connections, API clients) that skills can adopt for managing MCP tool dependencies.

3. **Response Models for Output Control**: Explicit response models ensure only intended data is returned - relevant for controlling what information skills expose.

4. **Background Tasks Pattern**: FastAPI's background task queue is useful for fire-and-forget operations in skills (logging, analytics, notifications).

5. **Middleware Chains**: FastAPI/Starlette middleware patterns inform how to structure pre/post processing in agent workflows.

### Integration Opportunities

1. **FastMCP Server Development**: Build MCP servers using FastMCP (which wraps FastAPI) for tool implementations.

2. **Skill-to-API Bridge**: Create FastAPI services that expose skill functionality via HTTP for non-Claude-Code clients.

3. **Webhook Receivers**: FastAPI excels at receiving webhooks from external services (GitHub, Slack, etc.) for agent triggers.

4. **OpenAPI-to-Skill Generation**: FastAPI's OpenAPI output could feed skill generators that create Claude Code skills from API specs.

5. **Testing Infrastructure**: FastAPI's TestClient patterns apply to testing MCP servers and skill implementations.

### Comparison with Related Tools

| Aspect              | FastAPI                          | Flask                       | Django REST Framework       |
| ------------------- | -------------------------------- | --------------------------- | --------------------------- |
| Performance         | High (Starlette + uvloop)        | Moderate (WSGI)             | Moderate (WSGI)             |
| Async Support       | Native                           | Limited (Flask 2.0+)        | Limited                     |
| Type Validation     | Native (Pydantic)                | Manual/extensions           | Serializers                 |
| Auto Documentation  | Built-in (OpenAPI)               | Extensions (Flask-RESTX)    | Built-in (DRF)              |
| Learning Curve      | Low (Python types)               | Low                         | Higher (Django ecosystem)   |
| MCP Server Support  | FastMCP integration              | Manual                      | Manual                      |

---

## Enterprise Adoption

FastAPI is used in production by major organizations:

- **Microsoft**: ML services, integrated into Windows and Office products
- **Netflix**: Dispatch (crisis management orchestration framework)
- **Uber**: Ludwig ML predictions REST server
- **Cisco**: API-first development strategy, Virtual TAC Engineer

---

## References

| Source                      | URL                                                                | Accessed   |
| --------------------------- | ------------------------------------------------------------------ | ---------- |
| Official Documentation      | <https://fastapi.tiangolo.com/>                                    | 2026-02-05 |
| GitHub Repository           | <https://github.com/fastapi/fastapi>                               | 2026-02-05 |
| GitHub README               | <https://github.com/fastapi/fastapi/blob/master/README.md>         | 2026-02-05 |
| PyPI Package                | <https://pypi.org/project/fastapi/>                                | 2026-02-05 |
| pyproject.toml              | <https://github.com/fastapi/fastapi/blob/master/pyproject.toml>    | 2026-02-05 |
| GitHub API (stats)          | <https://api.github.com/repos/fastapi/fastapi>                     | 2026-02-05 |
| FastAPI Cloud               | <https://fastapicloud.com/>                                        | 2026-02-05 |
| Typer (sister project)      | <https://typer.tiangolo.com/>                                      | 2026-02-05 |
| FastMCP                     | <https://github.com/jlowin/fastmcp>                                | 2026-02-05 |

**Research Method**: Information gathered from official GitHub repository README, GitHub API (stars, forks, issues, contributors), PyPI metadata, and pyproject.toml dependencies. Enterprise adoption quotes verified from README testimonials with linked references.

---

## Freshness Tracking

| Field              | Value                               |
| ------------------ | ----------------------------------- |
| Version Documented | 0.128.1                             |
| Release Date       | 2026-02-04                          |
| GitHub Stars       | 94,804 (as of 2026-02-05)           |
| Next Review Date   | 2026-05-05                          |

**Review Triggers**:

- Major version release (1.0.0)
- Significant MCP/FastMCP integration updates
- GitHub stars milestone (100K)
- Breaking changes to core APIs (routing, DI, Pydantic integration)
- New async features or performance improvements
- FastAPI Cloud general availability changes
