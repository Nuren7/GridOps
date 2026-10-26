from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db_session, get_sensor_readings_collection
from app.main import app
from app.models import Base, Device, Sensor, User
from app.security import password_hash


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def database_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_sensor_data_is_saved_to_mongodb() -> None:
    class FakeCollection:
        document = None

        async def insert_one(self, document):
            self.document = document
            return SimpleNamespace(inserted_id="reading-1")

    collection = FakeCollection()
    app.dependency_overrides[get_sensor_readings_collection] = lambda: collection
    payload = {
        "sensor_id": "S-101",
        "temperature": 22.4,
        "timestamp": "2026-10-26T14:00:00Z",
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/sensors/data", json=payload)

    assert response.status_code == 201
    assert response.json() == {"id": "reading-1", "status": "accepted"}
    assert collection.document["sensor_id"] == "S-101"
    assert collection.document["timestamp"] == datetime(
        2026, 10, 26, 14, 0, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_sensor_data_requires_a_measurement() -> None:
    app.dependency_overrides[get_sensor_readings_collection] = lambda: None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/sensors/data",
            json={
                "sensor_id": "S-101",
                "timestamp": "2026-10-26T14:00:00Z",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_a_jwt(
    database_session: AsyncSession,
) -> None:
    database_session.add(
        User(
            username="operator",
            hashed_password=password_hash.hash("correct-horse-battery-staple"),
            role="operator",
        )
    )
    await database_session.commit()

    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/token",
            data={
                "username": "operator",
                "password": "correct-horse-battery-staple",
            },
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_registration_creates_a_user_with_a_hashed_password(
    database_session: AsyncSession,
) -> None:
    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "new-operator", "password": "safe-password"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "registered": True,
        "username": "new-operator",
    }
    user = await database_session.scalar(
        select(User).where(User.username == "new-operator")
    )
    assert user is not None
    assert user.hashed_password != "safe-password"
    assert password_hash.verify("safe-password", user.hashed_password)


@pytest.mark.asyncio
async def test_registration_rejects_an_existing_username(
    database_session: AsyncSession,
) -> None:
    database_session.add(
        User(
            username="existing",
            hashed_password=password_hash.hash("existing-password"),
        )
    )
    await database_session.commit()

    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "existing", "password": "new-password"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Användarnamnet är upptaget"


@pytest.mark.asyncio
async def test_json_login_authenticates_registered_user(
    database_session: AsyncSession,
) -> None:
    database_session.add(
        User(
            username="operator",
            hashed_password=password_hash.hash("correct-password"),
        )
    )
    await database_session.commit()

    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "operator", "password": "correct-password"},
        )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "operator"}


@pytest.mark.asyncio
async def test_json_login_rejects_incorrect_credentials(
    database_session: AsyncSession,
) -> None:
    database_session.add(
        User(
            username="operator",
            hashed_password=password_hash.hash("correct-password"),
        )
    )
    await database_session.commit()

    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "operator", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Felaktigt användarnamn eller lösenord."


@pytest.mark.asyncio
async def test_summary_combines_sql_metadata_and_mongo_readings(
    database_session: AsyncSession,
) -> None:
    database_session.add(
        Device(
            id="GW-1",
            hostname="gateway-1",
            model="Edge Gateway",
            firmware="1.0",
            location="Hall A",
            ip="192.0.2.1",
            status="ok",
        )
    )
    database_session.add(
        Sensor(
            id="S-101",
            name="Spindle temperature",
            machine="CNC-01",
            sensor_type="temperature",
            unit="°C",
            device_id="GW-1",
        )
    )
    await database_session.commit()

    class FakeCursor:
        def __init__(self, documents):
            self.documents = documents

        def __aiter__(self):
            self.iterator = iter(self.documents)
            return self

        async def __anext__(self):
            try:
                return next(self.iterator)
            except StopIteration:
                raise StopAsyncIteration

    class FakeCollection:
        def aggregate(self, pipeline):
            is_latest_pipeline = any(
                "$group" in step and step["$group"]["_id"] == "$sensor_id"
                for step in pipeline
            )
            if is_latest_pipeline:
                return FakeCursor(
                    [
                        {
                            "_id": "S-101",
                            "reading": {
                                "temperature": 22.4,
                                "status": "warning",
                            },
                        }
                    ]
                )
            return FakeCursor(
                [
                    {
                        "_id": datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc),
                        "temperature": 22.4,
                        "humidity": 45.0,
                    }
                ]
            )

    async def override_session():
        yield database_session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_sensor_readings_collection] = lambda: FakeCollection()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/sensors/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["sensors"][0]["value"] == 22.4
    assert summary["sensors"][0]["status"] == "warning"
    assert summary["devices"][0]["id"] == "GW-1"
    assert summary["timeseries"][0]["humidity"] == 45.0
