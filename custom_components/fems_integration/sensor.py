from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
import requests
from homeassistant.util import dt as dt_util

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
    # Bestehende Sensoren für die einzelnen Datenpunkte hinzufügen
    for point in DATA_POINTS:
        sensors.append(MyIntegrationSensor(session, base_url, point))
    
    # Neuen Sensor für den täglichen Verbrauch hinzufügen
    sensors.append(DailyConsumptionSensor(session, base_url))
    
    # Neue Sensoren für tägliche Netzeinspeisung und täglichen Bezug hinzufügen
    sensors.append(DailyGridFeedInSensor(session, base_url))
    sensors.append(DailyGridConsumptionSensor(session, base_url))
    
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

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return "energy"

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

class DailyConsumptionSensor(Entity):
    """Sensor zur Berechnung des täglichen Energieverbrauchs in kWh
       durch Integration der ConsumptionActivePower (in Watt) über die Zeit.
    """

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_energy = 0.0  # akkumulierte Energie in kWh
        self._last_update = None  # Zeitpunkt des letzten Updates
        self._state = None

    @property
    def name(self):
        """Name des Sensors."""
        return "Fenecon Daily Consumption"

    @property
    def state(self):
        """Aktueller Tagesverbrauch in kWh (auf 3 Nachkommastellen gerundet)."""
        if self._state is not None:
            return round(self._state, 3)
        return None

    @property
    def unit_of_measurement(self):
        """Einheit der Messung."""
        return "kWh"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return "energy"
    
    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return "total_increasing"

    def update(self):
        """Berechne den täglichen Verbrauch:
           - Hole die aktuelle ConsumptionActivePower (Watt).
           - Berechne die seit dem letzten Update verstrichene Zeit.
           - Integriere die Leistung (Watt * Zeit) zu Energie (kWh).
           - Setze den Tageszähler bei Tageswechsel zurück.
        """
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_update is not None and now.date() != self._last_update.date():
            self._daily_energy = 0.0

        # Aktuellen Wert von ConsumptionActivePower abrufen
        try:
            url = f"{self._base_url}ConsumptionActivePower"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            consumption_power = data.get("value", None)
            if consumption_power is None:
                return
            consumption_power = float(consumption_power)
        except Exception as e:
            # Im Fehlerfall einfach nichts integrieren
            return

        if self._last_update is not None:
            # Berechne die verstrichene Zeit in Sekunden
            dt_seconds = (now - self._last_update).total_seconds()
            # Umrechnung: (Watt * Sekunden) in kWh => (W * s) / (3600 * 1000)
            # (Hier: Annahme, dass consumption_power in Watt geliefert wird)
            self._daily_energy += consumption_power * dt_seconds / 3600000.0

        self._last_update = now
        self._state = self._daily_energy

class DailyGridFeedInSensor(Entity):
    """Sensor zur Berechnung der täglichen Netzeinspeisung in kWh."""

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_feed_in = 0.0  # akkumulierte Einspeisung in kWh
        self._last_update = None
        self._state = None

    @property
    def name(self):
        """Name des Sensors."""
        return "Fenecon Daily Grid Feed-In"

    @property
    def state(self):
        """Aktuelle tägliche Einspeisung in kWh (auf 3 Nachkommastellen gerundet)."""
        if self._state is not None:
            return round(self._state, 3)
        return None

    @property
    def unit_of_measurement(self):
        """Einheit der Messung."""
        return "kWh"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return "energy"

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return "total_increasing"

    def update(self):
        """Berechne die tägliche Einspeisung."""
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_update is not None and now.date() != self._last_update.date():
            self._daily_feed_in = 0.0

        # Aktuellen Wert von GridActivePower abrufen
        try:
            url = f"{self._base_url}GridActivePower"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            grid_power = data.get("value", None)
            if grid_power is None or grid_power >= 0:
                return
            grid_power = abs(float(grid_power))  # Nur negative Werte (Einspeisung)
        except Exception as e:
            return

        if self._last_update is not None:
            dt_seconds = (now - self._last_update).total_seconds()
            self._daily_feed_in += grid_power * dt_seconds / 3600000.0

        self._last_update = now
        self._state = self._daily_feed_in

class DailyGridConsumptionSensor(Entity):
    """Sensor zur Berechnung des täglichen Netzbezugs in kWh."""

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_consumption = 0.0  # akkumulierter Bezug in kWh
        self._last_update = None
        self._state = None

    @property
    def name(self):
        """Name des Sensors."""
        return "Fenecon Daily Grid Consumption"

    @property
    def state(self):
        """Aktueller täglicher Netzbezug in kWh (auf 3 Nachkommastellen gerundet)."""
        if self._state is not None:
            return round(self._state, 3)
        return None

    @property
    def unit_of_measurement(self):
        """Einheit der Messung."""
        return "kWh"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return "energy"

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return "total_increasing"

    def update(self):
        """Berechne den täglichen Netzbezug."""
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_update is not None and now.date() != self._last_update.date():
            self._daily_consumption = 0.0

        # Aktuellen Wert von GridActivePower abrufen
        try:
            url = f"{self._base_url}GridActivePower"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            grid_power = data.get("value", None)
            if grid_power is None or grid_power <= 0:
                return
            grid_power = float(grid_power)  # Nur positive Werte (Bezug)
        except Exception as e:
            return

        if self._last_update is not None:
            dt_seconds = (now - self._last_update).total_seconds()
            self._daily_consumption += grid_power * dt_seconds / 3600000.0

        self._last_update = now
        self._state = self._daily_consumption
