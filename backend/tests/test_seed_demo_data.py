from collections import Counter
from datetime import datetime, timedelta, timezone

from seed_demo_data import generate_demo_data


def test_generates_48_utc_readings_for_each_sensor() -> None:
    end_time = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    documents = generate_demo_data(end_time)

    assert len(documents) == 144
    assert Counter(document["sensor_id"] for document in documents) == {
        "Sensor-A1": 48,
        "Sensor-B2": 48,
        "Sensor-C3": 48,
    }
    assert all(document["timestamp"].tzinfo == timezone.utc for document in documents)
    assert all(document["status"] == "normal" for document in documents)
    assert all(
        set(document) == {"sensor_id", "timestamp", "metrics", "status"}
        for document in documents
    )

    for sensor_id in ("Sensor-A1", "Sensor-B2", "Sensor-C3"):
        readings = [item for item in documents if item["sensor_id"] == sensor_id]
        assert readings[0]["timestamp"] == end_time - timedelta(hours=23, minutes=30)
        assert readings[-1]["timestamp"] == end_time
        assert all(
            later["timestamp"] - earlier["timestamp"] == timedelta(minutes=30)
            for earlier, later in zip(readings, readings[1:])
        )


def test_sensor_values_stay_within_expected_ranges() -> None:
    documents = generate_demo_data(datetime(2026, 10, 26, tzinfo=timezone.utc))
    ranges = {
        "Sensor-A1": (22.0, 25.0),
        "Sensor-B2": (40.0, 50.0),
        "Sensor-C3": (0.5, 1.8),
    }

    for document in documents:
        value = document["metrics"]["value"]
        minimum, maximum = ranges[document["sensor_id"]]
        assert minimum <= value <= maximum
