from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="viewer")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    firmware: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(255))
    ip: Mapped[str] = mapped_column(String(45))
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="device")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    machine: Mapped[str] = mapped_column(String(255))
    sensor_type: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(50))
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id"), nullable=True
    )
    device: Mapped[Device | None] = relationship(back_populates="sensors")
