# TaskHub - Async FastAPI Project Management & Collaboration REST API

TaskHub is a production-grade, high-performance async REST API for project management, workspace collaboration, role-based access control (RBAC), task tracking, comments, labels, background notifications, and Redis caching.

Built with **Python 3.12+**, **FastAPI**, **SQLAlchemy 2.0 Async (PostgreSQL 16)**, **Redis 7**, **Alembic**, and **Pydantic v2**. Managed strictly via **uv**.

---

## 🚀 Features

- 🔐 **Authentication & Token Blacklisting**: JWT Access & Refresh tokens, Passlib/Bcrypt password hashing, and SHA-256 Redis token revocation blacklist upon logout.
- 👥 **Workspaces & RBAC**: Granular role hierarchy (`OWNER: 40`, `ADMIN: 30`, `EDITOR: 20`, `VIEWER: 10`) with permission guards across workspace, project, task, and comment resources.
- 📁 **Projects & Archiving**: Project management under workspaces with archiving support (`is_archived`).
- ✅ **Task Management & Filtering**: Task CRUD with status (`TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`), priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), assignee filtering, and page/limit pagination.
- 🏷️ **Labels & Comments**: Workspace-level custom labels, task label attachment/detachment, and author/admin comment moderation.
- ⚡ **Redis Caching**: Read-through caching for project tasks (`cache:project:{id}:tasks:*`) with pattern-based `SCAN` cache invalidation on task/label mutations.
- 📧 **Background Notifications**: Async background task queue dispatching email notifications via `FastAPI-Mail` on task assignment.
- 📊 **OpenAPI Docs & Correlation Logging**: Interactive Swagger UI & ReDoc with `BearerAuth` scheme, standard error schemas, and `X-Request-ID` request correlation logging.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Language & Runtime** | Python 3.12+ |
| **Dependency Manager** | `uv` (Fast Python package installer & resolver) |
| **Web Framework** | FastAPI (Async-first) |
| **Database & ORM** | PostgreSQL 16 + SQLAlchemy 2.0 Async Engine (`asyncpg`) |
| **Migrations** | Alembic |
| **Caching** | Redis 7 (`redis-py` asyncio) |
| **Email & Background Queue** | `FastAPI-Mail` + FastAPI `BackgroundTasks` |
| **Auth & Security** | JWT (`python-jose`), Passlib (`bcrypt`) |
| **Validation & Schemas** | Pydantic v2 |
| **Containerization** | Multi-stage Dockerfile & Docker Compose |
| **Code Quality** | Ruff & MyPy |

---

## 🏛️ Layered Architecture

TaskHub strictly follows a decoupled **Layered Architecture**:

```
[ HTTP Request ]
      │
      ▼
┌───────────┐
│  Router   │ ◄── Handles HTTP requests/responses, path params, response schemas
└─────┬─────┘
      │
      ▼
┌───────────┐
│  Service  │ ◄── Business logic, cache management, email dispatch, transaction boundaries
└─────┬─────┘
      │
      ▼
┌───────────┐
│ Repository│ ◄── Database queries, filter composition, pagination execution
└─────┬─────┘
      │
      ▼
┌───────────┐
│ Database  │ ◄── PostgreSQL via SQLAlchemy 2.0 Async Session
└───────────┘
```

1. **Routers** (`src/api/v1/`): Handle HTTP request routing, parameter validation, and response serialization. Must NOT execute direct SQL/SQLAlchemy queries.
2. **Services** (`src/services/`): Enforce business rules, handle Redis caching logic, and dispatch background tasks.
3. **Repositories** (`src/repositories/`): Inherit from `BaseRepository[T]` for async CRUD, pagination, and filter execution. Must NOT commit transactions internally.
4. **Models** (`src/models/`): SQLAlchemy 2.0 declarative entities using `Mapped[T]` and `mapped_column()`.

---

## 📂 Project Structure

```
TaskHub/
├── alembic/                      # Alembic async migration scripts & env configuration
│   ├── versions/                 # Database migration revisions
│   └── env.py                    # Migration discovery & execution setup
├── src/                          # Application source code
│   ├── api/                      # API Layer
│   │   ├── deps.py               # Dependency injection (db, current_user, rbac, redis)
│   │   └── v1/                   # API v1 routes (auth, users, workspaces, projects, tasks)
│   ├── core/                     # Core system utilities
│   │   ├── exceptions.py         # Custom HTTP exceptions & global handlers
│   │   ├── middleware.py         # Request logging & correlation ID middleware
│   │   ├── rbac.py               # Resource role definitions & permission logic
│   │   └── security.py           # JWT generation & password hashing
│   ├── models/                   # SQLAlchemy ORM models
│   ├── repositories/             # Data access repository layer
│   ├── schemas/                  # Pydantic v2 request/response schemas
│   ├── services/                 # Business logic services (auth, cache, email)
│   ├── config.py                 # Pydantic BaseSettings environment configuration
│   ├── database.py               # Async SQLAlchemy engine & session maker
│   ├── main.py                   # FastAPI app initialization, lifespan, & middleware
│   └── redis_client.py           # Async Redis client lifecycle
├── .env                          # Environment variables (local dev)
├── .env.example                  # Environment template
├── AGENTS.md                     # AI guidance & development standards
├── Dockerfile                    # Production-ready multi-stage Docker build
├── docker-compose.yml            # Docker stack (App, PostgreSQL 16, Redis 7)
├── pyproject.toml                # Project configuration & dependencies
├── ruff.toml                     # Ruff linter configuration
└── mypy.ini                      # MyPy strict typing configuration
```

---

## 📦 Installation & Setup (`uv`)

This project uses **`uv`** as the sole dependency manager. Do **NOT** use `pip`, `pipenv`, `poetry`, or `requirements.txt`.

### 1. Prerequisites
- Python 3.12+
- `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose (optional for containerized setup)

### 2. Clone & Install Dependencies
```bash
# Install dependencies strictly via uv
uv sync
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and adjust credentials as required:

```ini
PROJECT_NAME="TaskHub API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
DEBUG=True

# Security
SECRET_KEY="supersecretkeyforjwtsigningchangeinproduction"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PostgreSQL Database
POSTGRES_SERVER="localhost"
POSTGRES_PORT=5432
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="password"
POSTGRES_DB="taskhub"
DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/taskhub"

# Redis Cache
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_URL="redis://localhost:6379/0"

# Mail Settings (FastAPI-Mail)
MAIL_USERNAME="smtp_user"
MAIL_PASSWORD="smtp_password"
MAIL_FROM="noreply@taskhub.com"
MAIL_PORT=587
MAIL_SERVER="smtp.gmail.com"
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
```

---

## 🗄️ Database & Migration Workflow

Alembic manages database schema revisions asynchronously.

```bash
# Run PostgreSQL locally or via Docker Compose
docker compose up -d db redis

# Apply latest migrations
uv run alembic upgrade head

# Rollback last migration (if needed)
uv run alembic downgrade -1

# Generate new migration after updating ORM models
uv run alembic revision --autogenerate -m "describe_changes"
```

---

## 🐳 Docker & Docker Compose Setup

Run the full TaskHub backend stack (FastAPI App + PostgreSQL 16 + Redis 7) with multi-stage container optimization:

```bash
# Build and start services in background
docker compose up -d --build

# View container logs
docker compose logs -f app

# Stop docker stack
docker compose down
```

The app container automatically applies Alembic migrations on startup before spawning Uvicorn.

---

## 🔑 Authentication & Token Revocation

1. **Login & Registration**:
   - `POST /api/v1/auth/register`: Create user account.
   - `POST /api/v1/auth/login`: Authenticate and receive `access_token` (30 mins) and `refresh_token` (7 days).
2. **Token Refresh**:
   - `POST /api/v1/auth/refresh`: Re-issue access token using a valid, non-blacklisted refresh token.
3. **Logout & Revocation**:
   - `POST /api/v1/auth/logout`: Revokes active Bearer token and optional refresh token by writing SHA-256 hashes to Redis with TTL equal to the token's remaining lifespan.

---

## 📖 API Documentation

Once running, access interactive API documentation at:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Authentication is authorized via the `BearerAuth` scheme in Swagger UI.

---

## ⚡ Redis Caching & Invalidation Strategy

- **Tasks Query Caching**: `GET /api/v1/projects/{id}/tasks` caches responses under keys formatted as `cache:project:{id}:tasks:s={status}:p={priority}:a={assignee}:pg={page}:lim={limit}` with a 300s TTL.
- **Cache Invalidation**: Task creation, updates, deletions, and label attachments asynchronously call `invalidate_project_tasks_cache(project_id)` which uses non-blocking Redis `SCAN` to locate and purge matching task keys.

---

## 🧪 Code Quality & Developer Commands

Always run quality enforcement tools before committing:

| Task | Command |
| :--- | :--- |
| **Run Dev Server** | `uv run uvicorn src.main:app --reload` |
| **Linting Check** | `uvx ruff check .` |
| **Formatting Check** | `uvx ruff format --check .` |
| **Auto-Fix Format** | `uvx ruff format .` |
| **Strict Type Check** | `uv run mypy src/` |
| **Run Tests** | `uv run pytest` |
| **Alembic Upgrade** | `uv run alembic upgrade head` |

---

## 🏭 Production Considerations

1. **Secrets Security**: Change `SECRET_KEY` in production to a strong 64-byte random key and store securely.
2. **Database Connection Pooling**: Adjust engine pool parameters in `src/database.py` according to expected concurrency demands.
3. **HTTPS & CORS**: Restrict `allow_origins` in CORS settings to trusted production domains.
4. **Redis Persistence**: Configure Redis append-only file (AOF) or snapshotting depending on cache durability requirements.

---

## 📄 License

This project is licensed under the MIT License.
