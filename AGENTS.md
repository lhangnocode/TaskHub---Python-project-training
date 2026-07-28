# AGENTS.md - TaskHub AI Guidance & Development Standards

This document establishes the architecture rules, coding standards, tool workflows, and boundaries for AI agents and human developers working on the **TaskHub** repository.

---

## 1. Project Stack

- **Language & Runtime**: Python 3.12+
- **Dependency Manager**: `uv` (Fast Python package installer & resolver)
- **Web Framework**: FastAPI (Async-first)
- **Database & ORM**: PostgreSQL 16 + SQLAlchemy 2.0 (Async Engine via `asyncpg`)
- **Database Migrations**: Alembic
- **Caching**: Redis 7 (`redis-py` asyncio)
- **Background Tasks & Emails**: `FastAPI-Mail` + FastAPI `BackgroundTasks`
- **Authentication & Security**: JWT (`python-jose`), Passlib (Bcrypt)
- **Data Validation & Serialization**: Pydantic v2
- **Containerization**: Docker & Docker Compose
- **Linting & Type Checking**: Ruff & MyPy

---

## 2. Development Commands (`uv` based)

All commands MUST be executed via `uv`. Do NOT use `pip` directly.

| Task | Command |
| :--- | :--- |
| **Install Dependencies** | `uv sync` |
| **Add Runtime Package** | `uv add <package_name>` |
| **Add Dev Package** | `uv add --dev <package_name>` |
| **Run Dev Server** | `uv run uvicorn src.main:app --reload` |
| **Docker Stack Up** | `docker compose up -d --build` |
| **Docker Stack Down** | `docker compose down` |
| **Linting Check** | `uvx ruff check .` |
| **Formatting Check** | `uvx ruff format --check .` |
| **Type Check** | `uv run mypy src/` |
| **Run Tests** | `uv run pytest` |
| **Generate Migration** | `uv run alembic revision --autogenerate -m "message"` |
| **Apply Migrations** | `uv run alembic upgrade head` |
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc UI** | `http://localhost:8000/redoc` |

---

## 3. Coding Standards

- **Layered Architecture**: Strictly follow `Router -> Service -> Repository -> Database`.
- **Async-First**: All database access, network calls, and I/O operations MUST use `async` / `await`.
- **No Blocking I/O**: Never perform synchronous blocking operations (e.g. `time.sleep()`, synchronous `requests`, blocking file reads) inside async routes.
- **SQLAlchemy 2.x Style**: Always use `Mapped[T]`, `mapped_column()`, and modern `select()` syntax.
- **Pydantic v2**: Use `model_config = ConfigDict(from_attributes=True)` and `model_validate()` / `model_dump()`.
- **Dependency Injection**: Use FastAPI `Depends()` for DB sessions, authenticated users, and permission guards.
- **Strict Typing**: Type annotations are **REQUIRED** for every function signature and return type.
- **Ruff & MyPy Clean**: Code must pass `ruff check .` with 0 warnings and `mypy src/` with 0 type errors.

---

## 4. Architecture Constraints

To maintain a maintainable and clean codebase, enforce these strict layer boundaries:

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

### Layer Responsibilities & Rules
1. **Routers**:
   - MUST NOT execute raw SQL or direct SQLAlchemy queries.
   - MUST call Service methods or Repository functions.
2. **Services**:
   - Handle business rules, Redis caching logic, and background email dispatch.
   - MUST NOT import other Services directly (decouple using shared repositories or dependencies).
3. **Repositories**:
   - Manage data fetching, pagination, and filters.
   - Repositories MUST NOT call `commit()` internally; transactions are committed at the Service / route boundary.

---

## 5. Boundaries (Do Not Carelessly Modify)

The following files contain critical infrastructure configuration. AI agents MUST NOT modify them without explicit user consent:

- `.env` and `.env.example`
- `uv.lock`
- Generated database migrations (`alembic/versions/*`)
- Docker setup (`Dockerfile`, `docker-compose.yml`)
- CI/CD workflows (`.github/workflows/*`)

---

## 6. Git Workflow

- **Conventional Commits**: Format commit messages as `type(scope): description` (e.g., `feat(auth): add refresh token endpoint`, `fix(task): invalidate cache on delete`).
- **Branch Naming**: Use feature/fix prefix (e.g., `feat/rbac-permissions`, `fix/redis-cache-key`).
- **Squash Merge**: PRs are merged into `main` using squash merge.
- **No Secrets**: Never commit `.env` files, JWT secrets, or DB credentials.

---

## 7. AI Agent Instructions

When acting as an AI assistant on this project:

1. **Read `AGENTS.md` First**: Always inspect `AGENTS.md` before generating or modifying code.
2. **Reuse Existing Patterns**: Align with existing file structure, models, schemas, and error handlers.
3. **Avoid Unnecessary Refactoring**: Only modify files necessary for the given task.
4. **No Unapproved Libraries**: Do not introduce new dependencies into `pyproject.toml` without explicit user permission.
5. **Update Documentation**: Keep OpenAPI docs, docstrings, and plan artifacts updated when behavior changes.
6. **Incremental Milestones**: Complete one milestone at a time. After completing a milestone, provide a review summary and wait for user approval before moving to the next.

---

## 8. `uv` Rules

- **`uv` is the ONLY dependency manager**.
- **NEVER** use `pip`, `pip3`, `pipenv`, or `poetry`.
- **NEVER** create `requirements.txt`.
- **NEVER** manually edit `uv.lock` (let `uv` update it automatically via `uv add` or `uv sync`).
