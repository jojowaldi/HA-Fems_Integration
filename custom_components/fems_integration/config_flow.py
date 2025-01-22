from homeassistant import config_entries
import voluptuous as vol
from . import DOMAIN

class FemsIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Fenecon Fems Integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Fenecon Fems Integration", data=user_input)

        schema = vol.Schema({
            vol.Required("ip_address"): str,
            vol.Required("username"): str,
            vol.Required("password"): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema)
