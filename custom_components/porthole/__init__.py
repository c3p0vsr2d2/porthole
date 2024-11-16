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
from .portainer_server import PortainerServer
from .devices.portainer_endpoint_device import PortainerEndpointDevice

_LOGGER = logging.getLogger(__name__)

# Define platform names as constants to avoid magic strings
# PLATFORMS = ["sensor", "switch"]
PLATFORMS = "sensor"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Porthole integration without a config entry."""
    _LOGGER.info("Setting up Porthole integration without a config entry.")
    # If there is setup logic that doesn't require config entries, add it here
    # For now, it seems like there is nothing to initialize without a config entry.
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Porthole from a config entry."""
    _LOGGER.info("[Porthole] Setting up Porthole integration with config entry.")

    # Store the config entry data to access later
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = entry.data
        _LOGGER.info("[Porthole] Porthole integration data stored in hass.data.")
    else:
        _LOGGER.debug("[Porthole] Porthole integration data already exists in hass.data.")

    """Set up Portainer from a config entry."""
    _LOGGER.debug("[Porthole] Setting up Portainer integration with config entry.")
    
    # Use the configuration data stored in the config entry
    url = entry.data.get("url")
    username = entry.data.get("username")
    password = entry.data.get("password")

    if not url or not username or not password:
        _LOGGER.error("URL, username, or password not provided.")
        return

    try:
        # Initialize the PortainerServer object for fetching data
        entry.portainer = PortainerServer(url, username, password)
        await entry.portainer.update()  # Run the update asynchronously
    except Exception as e:
        _LOGGER.error(f"[Porthole] Error initializing Portainer Server: {e}")
        return False

    try:
        # Add a device for each endpoint
        for endpoint_index in range(0, entry.portainer.portainer_obj["measured_num_endpoints"]):
            endpoint_id = entry.portainer.portainer_obj["endpoint_ids"][endpoint_index]
            device = PortainerEndpointDevice(hass, entry, url, entry.portainer, endpoint_index)
    except Exception as e:
        _LOGGER.error(f"[Porthole] Error initializing Portainer Endpoints: {e}")
        return False

    # Forward the configuration to the sensor platform
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("[Porthole] Successfully set up sensor/switch platforms for Porthole.")
    except Exception as ex:
        _LOGGER.error("[Porthole] Failed to set up sensor/switch platforms for Porthole: %s", ex)
        return False  # Return False to indicate failure

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Porthole config entry."""
    _LOGGER.info("[Porthole] Unloading Porthole integration.")

    # Unload the sensor platform if necessary
    try:
        unloaded = await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS)
        if unloaded:
            _LOGGER.info("[Porthole] Successfully unloaded sensor platform for Porthole.")
        else:
            _LOGGER.warning("[Porthole] Failed to unload sensor platform for Porthole.")
    except Exception as ex:
        _LOGGER.error("[Porthole] Error unloading sensor platform for Porthole: %s", ex)

    # Clean up any stored data
    data = hass.data.get(DOMAIN)
    if data:
        del hass.data[DOMAIN]
        _LOGGER.info("[Porthole] Porthole integration data has been removed from hass.data.")
    else:
        _LOGGER.warning("[Porthole] Porthole integration data was not found in hass.data.")
    
    return True

async def async_reload(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload the Porthole integration: Unloads and re-sets up the integration."""
    _LOGGER.info("[Porthole] Reloading Porthole integration...")
    
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
    except Exception as ex:
        _LOGGER.error(f"[Porthole] Error reloading Porthole integration: {ex}")
        return False
    
    _LOGGER.info("[Porthole] Porthole integration reloaded successfully.")
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
