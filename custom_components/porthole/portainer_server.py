import logging
from datetime import timedelta, datetime
import aiohttp

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from typing import List, Dict, Any, Optional, Union
import asyncio
from homeassistant.util import Throttle

# Define the minimum time between updates (e.g., 5 minutes)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

_LOGGER = logging.getLogger(__name__)

class PortainerServer:
    """Class to handle communication with the Portainer API."""
    
    def __init__(self, url: str, username: str, password: str) -> None:
        self._url: str = url
        self._username: str = username
        self._password: str = password
        self._jwt: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None  # Reuse a session for all HTTP requests

        self.portainer_obj: Dict[str, Union[List[str], List[Dict[str, Any]], int]] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Create a session for HTTP requests."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session once done."""
        if self._session:
            await self._session.close()
        
    @Throttle(MIN_TIME_BETWEEN_UPDATES)  # Throttle the updates
    async def update(self) -> None:
        """Update the data from Portainer API."""
        if not self._jwt:
            self._jwt = await self._get_jwt()

        if self._jwt:
            self.portainer_obj = {
                "attributes": [],
                "name": "portainer_main_server",
                "friendly_name": "portainer_main_server",
                "endpoint_ids": [],
                "endpoints": [],
                "endpoint_names": [],
                "measured_num_endpoints": 0,
                "server_sensor_name": "",
                "server_sensor_unique_id": "",
                "total_container_count": 0,
                "measured_total_num_containers": 0,
                "all_container_names_list": []
            }

            self.portainer_obj["portainer_id"], self.portainer_obj["portainer_version"] = await self._get_status()

            # Fetch all endpoints
            temp_endpoints = await self._get_endpoints()
            self.portainer_obj["measured_num_endpoints"] = len(temp_endpoints)

            self.portainer_obj["server_sensor_name"]. = f"[PSS][{temp_endpoint_id}][portainer_server_{self.portainer_obj["portainer_id"]}_sensor]"
            self.portainer_obj["server_sensor_unique_id"] = f"portainer_server_{self.portainer_obj["portainer_id"]}_sensor"

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
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_device_name"] = f"[PED][{temp_endpoint_index}][{self.portainer_obj["endpoints"][temp_endpoint_index]["name"]}]"
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_device_unique_id"] = f"portainer_endpoint_{temp_endpoint_id:0>3}_device"
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_sensor_name"] = f"[PES][{temp_endpoint_id}][portainer_endpoint_{temp_endpoint_id:0>3}_sensor]"
                self.portainer_obj["endpoints"][temp_endpoint_index]["endpoint_sensor_unique_id"] = f"portainer_endpoint_{temp_endpoint_id:0>3}_sensor"
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
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["container_sensor_name"] = f"[PCS][{temp_endpoint_id:0>3}][{temp_container_index:0>3}][portainer_endpoint_{temp_endpoint_id:0>3}_container_{(temp_container["Names"][0].strip("/")).lower()}_sensor]"
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["container_sensor_unique_id"] = f"portainer_endpoint_{temp_endpoint_id:0>3}_container_{(temp_container["Names"][0].strip("/")).lower()}_sensor"
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["container_switch_name"] = f"[PCW][{temp_endpoint_id:0>3}][{temp_container_index:0>3}][portainer_endpoint_{temp_endpoint_id:0>3}_container_{(temp_container["Names"][0].strip("/")).lower()}_switch]"
                    self.portainer_obj["endpoints"][temp_endpoint_index]["containers"][temp_container_index]["container_switch_unique_id"] = f"portainer_endpoint_{temp_endpoint_id:0>3}_container_{(temp_container["Names"][0].strip("/")).lower()}_switch"
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

    async def _get_jwt(self) -> Optional[str]:
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

    async def _get_endpoints(self) -> List[Dict[str, Any]]:
        """Get the list of endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._url}/api/endpoints", headers={"Authorization": f"Bearer {self._jwt}"}) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            _LOGGER.error(f"Failed to get endpoints: {e}")
            return []

    async def _get_containers(self, endpoint_id: str) -> List[Dict[str, Any]]:
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

    async def _get_status(self) -> tuple[Optional[str], Optional[str]]:
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

    def _get_ports(self, in_container: Dict[str, Any]) -> List[str]:
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

    async def start_container(self, endpoint_id: str, container_id: str) -> Optional[int]:
        """Start a container given its endpoint and container ID."""
        start_url = f"{self._url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/start"
        headers = {"Authorization": f"Bearer {self._jwt}"}

        async with aiohttp.ClientSession() as session:
            # Use POST request to start the container
            async with session.post(start_url, headers=headers) as response:
                if response.status == 204:
                    # Successfully started, no content to return
                    _LOGGER.info(f"Endpoint ID {endpoint_id}, Container with ID '{container_id}' started successfully.")
                    return response.status
                else:
                    _LOGGER.error(f"Failed to start container with ID '{container_id}': {await response.text()}")
                    response.raise_for_status()  # Raise exception for 4xx/5xx responses
                    return None
                
    async def stop_container(self, endpoint_id: str, container_id: str) -> Optional[int]:
        """Stop a container given its endpoint and container ID."""
        stop_url = f"{self._url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/stop"
        headers = {"Authorization": f"Bearer {self._jwt}"}

        async with aiohttp.ClientSession() as session:
            # Use POST request to start the container
            async with session.post(stop_url, headers=headers) as response:
                if response.status == 204:
                    # Successfully stopped, no content to return
                    _LOGGER.info(f"Endpoint ID {endpoint_id}, Container with ID '{container_id}' stopped successfully.")
                    return response.status
                else:
                    _LOGGER.error(f"Failed to stop container with ID '{container_id}': {await response.text()}")
                    response.raise_for_status()  # Raise exception for 4xx/5xx responses
                    return None
