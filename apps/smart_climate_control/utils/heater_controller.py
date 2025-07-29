from typing import Dict, List, Any, Optional


class HeaterController:
    """Controls the gas water heater for in-floor heating.

    This class manages setting the appropriate temperature for the 
    on-demand gas water heater based on outdoor conditions.
    """

    def __init__(self, controller):
        """Initialize the heater controller.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config

        # Get entity for controlling the heater
        self.heater_entity = self.config.get("global_entities", {}).get("central_heater_control")

        # Initialize with default values
        self.current_heater_temp = 0.0
        self.target_heater_temp = 0.0

        # Configuration values
        self.min_heater_temp = float(self.config.get("min_heater_temp", 35.0))  # Celsius
        self.max_heater_temp = float(self.config.get("max_heater_temp", 55.0))  # Celsius
        self.default_heater_temp = float(self.config.get("default_heater_temp", 45.0))  # Celsius

    def set_heater_temperature(self, temperature: float) -> bool:
        """Set the gas water heater to the specified temperature.

        Args:
            temperature: Target temperature in Celsius

        Returns:
            True if successful, False otherwise
        """
        # Ensure temperature is within safe range
        temperature = max(self.min_heater_temp, min(self.max_heater_temp, temperature))

        # Round to single decimal for cleaner display
        temperature = round(temperature, 1)

        # Only update if we have a heater entity to control
        if not self.heater_entity:
            self.controller.log("Cannot set heater temperature: no heater control entity configured", level="WARNING")
            return False

        try:
            # Set the temperature using the appropriate service
            # This will depend on your specific heater integration
            self.controller.call_service(
                "climate/set_temperature", 
                entity_id=self.heater_entity,
                temperature=temperature
            )

            self.controller.log(f"Set gas water heater temperature to {temperature}°C", level="INFO")
            self.target_heater_temp = temperature
            return True
        except Exception as e:
            self.controller.log(f"Error setting heater temperature: {e}", level="ERROR")
            return False

    def update_heater_based_on_weather(self) -> None:
        """Update the heater temperature based on current weather conditions."""
        # Get the optimal temperature from power manager
        optimal_temp = self.controller.power_manager.calculate_optimal_heater_temp()

        # Only update if it's significantly different from current target
        if abs(optimal_temp - self.target_heater_temp) >= 1.0:
            self.set_heater_temperature(optimal_temp)

    def get_heater_status(self) -> Dict[str, Any]:
        """Get the current status of the heater.

        Returns:
            Dictionary with heater status information
        """
        # Get current temperature from entity if available
        current_temp = 0.0
        if self.heater_entity:
            try:
                current_temp = float(self.controller.get_state(self.heater_entity, attribute="current_temperature"))
            except (ValueError, TypeError):
                # Try getting temperature directly from state
                try:
                    current_temp = float(self.controller.get_state(self.heater_entity))
                except (ValueError, TypeError):
                    self.controller.log("Could not get current heater temperature", level="WARNING")

        self.current_heater_temp = current_temp

        return {
            "current_temperature": self.current_heater_temp,
            "target_temperature": self.target_heater_temp,
            "min_temperature": self.min_heater_temp,
            "max_temperature": self.max_heater_temp
        }
