import logging
from datetime import timedelta, datetime
import aiohttp

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
import asyncio
from homeassistant.util import Throttle

from ..portainer.portainer_server import PortainerServer

class PortainerEndpointDevice(Entity):
    """Device representing a Portainer endpoint."""
    
    def __init__(self, hass, entry, url, portainer, endpoint_index):
        self.hass = hass
        self._url = url
        self._portainer = portainer
        self._portainer_obj = portainer.portainer_obj
        self._endpoint_index = endpoint_index
        
        # self._name = self._portainer_obj["endpoints"][endpoint_index]["name"]

        # # Register the device in the Home Assistant device registry
        # device_registry = dr.async_get(hass)
        
        # device_info = DeviceEntry(
        #     identifiers={(f"portainer_{self._portainer.instance_id}", self._endpoint_id)},
        #     name=self._portainer.endpoints_dict[str(self._endpoint_id)]["Name"],
        #     manufacturer="Portainer",
        #     model="Portainer Endpoint",
        #     sw_version=self._portainer.version,
        #     configuration_url=self._url,
        # )

        # # Adding custom attributes
        # device_info.attributes = {
        #     "PortainerId": self._portainer.instance_id,
        #     "EndpointId": self._endpoint_id,
        #     "Friendly Name": self._name,
        #     "Number Of Containers": len(self._containers),
        #     "Containers": self._containers,  # List of container names for this endpoint
        #     "URL": self._url,
        # }

        # device_registry.async_get_or_create(device_info)

        # Register the device in the Home Assistant device registry
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(f"portainer_{self._portainer_obj["portainer_id"]}", self._portainer_obj["endpoints"][endpoint_index]["endpoint_id"])},
            name=self._portainer_obj["endpoints"][endpoint_index]["name"],
            manufacturer="Portainer",
            model="Portainer Endpoint",
            sw_version=self._portainer_obj["portainer_version"],
            configuration_url=self._url,
        )
    
    @property
    def unique_id(self):
        """Return a unique ID for the device."""
        return self.name()
    
    @property
    def name(self):
        """Return the name of the device."""
        return (self._portainer_obj["endpoints"][self._endpoint_index]["name"] + "_device")

    @property
    def state(self):
        """Return the state of the device (the number of containers)."""
        return self._portainer_obj["endpoints"][self._endpoint_index]["measured_num_containers"]

    @property
    def icon(self):
        """Return the icon to represent the device."""
        return "mdi:server"
    
    async def async_update(self):
        """Update the endpoint's state and attributes."""
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        _LOGGER.debug(f"Updating Portainer endpoint: {endpoint_info["id"]} from {endpoint_info["url"]}")
        await self._portainer.update()
