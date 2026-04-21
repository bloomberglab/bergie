from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    Every model in app/models/ inherits from this.
    It gives them the __tablename__ convention and shared metadata.
    """
    pass