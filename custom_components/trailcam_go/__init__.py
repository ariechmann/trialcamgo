"""TrailCam Go integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_CAMERA_IP,
    CONF_BLE_MAC,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    SERVICE_WAKE_WIFI,
    SERVICE_SYNC,
    SERVICE_DOWNLOAD_LATEST,
)
from .coordinator import TrailCamGoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TrailCam Go from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = TrailCamGoCoordinator(
        hass=hass,
        camera_ip=entry.data[CONF_CAMERA_IP],
        ble_mac=entry.data.get(CONF_BLE_MAC),
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    # Initial refresh – don't fail setup if camera is offline
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass, coordinator, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: TrailCamGoCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close()
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _register_services(
    hass: HomeAssistant,
    coordinator: TrailCamGoCoordinator,
    entry: ConfigEntry,
) -> None:
    """Register integration services."""

    async def handle_wake_wifi(call: ServiceCall) -> None:
        """Send BLE command to wake the camera's WiFi AP."""
        success = await coordinator.async_wake_wifi()
        if success:
            _LOGGER.info("TrailCam Go WiFi wake succeeded")
        else:
            _LOGGER.warning("TrailCam Go WiFi wake failed – check BLE MAC and proximity")

    async def handle_sync(call: ServiceCall) -> None:
        """Force a data refresh from the camera."""
        await coordinator.async_request_refresh()

    async def handle_download_latest(call: ServiceCall) -> None:
        """Download the most recent photo to /config/www/trailcam_go/."""
        import os

        files = await coordinator.async_get_file_list("Photo", page=0)
        if not files:
            _LOGGER.warning("No photos found on camera")
            return

        files_sorted = sorted(files, key=lambda f: f.get("dt", 0), reverse=True)
        latest = files_sorted[0]
        fid = latest["fid"]
        filename = latest.get("n", f"{fid}.jpg")

        data = await coordinator.async_download_file(fid)
        if data is None:
            return

        save_dir = hass.config.path("www", "trailcam_go")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        def _write() -> None:
            with open(save_path, "wb") as f:
                f.write(data)

        await hass.async_add_executor_job(_write)
        _LOGGER.info("Saved latest photo to %s", save_path)

    if not hass.services.has_service(DOMAIN, SERVICE_WAKE_WIFI):
        hass.services.async_register(DOMAIN, SERVICE_WAKE_WIFI, handle_wake_wifi)

    if not hass.services.has_service(DOMAIN, SERVICE_SYNC):
        hass.services.async_register(DOMAIN, SERVICE_SYNC, handle_sync)

    if not hass.services.has_service(DOMAIN, SERVICE_DOWNLOAD_LATEST):
        hass.services.async_register(
            DOMAIN, SERVICE_DOWNLOAD_LATEST, handle_download_latest
        )
