"""Sensor platform for TrailCam Go."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CAMERA_IP
from .coordinator import TrailCamGoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TrailCamGoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TrailCamGoPhotoCountSensor(coordinator, entry),
            TrailCamGoVideoCountSensor(coordinator, entry),
            TrailCamGoOnlineSensor(coordinator, entry),
            TrailCamGoLastSyncSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get("name", "TrailCam Go"),
        manufacturer="TrailCam Go / Dsoon",
        model="WiFi BLE Trail Camera",
        configuration_url=f"http://{entry.data[CONF_CAMERA_IP]}",
    )


class _TrailCamGoSensorBase(CoordinatorEntity[TrailCamGoCoordinator], SensorEntity):
    def __init__(self, coordinator: TrailCamGoCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


class TrailCamGoPhotoCountSensor(_TrailCamGoSensorBase):
    _attr_name = "Photos"
    _attr_icon = "mdi:image-multiple"
    _attr_native_unit_of_measurement = "photos"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_photo_count"

    @property
    def native_value(self):
        return self.coordinator.data.get("num_jpg") if self.coordinator.data else None


class TrailCamGoVideoCountSensor(_TrailCamGoSensorBase):
    _attr_name = "Videos"
    _attr_icon = "mdi:video"
    _attr_native_unit_of_measurement = "videos"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_video_count"

    @property
    def native_value(self):
        return self.coordinator.data.get("num_avi") if self.coordinator.data else None


class TrailCamGoOnlineSensor(_TrailCamGoSensorBase):
    _attr_name = "Status"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_online"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "unknown"
        return "online" if self.coordinator.data.get("online") else "offline"


class TrailCamGoLastSyncSensor(_TrailCamGoSensorBase):
    _attr_name = "Last Sync"
    _attr_icon = "mdi:clock-check"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_sync"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get("last_sync")
        if not raw:
            return None
        from datetime import datetime
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
