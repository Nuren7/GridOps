from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models import Base


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+aiomysql://", 1)
    if url.startswith("mysql+pymysql://"):
        return url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


database_url = normalize_database_url(settings.database_url.get_secret_value())
engine = create_async_engine(database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_sensor_readings_collection(request: Request) -> AsyncCollection[Any]:
    return request.app.state.mongo_database["sensor_data"]


async def initialize_mongo(uri: str) -> tuple[Any, Any]:
    from pymongo import AsyncMongoClient

    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
    await client.admin.command("ping")
    database = client.get_database("gridops")
    collection = database["sensor_readings"]
    await collection.create_index([("sensor_id", ASCENDING), ("timestamp", DESCENDING)])
    await collection.create_index([("timestamp", DESCENDING)])
    return client, database
