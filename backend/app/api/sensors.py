from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session, get_sensor_readings_collection
from app.models import Device, Sensor
from app.schemas.sensor import (
    DeviceSummary,
    SensorReading,
    SensorSummary,
    SensorValue,
    TimePoint,
)

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("/data", status_code=status.HTTP_201_CREATED)
async def receive_sensor_data(
    reading: SensorReading,
    collection=Depends(get_sensor_readings_collection),
) -> dict[str, str]:
    result = await collection.insert_one(reading.model_dump())
    return {"id": str(result.inserted_id), "status": "accepted"}


@router.get("/summary", response_model=SensorSummary)
async def get_sensor_summary(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    collection=Depends(get_sensor_readings_collection),
) -> SensorSummary:
    sensor_result = await session.execute(select(Sensor).order_by(Sensor.id))
    sensors = sensor_result.scalars().all()
    device_result = await session.execute(select(Device).order_by(Device.id))
    devices = device_result.scalars().all()

    sensor_ids = [sensor.id for sensor in sensors]
    latest_readings: dict[str, dict] = {}
    if sensor_ids:
        latest_cursor = collection.aggregate(
            [
                {"$match": {"sensor_id": {"$in": sensor_ids}}},
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": "$sensor_id",
                        "reading": {"$first": "$$ROOT"},
                    }
                },
            ]
        )
        async for document in latest_cursor:
            latest_readings[document["_id"]] = document["reading"]

    now = datetime.now(timezone.utc)
    time_cursor = collection.aggregate(
        [
            {"$match": {"timestamp": {"$gte": now - timedelta(minutes=60)}}},
            {
                "$group": {
                    "_id": {
                        "$dateTrunc": {
                            "date": "$timestamp",
                            "unit": "minute",
                            "timezone": "UTC",
                        }
                    },
                    "temperature": {"$avg": "$temperature"},
                    "humidity": {"$avg": "$humidity"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
    )
    timeseries: list[TimePoint] = []
    async for document in time_cursor:
        timeseries.append(
            TimePoint(
                time=document["_id"],
                temperature=document.get("temperature") or 0,
                humidity=document.get("humidity") or 0,
            )
        )

    sensor_values = []
    for sensor in sensors:
        reading = latest_readings.get(sensor.id)
        value = reading.get(sensor.sensor_type) if reading else None
        sensor_values.append(
            SensorValue(
                id=sensor.id,
                name=sensor.name,
                machine=sensor.machine,
                type=sensor.sensor_type,
                value=value if value is not None else 0,
                unit=sensor.unit,
                status=(
                    reading.get("status") or "ok" if value is not None else "offline"
                ),
            )
        )

    device_summaries = [
        DeviceSummary(
            id=device.id,
            hostname=device.hostname,
            model=device.model,
            firmware=device.firmware,
            location=device.location,
            ip=device.ip,
            lastSeen=(
                device.last_seen.isoformat() if device.last_seen is not None else ""
            ),
            status=device.status,
        )
        for device in devices
    ]
    return SensorSummary(
        sensors=sensor_values,
        devices=device_summaries,
        timeseries=timeseries,
    )
