import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import discovery
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define platform names as constants to avoid magic strings
PLATFORM_SENSOR = "ingress"

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
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]
        _LOGGER.info("Portainer integration data has been removed from hass.data.")
    else:
        _LOGGER.warning("Portainer integration data not found in hass.data.")

    return True

async def async_reload(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the Portainer integration."""
    _LOGGER.info("Reloading Portainer integration...")

    # Unload and then reload the entry
    try:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
        _LOGGER.info("Portainer integration reloaded successfully.")
    except Exception as ex:
        _LOGGER.error("Error reloading Portainer integration: %s", ex)
        return False  # Return False to indicate failure

    return True
