from .const import *
from .setup import *
from .portainer_server import PortainerServer

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
