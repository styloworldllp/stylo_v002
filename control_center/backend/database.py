# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/database.py
#
# SQLAlchemy async engine + session factory for the Control Center.
#
# All database I/O is fully async:
#   engine            — single async connection pool shared by the process
#   AsyncSessionLocal — session factory; each request gets its own isolated
#                       session via the get_db() FastAPI dependency
#   get_db()          — async generator injected into route handlers with
#                       Depends(get_db); yields a session and closes it on exit
#   create_tables()   — called once at FastAPI lifespan startup to create any
#                       missing tables (dev convenience; production uses Alembic)
#   Base              — DeclarativeBase subclass imported by all model files
# ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
