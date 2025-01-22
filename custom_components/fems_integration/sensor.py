from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
import requests

DOMAIN = "fems_integration"

DATA_POINTS = [
    "State",
    "EssSoc",
    "EssActivePower",
    "EssReactivePower",
    "GridActivePower",
    "GridMinActivePower",
    "GridMaxActivePower",
    "ProductionActivePower",
    "ProductionMaxActivePower",
    "ProductionAcActivePower",
    "ProductionDcActualPower",
    "ConsumptionActivePower",
    "ConsumptionMaxActivePower",
    "EssActiveChargeEnergy",
    "EssActiveDischargeEnergy",
    "GridBuyActiveEnergy",
    "GridSellActiveEnergy",
    "ProductionActiveEnergy",
    "ProductionAcActiveEnergy",
    "ProductionDcActiveEnergy",
    "ConsumptionActiveEnergy",
    "EssDcChargeEnergy",
    "EssDcDischargeEnergy",
    "EssDischargePower",
    "GridMode",
]

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors based on the config entry."""
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    session = requests.Session()
    session.auth = (username, password)
    base_url = f"http://{ip_address}/rest/channel/_sum/"

    sensors = []
    for point in DATA_POINTS:
        sensors.append(MyIntegrationSensor(session, base_url, point))
    async_add_entities(sensors, True)

class MyIntegrationSensor(Entity):
    """Representation of a single data point as a sensor."""

    def __init__(self, session, base_url, point):
        self._session = session
        self._base_url = base_url
        self._point = point
        self._state = None
        self._unit = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Fenecon Fems Integration {self._point}"

    @property
    def state(self):
        """Return the current state."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    def update(self):
        """Fetch the latest data."""
        try:
            url = f"{self._base_url}{self._point}"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            self._state = data.get("value", "N/A")
            self._unit = data.get("unit", None)
        except requests.RequestException as e:
            self._state = "Error"
            self._unit = None
