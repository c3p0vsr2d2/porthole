import logging
from datetime import timedelta, datetime
import aiohttp
import asyncio

from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry

from homeassistant.util import Throttle

class PortainerContainerSwitch(SwitchEntity):

    def __init__(self, portainer, endpoint_index, container_index):
        self._portainer = portainer
        self._portainer_obj = self._portainer.portainer_obj
        self._endpoint_index = endpoint_index
        self._container_index = container_index
        self._endpoint_id = self._portainer_obj["endpoints"][self._endpoint_index]["endpoint_id"]
        self._container_id = self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["container_id"]
        
    @property
    def unique_id(self):
        """Return a unique ID for the entity, based on container name."""
        _LOGGER.debug(self._container_index)
        return self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["name"]

    @property
    def name(self):
        """Return the name of the entity."""
        return self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["name"]

    @property
    def state(self):
        """Return the current state of the container (status)."""
        # Use the "Status" field from Portainer to represent the state
        return self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["state"]

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return (self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["state"] == "running")

    def turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        _LOGGER.info(f"Turning on the switch: {self._name}")
        response = self._portainer_obj.start_container(self._endpoint_id, self._container_id)
        if (response != None):
            self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["state"] = "running"

    def turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        _LOGGER.info(f"Turning off the switch: {self._name}")
        response = self._portainer_obj.stop_container(self._endpoint_id, self._container_id)
        if (response != None):
            self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index]["state"] = "stopped"
        
    @property
    def icon(self):
        """Return the icon to represent this container."""
        return "mdi:docker"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        container_info = endpoint_info["containers"][self._container_index]

        return {
            "Name": container_info["name"],
            "Image": container_info["image"],
            "ContainerId": container_info["container_id"],
            "Created": container_info["created"],
            "Status": container_info["status"],
            "State": container_info["state"],
            "Ports": container_info["ports"],  # Get formatted ports
            "EndpointId": endpoint_info["endpoint_id"],
            "EndpointURL": endpoint_info["endpoint_url"],
            "EndpointName": endpoint_info["friendly_name"],
            "PortainerId": self._portainer_obj["portainer_id"],
            "Version": self._portainer_obj["portainer_version"],
        }

    async def async_update(self):
        """Update the server's state and attributes."""
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        _LOGGER.debug(f"Updating Portainer Container sensor: {endpoint_info["endpoint_id"]}")
        await self._portainer.update()
