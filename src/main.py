from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.api.v1.router import api_v1_router
from src.config import settings
from src.core.exceptions import (
    global_unhandled_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.core.middleware import RequestLoggingMiddleware
from src.redis_client import close_redis_client, get_redis_client

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("taskhub")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up TaskHub REST API backend service...")
    try:
        redis_conn = await get_redis_client()
        await redis_conn.ping()
        logger.info("Successfully connected to Redis instance")
    except Exception as exc:
        logger.warning("Redis ping on startup failed: %s", exc)

    yield

    logger.info("Shutting down TaskHub REST API backend service...")
    await close_redis_client()
    logger.info("Redis connection closed cleanly")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="TaskHub API - Enterprise Task & Project Management Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Custom Middlewares
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
app.add_exception_handler(HTTPException, http_exception_handler) # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler) # type: ignore[arg-type]
app.add_exception_handler(Exception, global_unhandled_exception_handler)

# Attach API v1 routes
app.include_router(api_v1_router)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter JWT Bearer token format: `Bearer <JWT_TOKEN>`",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}
