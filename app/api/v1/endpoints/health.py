from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone
from app.db.session import check_db_connection
from app.db.redis import check_redis_connection
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str                  # "healthy" or "degraded"
    timestamp: str
    version: str
    environment: str
    services: dict[str, str]     # individual service statuses


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the health status of Bergie and its dependencies.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()

    services = {
        "database": "ok" if db_ok else "unavailable",
        "redis":    "ok" if redis_ok else "unavailable",
    }

    overall = "healthy" if all(v == "ok" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
        environment=settings.APP_ENV,
        services=services,
    )