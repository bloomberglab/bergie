import uvicorn
from app.app import create_app
from app.core.config import settings

# This is what gets imported by uvicorn in production
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.APP_ENV == "development"),  # auto-reload on file changes
        log_level="debug" if settings.APP_ENV == "development" else "info",
    )