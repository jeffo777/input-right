from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Asynchronous Database URL for FastAPI
ASYNC_DATABASE_URL = "postgresql+asyncpg://postgres:Theonly***4me@localhost/contractor_leads_bot_db"

# Create an asynchronous engine to connect to the database
engine = create_async_engine(ASYNC_DATABASE_URL)

# Create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session.
    It ensures the session is properly closed after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session