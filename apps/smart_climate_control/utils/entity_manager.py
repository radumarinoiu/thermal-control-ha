from typing import Dict, List, Any, Optional, Union


class EntityManager:
    """Manages all entity IDs and their retrieval based on configuration.

    This class centralizes all entity ID resolution and state access to make
    the system more maintainable and configurable.
    """

    def __init__(self, controller):
        """Initialize the entity manager.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config
        self.rooms = controller.rooms

        # Entity ID templates
        self.entity_templates = self.config.get("entity_templates", {})

        # Default templates if not provided in config
        if not self.entity_templates:
            self.entity_templates = {
                "temperature": "sensor.{room_id}_thermohygrometer_temperature",
                "humidity": "sensor.{room_id}_thermohygrometer_humidity",
                "window": "binary_sensor.{room_id}_window",
                "ac": "climate.{room_id}_ac",
                "floor_heating": "switch.{room_id}_floor_heating",
                "lux": "sensor.{room_id}_lux_{window_id}",
                "presence": "binary_sensor.{room_id}_presence",
                "target_temp_day": "input_number.{room_id}_target_temp_day",
                "target_temp_night": "input_number.{room_id}_target_temp_night"
            }

        # Global entity IDs
        self.global_entities = self.config.get("global_entities", {})

        # Default global entities if not provided
        if not self.global_entities:
            self.global_entities = {
                "central_heater_temp": "sensor.central_heater_temperature",
                "solar_excess": "sensor.solar_power_excess",
                "battery_capacity": "sensor.battery_capacity",
                "outside_temp": "sensor.outside_temperature",
                "outside_humidity": "sensor.outside_humidity",
                "weather_forecast": "weather.forecast",
                "global_presence": ["binary_sensor.presence_sensor_1", "binary_sensor.presence_sensor_2"]
            }

    def get_temperature_entity(self, room_id: str) -> Optional[str]:
        """Get the temperature sensor entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "temperature_entity" in room_config:
            return room_config["temperature_entity"]

        # Use the template
        return self.entity_templates.get("temperature", "").format(room_id=room_id)

    def get_humidity_entity(self, room_id: str) -> Optional[str]:
        """Get the humidity sensor entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "humidity_entity" in room_config:
            return room_config["humidity_entity"]

        # Use the template
        return self.entity_templates.get("humidity", "").format(room_id=room_id)

    def get_window_entity(self, room_id: str) -> Optional[str]:
        """Get the window sensor entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "window_entity" in room_config:
            return room_config["window_entity"]

        # Use the template
        return self.entity_templates.get("window", "").format(room_id=room_id)

    def get_ac_entity(self, room_id: str) -> Optional[str]:
        """Get the AC entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "ac_entity" in room_config:
            return room_config["ac_entity"]

        # Use the template
        return self.entity_templates.get("ac", "").format(room_id=room_id)

    def get_floor_heating_entity(self, room_id: str) -> Optional[str]:
        """Get the floor heating entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "floor_heating_entity" in room_config:
            return room_config["floor_heating_entity"]

        # Use the template
        return self.entity_templates.get("floor_heating", "").format(room_id=room_id)

    def get_lux_entities(self, room_id: str) -> List[str]:
        """Get the lux sensor entity IDs for a room (multiple windows)."""
        room_config = self.rooms.get(room_id, {})

        # Check if there are custom entities defined for this room
        if "lux_entities" in room_config:
            return room_config["lux_entities"]

        # Use the template with window IDs from config
        lux_entities = []
        window_ids = room_config.get("window_ids", ["main"])  # Default to 'main' if not specified

        for window_id in window_ids:
            entity = self.entity_templates.get("lux", "").format(
                room_id=room_id, window_id=window_id
            )
            lux_entities.append(entity)

        return lux_entities

    def get_presence_entity(self, room_id: str) -> Optional[str]:
        """Get the presence sensor entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "presence_entity" in room_config:
            return room_config["presence_entity"]

        # Use the template
        return self.entity_templates.get("presence", "").format(room_id=room_id)

    def get_target_temp_day_entity(self, room_id: str) -> Optional[str]:
        """Get the day target temperature entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "target_temp_day_entity" in room_config:
            return room_config["target_temp_day_entity"]

        # Use the template
        return self.entity_templates.get("target_temp_day", "").format(room_id=room_id)

    def get_target_temp_night_entity(self, room_id: str) -> Optional[str]:
        """Get the night target temperature entity ID for a room."""
        room_config = self.rooms.get(room_id, {})

        # Check if there's a custom entity defined for this room
        if "target_temp_night_entity" in room_config:
            return room_config["target_temp_night_entity"]

        # Use the template
        return self.entity_templates.get("target_temp_night", "").format(room_id=room_id)

    def get_central_heater_entity(self) -> Optional[str]:
        """Get the central heater temperature entity ID."""
        return self.global_entities.get("central_heater_temp")

    def get_solar_excess_entity(self) -> Optional[str]:
        """Get the solar excess power entity ID."""
        return self.global_entities.get("solar_excess")

    def get_battery_entity(self) -> Optional[str]:
        """Get the battery capacity entity ID."""
        return self.global_entities.get("battery_capacity")

    def get_outside_temp_entity(self) -> Optional[str]:
        """Get the outside temperature entity ID."""
        return self.global_entities.get("outside_temp")

    def get_outside_humidity_entity(self) -> Optional[str]:
        """Get the outside humidity entity ID."""
        return self.global_entities.get("outside_humidity")

    def get_weather_forecast_entity(self) -> Optional[str]:
        """Get the weather forecast entity ID."""
        return self.global_entities.get("weather_forecast")

    def get_global_presence_entities(self) -> List[str]:
        """Get all global presence sensor entity IDs."""
        entities = self.global_entities.get("global_presence", [])
        if isinstance(entities, str):
            return [entities]
        return entities

    # Methods to get actual values

    def get_current_temperature(self, room_id: str) -> Optional[float]:
        """Get the current temperature value for a room."""
        entity_id = self.get_temperature_entity(room_id)
        if not entity_id:
            return None

        try:
            return float(self.controller.get_state(entity_id))
        except (ValueError, TypeError):
            self.controller.log(f"Invalid temperature value for {room_id}", level="WARNING")
            return None

    def get_current_humidity(self, room_id: str) -> Optional[float]:
        """Get the current humidity value for a room."""
        entity_id = self.get_humidity_entity(room_id)
        if not entity_id:
            return None

        try:
            return float(self.controller.get_state(entity_id))
        except (ValueError, TypeError):
            self.controller.log(f"Invalid humidity value for {room_id}", level="WARNING")
            return None

    def is_window_open(self, room_id: str) -> bool:
        """Check if the window is open for a room."""
        entity_id = self.get_window_entity(room_id)
        if not entity_id:
            return False

        return self.controller.get_state(entity_id) == "on"

    def get_average_lux(self, room_id: str) -> Optional[float]:
        """Get the average lux value from all window sensors in a room."""
        entities = self.get_lux_entities(room_id)
        if not entities:
            return None

        values = []
        for entity_id in entities:
            try:
                lux_value = float(self.controller.get_state(entity_id))
                values.append(lux_value)
            except (ValueError, TypeError):
                pass

        if not values:
            return None

        return sum(values) / len(values)

    def get_target_day_temp(self, room_id: str) -> float:
        """Get the target day temperature for a room."""
        # First check if there's a fixed value in the room config
        room_config = self.rooms.get(room_id, {})
        if "target_temp_day" in room_config:
            return float(room_config["target_temp_day"])

        # Otherwise, get from entity
        entity_id = self.get_target_temp_day_entity(room_id)
        if entity_id:
            try:
                return float(self.controller.get_state(entity_id))
            except (ValueError, TypeError):
                pass

        # Fall back to global default
        return float(self.config.get("default_target_temp_day", 21.0))

    def get_target_night_temp(self, room_id: str) -> float:
        """Get the target night temperature for a room."""
        # First check if there's a fixed value in the room config
        room_config = self.rooms.get(room_id, {})
        if "target_temp_night" in room_config:
            return float(room_config["target_temp_night"])

        # Otherwise, get from entity
        entity_id = self.get_target_temp_night_entity(room_id)
        if entity_id:
            try:
                return float(self.controller.get_state(entity_id))
            except (ValueError, TypeError):
                pass

        # Fall back to global default
        return float(self.config.get("default_target_temp_night", 18.0))
