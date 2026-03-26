"""Camera platform for TrailCam Go – shows the latest captured image."""
from __future__ import annotations

import logging

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CAMERA_IP
from .coordinator import TrailCamGoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TrailCamGoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TrailCamGoCamera(coordinator, entry)])


class TrailCamGoCamera(CoordinatorEntity[TrailCamGoCoordinator], Camera):
    """Displays the latest thumbnail from the TrailCam Go camera."""

    _attr_name = "Latest Capture"
    _attr_icon = "mdi:camera-wireless"
    _attr_supported_features = CameraEntityFeature(0)

    def __init__(self, coordinator: TrailCamGoCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_camera"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get("name", "TrailCam Go"),
            manufacturer="TrailCam Go / Dsoon",
            model="WiFi BLE Trail Camera",
            configuration_url=f"http://{entry.data[CONF_CAMERA_IP]}",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        return self.coordinator.latest_thumbnail
