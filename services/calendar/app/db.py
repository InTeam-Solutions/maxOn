from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


settings = get_settings()
engine: AsyncEngine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create database tables on startup if they do not exist."""

    from app import models  # noqa: WPS433 - imported lazily to avoid circular deps

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
