from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SensorStatus = Literal["ok", "warning", "critical", "offline"]
SensorType = Literal["temperature", "humidity", "vibration", "pressure"]


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)

    sensor_id: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    temperature: float | None = None
    humidity: float | None = None
    vibration: float | None = None
    pressure: float | None = None
    status: SensorStatus | None = None

    @model_validator(mode="after")
    def validate_measurement(self) -> "SensorReading":
        measurements = ("temperature", "humidity", "vibration", "pressure")
        if not any(getattr(self, name) is not None for name in measurements):
            raise ValueError("At least one numeric sensor measurement is required")
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        return self


class SensorValue(BaseModel):
    id: str
    name: str
    machine: str
    type: SensorType
    value: float
    unit: str
    status: SensorStatus


class DeviceSummary(BaseModel):
    id: str
    hostname: str
    model: str
    firmware: str
    location: str
    ip: str
    lastSeen: str
    status: SensorStatus


class TimePoint(BaseModel):
    time: datetime
    temperature: float
    humidity: float


class SensorSummary(BaseModel):
    sensors: list[SensorValue]
    devices: list[DeviceSummary]
    timeseries: list[TimePoint]
