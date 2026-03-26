"""DataUpdateCoordinator for TrailCam Go."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_SET_MODE_STORAGE,
    API_GET_DIR_INFO,
    API_GET_FILE_PAGE,
    API_GET_THUMBNAIL,
    API_DOWNLOAD_FILE,
    BLE_SERVICE_UUID,
    BLE_CHAR_UUID,
    BLE_NOTIFY_UUID,
    BLE_WAKE_CMD,
    BLE_WAKE_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class TrailCamGoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manages polling and caching of TrailCam Go data."""

    def __init__(
        self,
        hass: HomeAssistant,
        camera_ip: str,
        ble_mac: str | None,
        scan_interval: int,
    ) -> None:
        self.camera_ip = camera_ip
        self.ble_mac = ble_mac
        self.base_url = f"http://{camera_ip}"
        self._latest_thumbnail: bytes | None = None
        self._latest_fid: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self.ble_battery: int | None = None  # raw value from NOTIFY char

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    @property
    def latest_thumbnail(self) -> bytes | None:
        return self._latest_thumbnail

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def async_wake_wifi(self) -> bool:
        """Send BLE command to wake the camera's WiFi AP.

        Requires bleak to be installed and a Bluetooth adapter on the host.
        Returns True on success, False otherwise.
        """
        if not self.ble_mac:
            _LOGGER.warning("No BLE MAC configured – skipping BLE wake")
            return False

        try:
            from bleak import BleakClient  # noqa: PLC0415
        except ImportError:
            _LOGGER.error(
                "bleak is not installed. Install it with: pip install bleak"
            )
            return False

        try:
            _LOGGER.debug("Connecting to BLE device %s", self.ble_mac)
            notify_event = asyncio.Event()
            notify_data: list[bytearray] = []

            def _handle_notify(_, data: bytearray) -> None:
                notify_data.append(data)
                notify_event.set()

            async with BleakClient(self.ble_mac, timeout=15.0) as client:
                # Subscribe to NOTIFY char to receive battery/status response
                try:
                    await client.start_notify(BLE_NOTIFY_UUID, _handle_notify)
                except Exception:
                    pass  # NOTIFY is optional

                await client.write_gatt_char(BLE_CHAR_UUID, BLE_WAKE_CMD, response=False)
                _LOGGER.info("BLE wake command sent to %s", self.ble_mac)

                # Wait briefly for notify response
                try:
                    await asyncio.wait_for(notify_event.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    pass

            # Parse battery from JSON notify payload, e.g. {"battery":"625"}
            if notify_data:
                try:
                    import json
                    raw = b"".join(notify_data).decode("utf-8", errors="ignore")
                    # The payload may be truncated – try to extract a number
                    payload = json.loads(raw) if raw.startswith("{") else {}
                    for key in ("battery", "voltage", "bat", "v"):
                        if key in payload:
                            self.ble_battery = int(payload[key])
                            _LOGGER.debug("BLE battery value: %s", self.ble_battery)
                            break
                except Exception as exc:
                    _LOGGER.debug("Could not parse BLE notify payload: %s", exc)

            # Wait for WiFi AP to come up before polling
            await asyncio.sleep(BLE_WAKE_DELAY)
            return True

        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BLE wake failed: %s", exc)
            return False

    async def async_download_file(self, fid: str) -> bytes | None:
        """Download a file by its FID. Returns raw bytes."""
        url = self.base_url + API_DOWNLOAD_FILE.format(fid=fid)
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                return await resp.read()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to download file %s: %s", fid, exc)
            return None

    async def async_get_file_list(self, file_type: str = "Photo", page: int = 0) -> list[dict]:
        """Return list of files of given type from the camera."""
        url = self.base_url + API_GET_FILE_PAGE.format(page=page, file_type=file_type)
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return data.get("fs", [])
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to get file list: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _set_mode_storage(self) -> None:
        session = await self._get_session()
        url = self.base_url + API_SET_MODE_STORAGE
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            resp.raise_for_status()

    async def _fetch_dir_info(self) -> dict:
        session = await self._get_session()
        url = self.base_url + API_GET_DIR_INFO
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    async def _fetch_latest_thumbnail(self) -> None:
        """Fetch thumbnail of the most recently captured photo."""
        files = await self.async_get_file_list("Photo", page=0)
        if not files:
            return

        # Sort by date descending, take newest
        files_sorted = sorted(files, key=lambda f: f.get("dt", 0), reverse=True)
        latest = files_sorted[0]
        fid = latest.get("fid")

        if fid == self._latest_fid:
            return  # nothing new

        url = self.base_url + API_GET_THUMBNAIL.format(fid=fid)
        session = await self._get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            self._latest_thumbnail = await resp.read()
            self._latest_fid = fid
            _LOGGER.debug("Thumbnail updated (fid=%s)", fid)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from camera. Called by the coordinator on schedule."""
        try:
            await self._set_mode_storage()
            dir_info = await self._fetch_dir_info()
            await self._fetch_latest_thumbnail()

            return {
                "online": True,
                "num_jpg": dir_info.get("NumberOfJPG", 0),
                "num_avi": dir_info.get("NumberOfAVIS", 0),
                "num_files": dir_info.get("NumberOfFiles", 0),
                "last_sync": datetime.now().isoformat(),
            }

        except aiohttp.ClientConnectorError:
            # Camera AP not reachable – not an error, just offline
            _LOGGER.debug("Camera not reachable at %s", self.camera_ip)
            return {
                "online": False,
                "num_jpg": self.data.get("num_jpg", 0) if self.data else 0,
                "num_avi": self.data.get("num_avi", 0) if self.data else 0,
                "num_files": self.data.get("num_files", 0) if self.data else 0,
                "last_sync": self.data.get("last_sync") if self.data else None,
            }
        except Exception as exc:
            raise UpdateFailed(f"TrailCam Go update failed: {exc}") from exc

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
