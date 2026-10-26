from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database import (
    engine,
    initialize_database,
    initialize_mongo,
    session_factory,
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    await initialize_database()
    mongo_client = None
    try:
        mongo_client, mongo_database = await initialize_mongo(
            settings.mongo_uri.get_secret_value()
        )
        application.state.session_factory = session_factory
        application.state.mongo_client = mongo_client
        application.state.mongo_database = mongo_database
        yield
    finally:
        if mongo_client is not None:
            await mongo_client.close()
        await engine.dispose()


app = FastAPI(
    title="GridOps IoT Dashboard API",
    description="API for factory devices and sensor time-series data.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
