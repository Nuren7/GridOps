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

DEMO_SENSOR_METADATA = {
    "Sensor-A1": ("Factory temperature", "Factory floor", "temperature", "°C"),
    "Sensor-B2": ("Factory humidity", "Factory floor", "humidity", "%"),
    "Sensor-C3": ("Machine vibration", "Factory floor", "vibration", "mm/s"),
}


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

    latest_readings: dict[str, dict] = {}
    latest_cursor = collection.aggregate(
        [
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
            {"$match": {"timestamp": {"$gte": now - timedelta(hours=24)}}},
            {
                "$group": {
                    "_id": {
                        "$dateTrunc": {
                            "date": "$timestamp",
                            "unit": "minute",
                            "timezone": "UTC",
                        }
                    },
                    "temperature": {
                        "$avg": {
                            "$cond": [
                                {"$eq": ["$sensor_id", "Sensor-A1"]},
                                {"$ifNull": ["$metrics.value", "$temperature"]},
                                "$temperature",
                            ]
                        }
                    },
                    "humidity": {
                        "$avg": {
                            "$cond": [
                                {"$eq": ["$sensor_id", "Sensor-B2"]},
                                {"$ifNull": ["$metrics.value", "$humidity"]},
                                "$humidity",
                            ]
                        }
                    },
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

    sensor_metadata = {
        sensor.id: (
            sensor.name,
            sensor.machine,
            sensor.sensor_type,
            sensor.unit,
        )
        for sensor in sensors
    }
    for sensor_id, metadata in DEMO_SENSOR_METADATA.items():
        if sensor_id in latest_readings:
            sensor_metadata.setdefault(sensor_id, metadata)

    sensor_values = []
    for sensor_id, (name, machine, sensor_type, unit) in sensor_metadata.items():
        reading = latest_readings.get(sensor_id)
        value = (
            reading.get(sensor_type)
            if reading and reading.get(sensor_type) is not None
            else reading.get("metrics", {}).get("value")
            if reading
            else None
        )
        reading_status = reading.get("status") if reading else None
        sensor_values.append(
            SensorValue(
                id=sensor_id,
                name=name,
                machine=machine,
                type=sensor_type,
                value=value if value is not None else 0,
                unit=unit,
                status=(
                    ("ok" if reading_status == "normal" else reading_status or "ok")
                    if value is not None
                    else "offline"
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
