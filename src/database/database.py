"""Database connection management for PostgreSQL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, registry
import os

def get_database_url() -> str:
    """
    Construct the database URL from environment variables.
    
    Returns
    -------
    str
        The database URL.
    """
    # Try to get individual components first
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    name = os.getenv("DB_NAME", "claimvision")
    
    # If all components are available, construct the URL
    if username and password and host:
        return f"postgresql://{username}:{password}@{host}:5432/{name}"
    
    # Fall back to the full DATABASE_URL if available
    return os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testdb")

# Get the database URL
DATABASE_URL: str = get_database_url()

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
