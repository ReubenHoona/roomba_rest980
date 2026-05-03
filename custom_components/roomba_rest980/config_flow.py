"""The configuration flow for the robot."""

import asyncio
import hashlib
import logging

from aiohttp import ClientConnectorError, ClientError, ContentTypeError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .CloudApi import AuthenticationError, iRobotCloudApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required("base_url"): str,
        vol.Required("cloud_api", default=True): bool,
    }
)

CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required("irobot_username"): str,
        vol.Required("irobot_password"): str,
    }
)


def _normalize_base_url(url: str) -> str:
    """Strip trailing slash and lowercase the scheme/host portion.

    Same robot reachable as `http://rest980/`, `http://REST980`, or
    `http://rest980:3000` shouldn't produce three different unique IDs.
    """
    url = url.strip().rstrip("/")
    if "://" in url:
        scheme, rest = url.split("://", 1)
        url = f"{scheme.lower()}://{rest}"
    return url


class RoombaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 2

    _proposed_name: str
    _user_data: dict[str, any]
    _reauth_entry: config_entries.ConfigEntry | None = None
    _reconfigure_entry: config_entries.ConfigEntry | None = None

    # -- Initial setup ---------------------------------------------------------

    async def test_local(self, user_input):
        """Test connection to local rest980 API and normalize the URL."""
        normalized = _normalize_base_url(user_input["base_url"])
        user_input["base_url"] = normalized

        session = async_get_clientsession(self.hass)
        async with session.get(f"{normalized}/api/local/info/state") as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except (ContentTypeError, ValueError) as err:
                raise ValueError(f"Invalid JSON from device: {err}") from err

        if not isinstance(data, dict) or not data:
            raise ValueError("No data returned from device")

        unique_id = hashlib.md5(normalized.encode()).hexdigest()[:8]
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return data

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Show the user the input for the base url."""
        if user_input is not None:
            errors = {}
            try:
                async with asyncio.timeout(10):
                    device_data = await self.test_local(user_input)
            except TimeoutError:
                errors["base"] = "local_cannot_connect"
            except (ClientError, ClientConnectorError, OSError):
                errors["base"] = "local_cannot_connect"
            except ValueError:
                errors["base"] = "local_connected_no_data"
            except Exception:  # Allowed in config flow for robustness
                errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=USER_SCHEMA,
                    errors=errors,
                )

            device_name = device_data.get("name", "Roomba")
            self._proposed_name = f"{device_name}"

            if not user_input["cloud_api"]:
                return self.async_create_entry(
                    title=self._proposed_name,
                    data=user_input,
                )
            self._user_data = user_input
            return self.async_show_form(step_id="cloud", data_schema=CLOUD_SCHEMA)
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    async def async_step_cloud(self, user_input=None) -> ConfigFlowResult:
        """Show user the setup for the cloud API."""
        if user_input is not None:
            errors = await self._validate_cloud(user_input)
            if errors:
                return self.async_show_form(
                    step_id="cloud", data_schema=CLOUD_SCHEMA, errors=errors
                )

            if hasattr(self, "_user_data"):
                return self.async_create_entry(
                    title=self._proposed_name,
                    data={**self._user_data, **user_input},
                )
            return self.async_abort(reason="missing_user_data")

        return self.async_show_form(step_id="cloud", data_schema=CLOUD_SCHEMA)

    async def _validate_cloud(self, user_input) -> dict[str, str]:
        """Try cloud auth; return an error dict if it fails."""
        async with iRobotCloudApi(
            user_input["irobot_username"], user_input["irobot_password"]
        ) as api:
            try:
                await api.authenticate()
            except AuthenticationError:
                return {"base": "cloud_authentication_error"}
            except Exception:
                return {"base": "unknown"}
        return {}

    # -- Reauth: prompt user for fresh cloud credentials -----------------------

    async def async_step_reauth(self, entry_data: dict[str, any]) -> ConfigFlowResult:
        """Start the reauth flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        """Prompt for new cloud credentials and update the entry."""
        if user_input is not None:
            errors = await self._validate_cloud(user_input)
            if errors:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=CLOUD_SCHEMA,
                    errors=errors,
                )
            assert self._reauth_entry is not None
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data={**self._reauth_entry.data, **user_input},
            )
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=CLOUD_SCHEMA
        )

    # -- Reconfigure: let user change base_url / cloud setting -----------------

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        """Allow updating base_url and cloud_api on an existing entry."""
        self._reconfigure_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if user_input is not None:
            errors = {}
            try:
                async with asyncio.timeout(10):
                    await self.test_reconfigure(user_input)
            except TimeoutError:
                errors["base"] = "local_cannot_connect"
            except (ClientError, ClientConnectorError, OSError):
                errors["base"] = "local_cannot_connect"
            except ValueError:
                errors["base"] = "local_connected_no_data"
            except Exception:
                errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=USER_SCHEMA,
                    errors=errors,
                )

            assert self._reconfigure_entry is not None
            self.hass.config_entries.async_update_entry(
                self._reconfigure_entry,
                data={**self._reconfigure_entry.data, **user_input},
            )
            await self.hass.config_entries.async_reload(
                self._reconfigure_entry.entry_id
            )
            return self.async_abort(reason="reconfigure_successful")

        assert self._reconfigure_entry is not None
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, dict(self._reconfigure_entry.data)
            ),
        )

    async def test_reconfigure(self, user_input) -> None:
        """Validate the new base_url without an `already_configured` abort."""
        normalized = _normalize_base_url(user_input["base_url"])
        user_input["base_url"] = normalized

        session = async_get_clientsession(self.hass)
        async with session.get(f"{normalized}/api/local/info/state") as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except (ContentTypeError, ValueError) as err:
                raise ValueError(f"Invalid JSON from device: {err}") from err
        if not isinstance(data, dict) or not data:
            raise ValueError("No data returned from device")
