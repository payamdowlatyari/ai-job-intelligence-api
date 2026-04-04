"""Database engine and session management using SQLModel."""

from sqlmodel import SQLModel, create_engine, Session
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables() -> None:
    """Create all database tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that provides a database session."""
    with Session(engine) as session:
        yield session
