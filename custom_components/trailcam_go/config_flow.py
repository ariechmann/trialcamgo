"""Config flow for TrailCam Go."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_IP,
    DEFAULT_SCAN_INTERVAL,
    CONF_CAMERA_IP,
    CONF_BLE_MAC,
    CONF_SCAN_INTERVAL,
    API_GET_DIR_INFO,
    API_SET_MODE_STORAGE,
)

_LOGGER = logging.getLogger(__name__)


async def _test_connection(ip: str) -> bool:
    """Try to reach the camera HTTP API. Returns True if reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            # Switch to storage mode first
            async with session.get(
                f"http://{ip}{API_SET_MODE_STORAGE}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r1:
                r1.raise_for_status()
            async with session.get(
                f"http://{ip}{API_GET_DIR_INFO}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r2:
                r2.raise_for_status()
                await r2.json(content_type=None)
        return True
    except Exception:  # noqa: BLE001
        return False


class TrailCamGoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TrailCam Go."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            ip = user_input[CONF_CAMERA_IP]

            # Unique ID = camera IP to prevent duplicates
            await self.async_set_unique_id(ip)
            self._abort_if_unique_id_configured()

            # Optionally test connection if camera is reachable right now
            reachable = await _test_connection(ip)
            if not reachable:
                errors["base"] = "cannot_connect"
                # Allow override: user can proceed anyway (camera may be off)
                if not user_input.get("ignore_connectivity"):
                    # Show form again with option to ignore
                    schema = self._build_schema(user_input, show_ignore=True)
                    return self.async_show_form(
                        step_id="user", data_schema=schema, errors=errors
                    )

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                    CONF_CAMERA_IP: ip,
                    CONF_BLE_MAC: user_input.get(CONF_BLE_MAC) or None,
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                },
            )

        schema = self._build_schema()
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def _build_schema(defaults: dict | None = None, show_ignore: bool = False) -> vol.Schema:
        d = defaults or {}
        fields: dict = {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_CAMERA_IP, default=d.get(CONF_CAMERA_IP, DEFAULT_IP)): str,
            vol.Optional(CONF_BLE_MAC, default=d.get(CONF_BLE_MAC, "")): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=10, max=3600)),
        }
        if show_ignore:
            fields[vol.Optional("ignore_connectivity", default=False)] = bool
        return vol.Schema(fields)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return TrailCamGoOptionsFlow(config_entry)


class TrailCamGoOptionsFlow(config_entries.OptionsFlow):
    """Options flow to adjust settings after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_BLE_MAC,
                    default=data.get(CONF_BLE_MAC, ""),
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
