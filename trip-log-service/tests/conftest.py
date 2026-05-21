import asyncio
import os
import sys
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add trip-log-service directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_URL
from storage.database import Base


# Parse and compute the TEST_DATABASE_URL (swapping smartbus for smartbus_test)
parsed = urlparse(DATABASE_URL)
# swap the db name in path
test_path = "/smartbus_test"
TEST_DATABASE_URL = parsed._replace(path=test_path).geturl()


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-wide event loop for running async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create the smartbus_test database and initialize all tables."""
    # 1. Connect to default database with AUTOCOMMIT to drop/recreate test DB outside of a transaction
    admin_engine = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        # Drop existing test database if any, and create a fresh one
        await conn.execute(text("DROP DATABASE IF EXISTS smartbus_test"))
        await conn.execute(text("CREATE DATABASE smartbus_test"))
    await admin_engine.dispose()

    # 2. Connect to the newly created test database and create the tables
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Initialize schema asynchronously (using conn.run_sync as requested by user)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield test_engine

    # 3. Cleanup: Drop all tables and dispose engine at the end of test session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_test_db):
    """Provide an isolated database session per test with clean database tables."""
    test_engine = setup_test_db
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Clean any leftovers before starting
        await session.execute(text("TRUNCATE TABLE trips CASCADE"))
        await session.commit()
        
        yield session
        
        # Clean after test completes
        await session.execute(text("TRUNCATE TABLE trips CASCADE"))
        await session.commit()
