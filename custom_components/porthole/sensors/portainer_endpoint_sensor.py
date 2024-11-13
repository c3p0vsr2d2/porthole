from ..portainer.portainer_server import PortainerServer

class PortainerEndpointSensor(SensorEntity):
    """Sensor representing the Portainer server."""

    def __init__(self, portainer, endpoint_index):
        self._portainer = portainer
        self._portainer_obj = portainer.portainer_obj
        self._endpoint_index = endpoint_index
        self._endpoint_id = self._portainer_obj["endpoints"][self._endpoint_index]["endpoint_id"]

    @property
    def unique_id(self):
        """Return a unique ID for the entity, based on Portainer instance ID."""
        return self._portainer_obj["endpoints"][self._endpoint_index]["name"]

    @property
    def name(self):
        """Return the name of the entity."""
        return self._portainer_obj["endpoints"][self._endpoint_index]["name"]

    @property
    def state(self):
        return self._portainer_obj["endpoints"][self._endpoint_index]["measured_num_containers"]

    @property
    def icon(self):
        """Return the icon for the server."""
        return "mdi:server"

    @property
    def extra_state_attributes(self):
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        return {
            "EndpointId": endpoint_info["endpoint_id"],
            "FriendlyName": endpoint_info["friendly_name"],
            "Containers": endpoint_info["container_names"],
            "ContainerCount": endpoint_info["container_count"],
            "MeasuredNumContainers": endpoint_info["measured_num_containers"],
            "EndpointURL": endpoint_info["endpoint_url"],
            "TotalCPU": endpoint_info["total_cpu"],
            "TotalMemory": endpoint_info["total_memory"],
            "RunningContainerCount": endpoint_info["running_container_count"],
            "StoppedContainerCount": endpoint_info["stopped_container_count"],
            "HealthyContainerCount": endpoint_info["healthy_container_count"],
            "UnhealthyContainerCount": endpoint_info["unhealthy_container_count"],
            "VolumeCount": endpoint_info["volumes_count"],
            "ImageCount": endpoint_info["images_count"],
            "PortainerId": self._portainer_obj["portainer_id"],
            "Version": self._portainer_obj["portainer_version"],
        }

    async def async_update(self):
        """Update the server's state and attributes."""
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        _LOGGER.debug(f"Updating Portainer server: {endpoint_info["endpoint_id"]}")
        await self._portainer.update()

    @property
    def device_info(self):
        """Return device specific attributes."""
        # Device unique identifier is the serial
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        return {
            "identifiers": {(f"portainer_{self._portainer_obj["portainer_id"]}", endpoint_info["endpoint_id"])},
            "name": endpoint_info["name"],
            "manufacturer": "Portainer"
            }
