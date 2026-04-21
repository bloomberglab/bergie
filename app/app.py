from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Startup: initialise logging, verify connections, register Telegram webhook.
    Shutdown: clean up resources.
    """
    # ── Startup ────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"API prefix: {settings.API_V1_PREFIX}")

    yield  # app is running

    # ── Shutdown ───────────────────────────────────────────────────
    logger.info("Bergie is shutting down")


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-powered educational assistant for EduBerg Learning Hub",
        version="0.1.0",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────
    # In production this will be locked to your actual domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.APP_ENV == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ─────────────────────────────────────────────────────
    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )

    # ── Root redirect ──────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    return app