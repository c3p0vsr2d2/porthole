import logging
from datetime import timedelta, datetime
import aiohttp
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
import asyncio
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

# Define the minimum time between updates (e.g., 5 minutes)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

# Function to set up sensors from config entry
async def async_setup_entry(hass, entry, async_add_entities):
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
        async_add_entities([server_sensor], True)
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
                async_add_entities([endpoint_sensor], True)
            except Exception as e:
                _LOGGER.error(f"Error adding Portainer Endpoint sensor {endpoint_index}, {endpoint_id}: {e}")

            try:
                # Create container sensors associated with the device
                container_sensors = [
                    PortainerContainerSensor(portainer, endpoint_index, container_index)
                    for container_index in range(0, portainer.portainer_obj["endpoints"][endpoint_index]["measured_num_containers"])
                ]
                # Now, add them all at once
                async_add_entities(container_sensors, True)
            except Exception as e:
                _LOGGER.error(f"Error adding Portainer Container Sensors: {e}")
        
    except Exception as e:
        _LOGGER.error(f"Error adding Portainer sensors: {e}")

class PortainerServer:
    """Class to handle communication with the Portainer API."""
    
    def __init__(self, url, username, password):
        self._url = url
        self._username = username
        self._password = password
        self._jwt = None
        self._session = None  # Reuse a session for all HTTP requests

        self.portainer_obj = {}

    async def _get_session(self):
        """Create a session for HTTP requests."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session once done."""
        if self._session:
            await self._session.close()
        
    async def async_update_task(self):
        """Update the data from Portainer API."""
        if not self._jwt:
            self._jwt = await self._get_jwt()

        if self._jwt:
            self.portainer_obj = {}
            self.portainer_obj["attributes"] = []
            self.portainer_obj["name"] = f"portainer_main_server"
            self.portainer_obj["friendly_name"] = self.portainer_obj["name"]
            self.portainer_obj["endpoint_ids"] =  []
            self.portainer_obj["endpoints"] =  []
            self.portainer_obj["endpoint_names"] =  []
            self.portainer_obj["measured_num_endpoints"] = 0
            self.portainer_obj["total_container_count"] = 0
            self.portainer_obj["measured_total_num_containers"] = 0
            self.portainer_obj["all_container_names_list"] = []

            self.portainer_obj["portainer_id"], self.portainer_obj["portainer_version"] = await self._get_status()

            # Fetch all endpoints
            temp_endpoints = await self._get_endpoints()
            self.portainer_obj["measured_num_endpoints"] = len(temp_endpoints)

            if self.portainer_obj["measured_num_endpoints"] == 0:
                _LOGGER.error("No endpoints found in Portainer.")
                return  # Exit early if no endpoints are found

            temp_endpoint_index = 0
            for temp_endpoint in temp_endpoints:
                temp_endpoint_id = temp_endpoint["Id"]

                # Update portainer object
                self.portainer_obj["endpoint_ids"].append(temp_endpoint_id)
                self.portainer_obj["endpoint_names"].append(temp_endpoint["Name"])

                # Update portainer/endpoint object
                subdict = temp_endpoint["Snapshots"][0]
                self.portainer_obj["endpoints"].append({})
                self.portainer_obj["endpoints"][temp_endpoint_index] = {}
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_id"] = temp_endpoint_id
                self.portainer_obj["endpoints"][temp_endpoint_index]["name"] = f"portainer_endpoint_{temp_endpoint_id:0>3}"
                self.portainer_obj["endpoints"][temp_endpoint_index]["friendly_name"] = temp_endpoint["Name"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_url"] = temp_endpoint["URL"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["total_cpu"] = subdict["TotalCPU"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["total_memory"] = subdict["TotalMemory"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["container_count"] = subdict["ContainerCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["running_container_count"] = subdict["RunningContainerCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["stopped_container_count"] = subdict["StoppedContainerCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["healthy_container_count"] = subdict["HealthyContainerCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["unhealthy_container_count"] = subdict["UnhealthyContainerCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["volumes_count"] = subdict["VolumeCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["images_count"] = subdict["ImageCount"]
                self.portainer_obj["endpoints"][temp_endpoint_index]["container_names"] = []
                self.portainer_obj["endpoints"][temp_endpoint_index]["containers"] = []
                

                # Await the container fetching coroutine and assign to the dict
                temp_containers = await self._get_containers(temp_endpoint_id)
                self.portainer_obj["endpoints"][temp_endpoint_index]["measured_num_containers"] = len(temp_containers)
                self.portainer_obj["measured_total_num_containers"] = self.portainer_obj["measured_total_num_containers"] + len(temp_containers)
                self.portainer_obj["total_container_count"] = self.portainer_obj["total_container_count"] + self.portainer_obj["endpoints"][temp_endpoint_index]["container_count"]

                temp_container_index = 0
                for temp_container in temp_containers:
                    # Update portainer object
                    self.portainer_obj["endpoints"][temp_endpoint_index]["container_names"].append(temp_container["Names"][0].strip("/"))
                    
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"].append({})
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["state"] = temp_container["State"]
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["name"] = f"portainer_endpoint_{temp_endpoint_id:0>3}_container_{(temp_container["Names"][0].strip("/")).lower()}"
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["image"] = temp_container["Image"]
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["container_id"] = temp_container["Id"]
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["created"] = datetime.fromtimestamp(temp_container["Created"]).strftime("%Y%m%dT%H:%M:%S")
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["status"] = temp_container["Status"]
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["ports"] = self._get_ports(temp_container)

                    temp_container_index += 1

                self.portainer_obj["all_container_names_list"].append(self.portainer_obj["endpoints"][temp_endpoint_index]["container_names"])
                temp_endpoint_index += 1
            _LOGGER.debug(self.portainer_obj)
        else:
            _LOGGER.error("Failed to authenticate with Portainer.")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)  # Throttle the updates
    async def update(self):
        # Start the long task asynchronously
        await asyncio.create_task(async_update_task())

    async def _get_jwt(self):
        """Get JWT for authentication."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self._url}/api/auth", json={"Username": self._username, "Password": self._password}) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("jwt")
        except Exception as e:
            _LOGGER.error(f"Failed to get JWT: {e}")
            return None

    async def _get_endpoints(self):
        """Get the list of endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._url}/api/endpoints", headers={"Authorization": f"Bearer {self._jwt}"}) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            _LOGGER.error(f"Failed to get endpoints: {e}")
            return []

    async def _get_containers(self, endpoint_id):
        """Get containers for a given endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._url}/api/endpoints/{endpoint_id}/docker/containers/json?all=1", headers={"Authorization": f"Bearer {self._jwt}"}) as response:
                    response.raise_for_status()
                    containers = await response.json()
                    for container in containers:
                        container["EndpointID"] = endpoint_id  # Add EndpointID to each container for mapping
                    return containers
        except Exception as e:
            _LOGGER.error(f"Failed to get containers for endpoint {endpoint_id}: {e}")
            return []

    async def _get_status(self):
        """Get the status of the Portainer instance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._url}/api/status", headers={"Authorization": f"Bearer {self._jwt}"}) as response:
                    response.raise_for_status()
                    status_data = await response.json()
                    return status_data["InstanceID"], status_data["Version"]
        except Exception as e:
            _LOGGER.error(f"Failed to get status: {e}")
            return None, None

    def _get_ports(self, in_container):
        """Helper function to get and format container ports."""
        ports = []
        if "Ports" in in_container:
            for port in in_container["Ports"]:
                # Check if the port data contains necessary fields and format them
                public_port = port.get("PublicPort", "N/A")
                private_port = port.get("PrivatePort", "N/A")
                port_type = port.get("Type", "N/A")
                if public_port != "N/A" and private_port != "N/A":
                    ports.append(f"{public_port}->{private_port}/{port_type}")
        return ports if ports else ["No ports exposed"]  # Return a default message if no ports are found

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

class PortainerContainerSensor(SensorEntity):
    """Sensor representing a Portainer container."""
    
    def __init__(self, portainer, endpoint_index, container_index):
        self._portainer = portainer
        self._portainer_obj = self._portainer.portainer_obj
        self._endpoint_index = endpoint_index
        self._container_index = container_index
    
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
        return self._portainer_obj["endpoints"][self._endpoint_index]["containers"][self._container_index].get("state", "unknown")

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

    async def async_update(self):
        """Update the server's state and attributes."""
        endpoint_info = self._portainer_obj["endpoints"][self._endpoint_index]
        _LOGGER.debug(f"Updating Portainer Container sensor: {endpoint_info["endpoint_id"]}")
        await self._portainer.update()