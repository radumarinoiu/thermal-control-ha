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
        self.battery_state_of_charge = 0.0  # Percentage (0-100)
        self.battery_energy_left = 0.0  # kWh - Calculated energy left in battery
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

        # Update battery state of charge
        battery_soc_entity = self.controller.entity_manager.get_battery_soc_entity()

        # Get battery state of charge percentage
        if battery_soc_entity:
            try:
                self.battery_state_of_charge = float(self.controller.get_state(battery_soc_entity))
                # Calculate energy left in the battery
                self.battery_energy_left = (self.battery_state_of_charge / 100.0) * self.battery_max
            except (ValueError, TypeError):
                self.controller.log("Invalid battery state of charge value", level="WARNING")

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

    def update_battery_soc(self, value: float) -> None:
        """Update the battery state of charge value.

        Args:
            value: Battery state of charge in percentage (0-100)
        """
        self.battery_state_of_charge = value
        # Recalculate energy left based on new state of charge
        self.battery_energy_left = (value / 100.0) * self.battery_max

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
        # Check if we have direct solar excess (negative value means excess/exported power)
        if self.solar_excess < -self.min_solar_excess:
            return abs(self.solar_excess)

        # If battery is well-charged, we can also use that
        if self.battery_state_of_charge > self.min_battery_percent:
            # Calculate an equivalent power based on battery state of charge
            # Higher battery = more power available
            excess_percent = self.battery_state_of_charge - self.min_battery_percent
            if excess_percent > 0:
                # Scale from 0 to 1000W based on excess battery percentage
                battery_power = (excess_percent / (100.0 - self.min_battery_percent)) * 1000.0
                return max(battery_power, self.solar_excess)

        # Not enough renewable power available
        return self.solar_excess

    def is_heater_ready(self) -> bool:
        """Check if the gas water heater is ready for use.

        For on-demand gas water heaters, we assume it's always ready
        since it heats up the water when needed.

        Returns:
            True as the gas water heater is always available
        """
        return True

    def calculate_optimal_heater_temp(self, outdoor_temp: Optional[float] = None) -> float:
        """Calculate the optimal water temperature for the gas water heater based on outdoor temperature.

        Args:
            outdoor_temp: Current outdoor temperature in Celsius. If None, will be retrieved.

        Returns:
            Optimal water temperature in Celsius
        """
        # Get outdoor temperature if not provided
        if outdoor_temp is None:
            weather_manager = self.controller.weather_manager
            if weather_manager:
                outdoor_temp = weather_manager.get_outdoor_temperature()

        # Default temperature if we can't get outdoor temperature
        if outdoor_temp is None:
            return float(self.config.get("default_heater_temp", 45.0))

        # Calculate optimal temperature based on outdoor temperature
        # Colder outside = hotter water needed to maintain comfort

        # Get configuration values
        min_outdoor_temp = float(self.config.get("min_outdoor_temp", -10.0))  # Celsius
        max_outdoor_temp = float(self.config.get("max_outdoor_temp", 20.0))  # Celsius
        min_heater_temp = float(self.config.get("min_heater_temp", 35.0))  # Celsius
        max_heater_temp = float(self.config.get("max_heater_temp", 55.0))  # Celsius

        # Ensure outdoor temperature is within expected range
        outdoor_temp = max(min_outdoor_temp, min(max_outdoor_temp, outdoor_temp))

        # Linear mapping: colder outside = hotter water
        # When outside is at max_outdoor_temp, heater is at min_heater_temp
        # When outside is at min_outdoor_temp, heater is at max_heater_temp
        temp_range = max_outdoor_temp - min_outdoor_temp
        if temp_range == 0:  # Avoid division by zero
            return (min_heater_temp + max_heater_temp) / 2

        # Calculate percentage of how cold it is (0% = warmest, 100% = coldest)
        cold_percent = (max_outdoor_temp - outdoor_temp) / temp_range

        # Calculate heater temperature based on cold percentage
        heater_temp = min_heater_temp + cold_percent * (max_heater_temp - min_heater_temp)

        return round(heater_temp, 1)

    def get_power_status(self) -> Dict[str, Any]:
        """Get the current power status information.

        Returns:
            Dictionary with power status information
        """
        # Get outdoor temperature for optimal heater temp calculation
        outdoor_temp = None
        if hasattr(self.controller, 'weather_manager'):
            outdoor_temp = self.controller.weather_manager.get_outdoor_temperature()

        return {
            "solar_excess": self.solar_excess,
            "battery_state_of_charge": self.battery_state_of_charge,
            "battery_energy_left": self.battery_energy_left,
            "heater_temperature": self.heater_temperature,
            "optimal_heater_temp": self.calculate_optimal_heater_temp(outdoor_temp),
            "renewable_power_available": self.get_available_renewable_power(),
            "heater_ready": self.is_heater_ready()
        }
