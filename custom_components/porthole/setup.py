
import aiohttp
import logging
from datetime import timedelta, datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import discovery

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
import asyncio
from homeassistant.util import Throttle

from .sensors import PortainerServerSensor, PortainerEndpointSensor, PortainerContainerSensor
from .devices import PortainerEndpointDevice
from .switches import PortainerContainerSwitch

_LOGGER = logging.getLogger(__name__)

# Function to set up sensors from config entry
async def async_setup_entry(hass, entry, async_add_entities):

    """Set up Portainer from a config entry."""
    _LOGGER.info("Setting up Portainer integration with config entry.")

    # Store the config entry data to access later
    hass.data[DOMAIN] = entry.data
    
    """Set up the Portainer sensor platform from a config entry."""
    # Use the configuration data stored in the config entry
    url = entry.data.get("url")
    username = entry.data.get("username")
    password = entry.data.get("password")

    if not url or not username or not password:
        _LOGGER.error("URL, username, or password not provided.")
        return

    try:
        # Initialize the PortainerServer object for fetching data
        portainer = PortainerServer(url, username, password)
        await portainer.update()  # Run the update asynchronously
    except Exception as e:
        _LOGGER.error(f"Error initializing Portainer data: {e}")
        return
    
    try:
        # Add a server sensor for the Portainer server itself
        server_sensor = PortainerServerSensor(portainer)
        async_add_entities([server_sensor], update_before_add=True)
    except Exception as e:
        _LOGGER.error(f"Error adding Portainer Server sensor: {e}")
        
    try:
        # Add a device for each endpoint
        for endpoint_index in range(0, portainer.portainer_obj["measured_num_endpoints"]):
            endpoint_id = portainer.portainer_obj["endpoint_ids"][endpoint_index]

            try:
                device = PortainerEndpointDevice(hass, entry, url, portainer, endpoint_index)
            except Exception as e:
                _LOGGER.error(f"Error initializing Portainer Endpoint Device {endpoint_index}, {endpoint_id}: {e}")

            try:
                endpoint_sensor = PortainerEndpointSensor(portainer, endpoint_index)
                async_add_entities([endpoint_sensor], update_before_add=True)
            except Exception as e:
                _LOGGER.error(f"Error adding Portainer Endpoint sensor {endpoint_index}, {endpoint_id}: {e}")

            try:
                # Create container sensors associated with the device
                container_sensors = [
                    PortainerContainerSensor(portainer, endpoint_index, container_index)
                    for container_index in range(0, portainer.portainer_obj["endpoints"][endpoint_index]["measured_num_containers"])
                ]
                # Now, add them all at once
                async_add_entities(container_sensors, update_before_add=True)
            except Exception as e:
                _LOGGER.error(f"Error adding Portainer Container Sensors: {e}")
        
    except Exception as e:
        _LOGGER.error(f"Error adding Portainer sensors: {e}")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a Portainer config entry."""
    _LOGGER.info("Unloading Portainer integration.")

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