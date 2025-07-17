from typing import Dict, List, Any, Optional


class PowerManager:
    """Manages power sources and consumption information.

    This class handles tracking available renewable power, battery status,
    and central heating system status.
    """

    def __init__(self, controller):
        """Initialize the power manager.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config

        # Initialize power-related values
        self.solar_excess = 0.0  # Watts
        self.battery_capacity = 0.0  # kWh
        self.battery_percentage = 0.0  # Percent
        self.heater_temperature = 0.0  # Celsius

        # Configuration values
        self.battery_max = float(self.config.get("battery_max_capacity", 10.0))  # kWh
        self.min_solar_excess = float(self.config.get("min_solar_excess", 300.0))  # Watts
        self.min_battery_percent = float(self.config.get("min_battery_percent", 20.0))  # Percent

        # Update initial values
        self.update_power_status()

    def update_power_status(self) -> None:
        """Update all power-related status information."""
        # Update solar excess
        solar_entity = self.controller.entity_manager.get_solar_excess_entity()
        if solar_entity:
            try:
                self.solar_excess = float(self.controller.get_state(solar_entity))
            except (ValueError, TypeError):
                self.controller.log("Invalid solar excess value", level="WARNING")

        # Update battery capacity
        battery_entity = self.controller.entity_manager.get_battery_entity()
        if battery_entity:
            try:
                self.battery_capacity = float(self.controller.get_state(battery_entity))
                self.battery_percentage = (self.battery_capacity / self.battery_max) * 100.0 \
                    if self.battery_max > 0 else 0.0
            except (ValueError, TypeError):
                self.controller.log("Invalid battery capacity value", level="WARNING")

        # Update heater temperature
        heater_entity = self.controller.entity_manager.get_central_heater_entity()
        if heater_entity:
            try:
                self.heater_temperature = float(self.controller.get_state(heater_entity))
            except (ValueError, TypeError):
                self.controller.log("Invalid heater temperature value", level="WARNING")

    def update_solar_excess(self, value: float) -> None:
        """Update the solar excess power value.

        Args:
            value: Solar excess power in Watts
        """
        self.solar_excess = value

    def update_battery_capacity(self, value: float) -> None:
        """Update the battery capacity value.

        Args:
            value: Battery capacity in kWh
        """
        self.battery_capacity = value
        self.battery_percentage = (value / self.battery_max) * 100.0 if self.battery_max > 0 else 0.0

    def update_heater_temperature(self, value: float) -> None:
        """Update the central heater temperature value.

        Args:
            value: Heater temperature in Celsius
        """
        self.heater_temperature = value

    def get_available_renewable_power(self) -> float:
        """Get the amount of available renewable power.

        Returns:
            Available power in Watts that can be used for climate control
        """
        # Check if we have direct solar excess
        if self.solar_excess > self.min_solar_excess:
            return self.solar_excess

        # If battery is well-charged, we can also use that
        if self.battery_percentage > self.min_battery_percent:
            # Calculate an equivalent power based on battery percentage
            # Higher battery = more power available
            excess_percent = self.battery_percentage - self.min_battery_percent
            if excess_percent > 0:
                # Scale from 0 to 1000W based on excess battery percentage
                battery_power = (excess_percent / (100.0 - self.min_battery_percent)) * 1000.0
                return max(battery_power, self.solar_excess)

        # Not enough renewable power available
        return self.solar_excess

    def is_heater_ready(self) -> bool:
        """Check if the central heater is at a suitable temperature for use.

        Returns:
            True if the heater is ready, False otherwise
        """
        min_temp = float(self.config.get("min_heater_temp", 35.0))  # Celsius
        return self.heater_temperature >= min_temp

    def get_power_status(self) -> Dict[str, Any]:
        """Get the current power status information.

        Returns:
            Dictionary with power status information
        """
        return {
            "solar_excess": self.solar_excess,
            "battery_capacity": self.battery_capacity,
            "battery_percentage": self.battery_percentage,
            "heater_temperature": self.heater_temperature,
            "renewable_power_available": self.get_available_renewable_power(),
            "heater_ready": self.is_heater_ready()
        }
