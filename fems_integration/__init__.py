from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "fems_integration"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration via YAML (falls benötigt)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the integration via UI."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Entfernt die Integration."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
