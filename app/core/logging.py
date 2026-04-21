import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configure application-wide logging.
    In development: human-readable format with colours (if terminal supports it)
    In production: JSON-friendly format for log aggregation tools
    """

    log_level = logging.DEBUG if settings.APP_ENV == "development" else logging.INFO

    # Root logger format
    if settings.APP_ENV == "development":
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        datefmt = "%H:%M:%S"
    else:
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        datefmt = "%Y-%m-%dT%H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence noisy third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger("bergie")
    logger.info(f"Logging initialised | env={settings.APP_ENV} | level={logging.getLevelName(log_level)}")

    return logger


# Module-level logger — import this in other files
logger = logging.getLogger("bergie")