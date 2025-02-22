"""Database connection management for PostgreSQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, registry
import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
mapper_registry = registry()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Session:
    """
    Creates and returns a new database session.

    Returns
    -------
    Session
        A SQLAlchemy database session.
    """
    mapper_registry.configure()  # Ensure mappers are configured
    return SessionLocal()
