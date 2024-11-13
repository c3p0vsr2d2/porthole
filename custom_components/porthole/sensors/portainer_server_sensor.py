from ..portainer.portainer_server import PortainerServer

class PortainerServerSensor(SensorEntity):
    """Sensor representing the Portainer server."""

    def __init__(self, portainer):
        self._portainer = portainer
        self._portainer_obj = portainer.portainer_obj

    @property
    def unique_id(self):
        """Return a unique ID for the entity, based on Portainer instance ID."""
        return self._portainer_obj["name"]

    @property
    def name(self):
        """Return the name of the entity."""
        return self._portainer_obj["name"]

    @property
    def state(self):
        """Return the state of the entity (Portainer version)."""
        return self._portainer_obj["measured_total_num_containers"]

    @property
    def icon(self):
        """Return the icon for the server."""
        return "mdi:server"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes for the server."""
        return {
            "FriendlyName": self._portainer_obj["name"],
            "ContainerCount": self._portainer_obj["total_container_count"],
            "MeasuredTotalNumContainers": self._portainer_obj["measured_total_num_containers"],
            "Containers": self._portainer_obj["all_container_names_list"],
            "NumberOfEndpoints": self._portainer_obj["measured_num_endpoints"],
            "Endpoints": self._portainer_obj["endpoint_names"],
            "PortainerId": self._portainer_obj["portainer_id"],
            "Version": self._portainer_obj["portainer_version"],
        }

    async def async_update(self):
        """Update the server's state and attributes."""
        _LOGGER.debug(f"Updating Portainer server: {self._portainer_obj["portainer_id"]}")
        # We update the Portainer data and set the state to the version of the Portainer instance
        await self._portainer.update()
