import asyncio
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Handle SQLite vs PostgreSQL engine configurations
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

_db_initialized = False
_init_lock = asyncio.Lock()


async def ensure_database_initialized():
    """Ensure database schema and verified seed datasets are initialized."""
    global _db_initialized
    if _db_initialized or settings.ENVIRONMENT.lower() == "testing":
        return
    async with _init_lock:
        if _db_initialized:
            return
        from app.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            from app.tools.seed_demo_data import seed_all_demo_data
            await seed_all_demo_data(force=True)
        except Exception as e:
            logger.warning(f"Demo seeding notice: {e}")
        try:
            from scripts.import_coimbatore_facilities import import_coimbatore_dataset
            await import_coimbatore_dataset(dry_run=False)
        except Exception as e:
            logger.warning(f"Coimbatore dataset seeding notice: {e}")
        _db_initialized = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an asynchronous database session."""
    await ensure_database_initialized()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
