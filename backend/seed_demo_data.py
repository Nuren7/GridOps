"""Generate one day of demo sensor data in MongoDB Atlas."""

import math
import random
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

from app.config import settings

DATABASE_NAME = "gridops"
COLLECTION_NAME = "sensor_data"
POINTS_PER_SENSOR = 48
INTERVAL = timedelta(minutes=30)

# sensor_id, center, daily variation, random variation, minimum, maximum, phase
SENSORS = (
    ("Sensor-A1", 23.5, 0.8, 0.18, 22.0, 25.0, 0.0),
    ("Sensor-B2", 45.0, 2.5, 0.65, 40.0, 50.0, 1.2),
    ("Sensor-C3", 1.15, 0.2, 0.08, 0.5, 1.8, 2.4),
)


def generate_demo_data(now: datetime | None = None) -> list[dict]:
    end_time = now or datetime.now(timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    end_time = end_time.astimezone(timezone.utc)

    rng = random.Random(42)
    documents = []
    for sensor_id, center, cycle, noise, minimum, maximum, phase in SENSORS:
        for index in range(POINTS_PER_SENSOR):
            timestamp = end_time - INTERVAL * (POINTS_PER_SENSOR - 1 - index)
            trend = math.sin(index * math.tau / POINTS_PER_SENSOR + phase)
            value = round(
                min(
                    max(center + cycle * trend + rng.uniform(-noise, noise), minimum),
                    maximum,
                ),
                2,
            )
            documents.append(
                {
                    "sensor_id": sensor_id,
                    "timestamp": timestamp,
                    "metrics": {"value": value},
                    "status": "normal",
                }
            )
    return documents


def main() -> None:
    with MongoClient(
        settings.mongo_uri.get_secret_value(),
        serverSelectionTimeoutMS=10_000,
    ) as client:
        client.admin.command("ping")
        collection = client[DATABASE_NAME][COLLECTION_NAME]
        collection.delete_many({})
        documents = generate_demo_data()
        collection.insert_many(documents)

    print(f"Successfully seeded {len(documents)} mock sensor data points into MongoDB!")


if __name__ == "__main__":
    main()
