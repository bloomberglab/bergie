from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings
from app.core.logging import logger


# Create the engine once — it manages a connection pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # test connection before using from pool
    pool_size=5,             # number of persistent connections
    max_overflow=10,         # extra connections allowed under load
    echo=(settings.APP_ENV == "development"),  # log SQL in dev only
)

# Session factory — call SessionLocal() to get a DB session
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    The session is automatically closed after the request completes,
    even if an exception is raised.

    Usage in a route:
        @router.get("/something")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Health check — returns True if database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False