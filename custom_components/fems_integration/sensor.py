from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.restore_state import RestoreEntity
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

def _device_class_for_point(point):
    if "Energy" in point:
        return "energy"
    if "Power" in point:
        return "power"
    return None

def _state_class_for_device_class(device_class):
    if device_class == "power":
        return "measurement"
    if device_class == "energy":
        return "total_increasing"
    return None

def _unit_for_point(point, api_unit):
    if api_unit:
        return api_unit
    if "ReactivePower" in point:
        return "var"
    if "Energy" in point:
        return "Wh"
    if "Power" in point:
        return "W"
    if point == "EssSoc":
        return "%"
    return None

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

class MyIntegrationSensor(SensorEntity):
    """Representation of a single data point as a sensor."""

    def __init__(self, session, base_url, point):
        self._session = session
        self._base_url = base_url
        self._point = point
        self._state = None
        self._unit = None
        self._device_class = _device_class_for_point(point)
        self._state_class = _state_class_for_device_class(self._device_class)

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
        return self._device_class

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return self._state_class

    def update(self):
        """Fetch the latest data."""
        try:
            url = f"{self._base_url}{self._point}"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            self._state = data.get("value", "N/A")
            self._unit = _unit_for_point(self._point, data.get("unit", None))
        except requests.RequestException as e:
            self._state = "Error"
            self._unit = None

class DailyConsumptionSensor(SensorEntity, RestoreEntity):
    """Sensor zur Berechnung des täglichen Energieverbrauchs in kWh
       durch Integration der ConsumptionActivePower (in Watt) über die Zeit.
    """

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_energy = 0.0  # akkumulierte Energie in kWh
        self._last_update = None  # Zeitpunkt des letzten Updates
        self._last_reset_date = None
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

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._last_update is not None:
            attrs["last_update"] = dt_util.as_local(self._last_update).isoformat()
        if self._last_reset_date is not None:
            attrs["last_reset"] = self._last_reset_date.isoformat()
        return attrs

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            self._last_reset_date = dt_util.now().date()
            return

        try:
            restored_value = float(last_state.state)
        except (TypeError, ValueError):
            restored_value = None

        if restored_value is not None:
            self._daily_energy = restored_value
            self._state = restored_value

        last_reset = last_state.attributes.get("last_reset")
        if last_reset:
            parsed = dt_util.parse_date(last_reset)
            if parsed is not None:
                self._last_reset_date = parsed

        last_update = last_state.attributes.get("last_update")
        if last_update:
            parsed = dt_util.parse_datetime(last_update)
            if parsed is not None:
                self._last_update = parsed

        if self._last_reset_date is None:
            if self._last_update is not None:
                self._last_reset_date = self._last_update.date()
            else:
                self._last_reset_date = dt_util.now().date()

    def update(self):
        """Berechne den täglichen Verbrauch:
           - Hole die aktuelle ConsumptionActivePower (Watt).
           - Berechne die seit dem letzten Update verstrichene Zeit.
           - Integriere die Leistung (Watt * Zeit) zu Energie (kWh).
           - Setze den Tageszähler bei Tageswechsel zurück.
        """
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_reset_date is None:
            self._last_reset_date = now.date()
        if now.date() != self._last_reset_date:
            self._daily_energy = 0.0
            self._last_reset_date = now.date()
            self._last_update = None

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

class DailyGridFeedInSensor(SensorEntity, RestoreEntity):
    """Sensor zur Berechnung der täglichen Netzeinspeisung in kWh."""

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_feed_in = 0.0  # akkumulierte Einspeisung in kWh
        self._last_update = None
        self._last_reset_date = None
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

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._last_update is not None:
            attrs["last_update"] = dt_util.as_local(self._last_update).isoformat()
        if self._last_reset_date is not None:
            attrs["last_reset"] = self._last_reset_date.isoformat()
        return attrs

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            self._last_reset_date = dt_util.now().date()
            return

        try:
            restored_value = float(last_state.state)
        except (TypeError, ValueError):
            restored_value = None

        if restored_value is not None:
            self._daily_feed_in = restored_value
            self._state = restored_value

        last_reset = last_state.attributes.get("last_reset")
        if last_reset:
            parsed = dt_util.parse_date(last_reset)
            if parsed is not None:
                self._last_reset_date = parsed

        last_update = last_state.attributes.get("last_update")
        if last_update:
            parsed = dt_util.parse_datetime(last_update)
            if parsed is not None:
                self._last_update = parsed

        if self._last_reset_date is None:
            if self._last_update is not None:
                self._last_reset_date = self._last_update.date()
            else:
                self._last_reset_date = dt_util.now().date()

    def update(self):
        """Berechne die tägliche Einspeisung."""
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_reset_date is None:
            self._last_reset_date = now.date()
        if now.date() != self._last_reset_date:
            self._daily_feed_in = 0.0
            self._last_reset_date = now.date()
            self._last_update = None

        # Aktuellen Wert von GridActivePower abrufen
        try:
            url = f"{self._base_url}GridActivePower"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            grid_power = data.get("value", None)
            if grid_power is None:
                return
            grid_power = float(grid_power)
            if grid_power >= 0:
                grid_power = 0.0
            else:
                grid_power = abs(grid_power)  # Nur negative Werte (Einspeisung)
        except Exception as e:
            return

        if self._last_update is not None:
            dt_seconds = (now - self._last_update).total_seconds()
            self._daily_feed_in += grid_power * dt_seconds / 3600000.0

        self._last_update = now
        self._state = self._daily_feed_in

class DailyGridConsumptionSensor(SensorEntity, RestoreEntity):
    """Sensor zur Berechnung des täglichen Netzbezugs in kWh."""

    def __init__(self, session, base_url):
        self._session = session
        self._base_url = base_url
        self._daily_consumption = 0.0  # akkumulierter Bezug in kWh
        self._last_update = None
        self._last_reset_date = None
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

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._last_update is not None:
            attrs["last_update"] = dt_util.as_local(self._last_update).isoformat()
        if self._last_reset_date is not None:
            attrs["last_reset"] = self._last_reset_date.isoformat()
        return attrs

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            self._last_reset_date = dt_util.now().date()
            return

        try:
            restored_value = float(last_state.state)
        except (TypeError, ValueError):
            restored_value = None

        if restored_value is not None:
            self._daily_consumption = restored_value
            self._state = restored_value

        last_reset = last_state.attributes.get("last_reset")
        if last_reset:
            parsed = dt_util.parse_date(last_reset)
            if parsed is not None:
                self._last_reset_date = parsed

        last_update = last_state.attributes.get("last_update")
        if last_update:
            parsed = dt_util.parse_datetime(last_update)
            if parsed is not None:
                self._last_update = parsed

        if self._last_reset_date is None:
            if self._last_update is not None:
                self._last_reset_date = self._last_update.date()
            else:
                self._last_reset_date = dt_util.now().date()

    def update(self):
        """Berechne den täglichen Netzbezug."""
        now = dt_util.now()

        # Tageswechsel erkennen und den Zähler zurücksetzen
        if self._last_reset_date is None:
            self._last_reset_date = now.date()
        if now.date() != self._last_reset_date:
            self._daily_consumption = 0.0
            self._last_reset_date = now.date()
            self._last_update = None

        # Aktuellen Wert von GridActivePower abrufen
        try:
            url = f"{self._base_url}GridActivePower"
            response = self._session.get(url)
            response.raise_for_status()
            data = response.json()
            grid_power = data.get("value", None)
            if grid_power is None:
                return
            grid_power = float(grid_power)
            if grid_power <= 0:
                grid_power = 0.0
        except Exception as e:
            return

        if self._last_update is not None:
            dt_seconds = (now - self._last_update).total_seconds()
            self._daily_consumption += grid_power * dt_seconds / 3600000.0

        self._last_update = now
        self._state = self._daily_consumption
