"""
Database connection and session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create database engine
# Use asyncpg for async support, but SQLAlchemy 2.0 also supports sync operations
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Enable PostGIS extension on connection
@event.listens_for(engine, "connect", insert=True)
def set_postgis_extension(dbapi_conn, connection_record):
    """
    Enable PostGIS extension on each new database connection
    """
    try:
        with dbapi_conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
            dbapi_conn.commit()
    except Exception as e:
        logger.warning(f"Failed to enable PostGIS extension: {e}")


def init_db():
    """
    Initialize database - create all tables
    Should be called after all models are imported
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_db():
    """
    Drop all database tables
    Use with caution!
    """
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database tables dropped")

