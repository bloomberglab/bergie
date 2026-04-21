from fastapi import APIRouter
from app.api.v1.endpoints import health

api_router = APIRouter()

# Register endpoint modules
api_router.include_router(health.router)

# Telegram webhook will be added here in Milestone 2.1
# api_router.include_router(telegram.router, prefix="/webhook")