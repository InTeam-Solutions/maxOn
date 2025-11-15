import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

Base = declarative_base()


class Database:
    """Database connection manager for services"""

    def __init__(self, url: str = None, echo: bool = False):
        self.url = url or os.getenv("DATABASE_URL")
        if not self.url:
            raise RuntimeError("DATABASE_URL environment variable is not set")

        self.echo = echo or (os.getenv("DB_ECHO", "false").lower() == "true")

        # Use NullPool for better compatibility with async
        self.engine = create_engine(
            self.url,
            echo=self.echo,
            future=True,
            poolclass=NullPool
        )

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True
        )

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session_ctx(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)


# Global instance (will be initialized in each service)
_db: Database | None = None


def init_db(url: str = None, echo: bool = False) -> Database:
    """Initialize database connection"""
    global _db
    _db = Database(url=url, echo=echo)
    return _db


def get_db() -> Database:
    """Get initialized database instance"""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db