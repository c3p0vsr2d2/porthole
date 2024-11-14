import aiohttp
import logging
from datetime import timedelta, datetime
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import Throttle

from .const import *
from .setup import async_setup_entry, async_unload_entry, async_reload
from .portainer_server import PortainerServer

_LOGGER = logging.getLogger(__name__)

# Define platform names as constants to avoid magic strings
PLATFORM_SENSOR = "setup"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Portainer integration without a config entry."""
    _LOGGER.info("Setting up Portainer integration without config entry.")
    # If there is setup logic that doesn't require config entries, add it here
    # For now, it seems like there is nothing to initialize without a config entry.
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Portainer from a config entry."""
    _LOGGER.info("Setting up Portainer integration with config entry.")

    # Store the config entry data to access later
    hass.data[DOMAIN] = entry.data

    # Forward the configuration to the sensor platform
    try:
        await hass.config_entries.async_forward_entry_setups(entry, [PLATFORM_SENSOR])
        _LOGGER.info("Successfully set up sensor platform for Portainer.")
    except Exception as ex:
        _LOGGER.error("Failed to set up sensor platform for Portainer: %s", ex)
        return False  # Return False to indicate failure

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a Portainer config entry."""
    _LOGGER.info("Unloading Portainer integration.")

    # Unload the sensor platform if necessary
    try:
        unloaded = await hass.config_entries.async_forward_entry_unload(entry, PLATFORM_SENSOR)
        if not unloaded:
            _LOGGER.warning("Failed to unload sensor platform for Portainer.")
    except Exception as ex:
        _LOGGER.error("Error unloading sensor platform for Portainer: %s", ex)

    # Clean up any stored data
    data = hass.data.get(DOMAIN)
    if data:
        del hass.data[DOMAIN]
        _LOGGER.info("Portainer integration data has been removed from hass.data.")
    else:
        _LOGGER.warning("Portainer integration data was not found in hass.data.")

    return True

async def async_reload(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the Portainer integration."""
    _LOGGER.info("Reloading Portainer integration...")

    # Unload and then reload the entry
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
    except Exception as ex:
        _LOGGER.error(f"Error reloading Portainer integration: {ex}")
        return False
    _LOGGER.info("Portainer integration reloaded successfully.")
    return True


"""
Summarized flow of how Home Assistant sets up an integration when configured through the UI:

    User Initiates Setup: The user selects the integration from the UI under Configuration > Integrations.
    Home Assistant Triggers Config Flow: Home Assistant detects that the integration uses configuration entries (via config_flow.py) and calls the appropriate ConfigFlow class to start the setup.
      ConfigFlow class needs to have the domain set correctly
    User Input (Initial Setup): The user is prompted to provide necessary configuration details (e.g., username, password) through a form. This is handled by async_step_user().
    Create Config Entry: Once the user provides valid input, a ConfigEntry is created to store the configuration.
    Integration Setup: After the config entry is created, async_setup_entry() is called to set up the integration and initialize any required platforms (e.g., sensors, switches).
    Entity Setup: Relevant entities (like sensors or switches) are added to Home Assistant using async_add_entities().
    Integration Ready: The integration is now fully set up and visible in the Home Assistant UI, and the user can interact with it.
    Unload or Reload: If needed, the integration can be unloaded or reloaded, which will call async_unload_entry() to clean up and async_setup_entry() again to reload it.

This flow ensures that the integration is configured through a guided process, with Home Assistant handling most of the setup automatically.
"""
