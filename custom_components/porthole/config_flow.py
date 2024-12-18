import logging
from datetime import timedelta
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client
from homeassistant.const import CONF_SCAN_INTERVAL
import aiohttp
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PortainerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Portainer."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._user_input = None
        self._scan_interval = timedelta(minutes=10)  # Default scan interval

    async def async_step_user(self, user_input=None):
        """Handle the initial step of user input."""
        errors = {}

        if user_input is not None:
            url = user_input["url"]
            username = user_input["username"]
            password = user_input["password"]

            # Get scan interval, default to 10 minutes if not provided
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, 10)
            self._scan_interval = timedelta(minutes=scan_interval)

            try:
                # Test the connection to the Portainer API
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{url}/api/auth",
                        json={"Username": username, "Password": password},
                    ) as response:
                        if response.status == 200:
                            # Authentication successful
                            return self.async_create_entry(
                                title=f"Portainer at {url}", data=user_input
                            )
                        else:
                            # Handle failed authentication
                            _LOGGER.error(f"Failed authentication for {url}: {response.status}")
                            errors["base"] = "auth_error"

            except aiohttp.ClientError as err:
                _LOGGER.error(f"Could not connect to Portainer API at {url}: {err}")
                errors["base"] = "cannot_connect"

        # Return the form with errors if present or initial data
        return self.async_show_form(
            step_id="user",
            data_schema=self._get_data_schema(),
            errors=errors,
        )

    def _get_data_schema(self):
        """Return the data schema for the configuration flow."""
        return vol.Schema(
            {
                vol.Required("url", description="Portainer URL"): str,
                vol.Required("username", description="Portainer Username"): str,
                vol.Required("password", description="Portainer Password"): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(int, vol.Range(min=1, max=60)
                ),
            }
        )
