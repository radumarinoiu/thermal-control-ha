from typing import Dict, List, Any, Optional, Union


class ClimateDecisionEngine:
    """Engine for making climate control decisions.

    This class handles the logic for deciding what climate control actions to take
    based on current conditions, preferences, and available power sources.
    """

    def __init__(self, controller):
        """Initialize the decision engine.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config

        # Load decision parameters from config
        self.temp_tolerance = float(self.config.get("temp_tolerance", 0.5))
        self.ac_min_temp = float(self.config.get("ac_min_temp", 16.0))
        self.ac_max_temp = float(self.config.get("ac_max_temp", 30.0))
        self.heater_min_temp = float(self.config.get("heater_min_temp", 35.0))
        self.prioritize_solar = bool(self.config.get("prioritize_solar", True))
        self.solar_excess_threshold = float(self.config.get("solar_excess_threshold", 500.0))  # Watts
        self.battery_threshold = float(self.config.get("battery_threshold", 50.0))  # Percent
        self.prefer_floor_heating = bool(self.config.get("prefer_floor_heating", True))

    def get_climate_decision(self, 
                             room_id: str,
                             current_temp: float,
                             target_temp: float,
                             window_open: bool,
                             room_occupied: bool,
                             home_occupied: bool,
                             renewable_power: float,
                             weather_forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the optimal climate control action for a room.

        Args:
            room_id: Room identifier
            current_temp: Current room temperature
            target_temp: Target temperature for the room
            window_open: Whether the window is open
            room_occupied: Whether the room is currently occupied
            home_occupied: Whether anyone is home
            renewable_power: Available power from renewable sources (W)
            weather_forecast: Weather forecast data

        Returns:
            Dictionary with the decision and its parameters:
            {
                "action": One of ["no_action", "heat_with_ac", "cool_with_ac", 
                                  "heat_with_floor", "heat_with_ac_and_floor"],
                "ac_mode": AC mode to set ("heat", "cool", "off", etc.),
                "ac_temp": Temperature to set the AC to,
                "floor_heating": Whether to turn on floor heating,
                "reason": Explanation for the decision
            }
        """
        # Base decision structure
        decision = {
            "action": "no_action",
            "ac_mode": "off",
            "ac_temp": None,
            "floor_heating": False,
            "reason": "No action needed"
        }

        # Get room-specific settings
        room_config = self.controller.rooms.get(room_id, {})
        room_tolerance = float(room_config.get("temp_tolerance", self.temp_tolerance))

        # If window is open, turn everything off
        if window_open:
            decision["reason"] = "Window is open, disabling climate control"
            return decision

        # If home is unoccupied and eco mode is enabled, adjust target
        eco_mode = self.config.get("eco_mode_when_away", True)
        eco_temp_heating = float(self.config.get("eco_temp_heating", 16.0))
        eco_temp_cooling = float(self.config.get("eco_temp_cooling", 26.0))

        effective_target = target_temp
        if not home_occupied and eco_mode:
            # If current temp is below target (heating needed), use eco_temp_heating
            if current_temp < target_temp:
                effective_target = eco_temp_heating
                decision["reason"] = f"Eco mode active (away): using {eco_temp_heating}°C instead of {target_temp}°C"
            # If current temp is above target (cooling needed), use eco_temp_cooling
            elif current_temp > target_temp:
                effective_target = eco_temp_cooling
                decision["reason"] = f"Eco mode active (away): using {eco_temp_cooling}°C instead of {target_temp}°C"

        # Check if room needs heating
        if current_temp < (effective_target - room_tolerance):
            return self._get_heating_decision(
                room_id, current_temp, effective_target, renewable_power, weather_forecast
            )

        # Check if room needs cooling
        elif current_temp > (effective_target + room_tolerance):
            return self._get_cooling_decision(
                room_id, current_temp, effective_target, renewable_power, weather_forecast
            )

        # No action needed - temperature is within tolerance
        decision["reason"] = f"Temperature ({current_temp}°C) is within tolerance of target ({effective_target}°C)"
        return decision

    def _get_heating_decision(self,
                             room_id: str,
                             current_temp: float,
                             target_temp: float,
                             renewable_power: float,
                             weather_forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best heating strategy."""
        # Start with the base decision
        decision = {
            "action": "no_action",
            "ac_mode": "off",
            "ac_temp": None,
            "floor_heating": False,
            "reason": "Evaluating heating options"
        }

        # Calculate how much heating is needed
        temp_difference = target_temp - current_temp

        # Get room-specific config
        room_config = self.controller.rooms.get(room_id, {})
        floor_heating_available = room_config.get("floor_heating_available", True)
        ac_heating_available = room_config.get("ac_heating_available", True)
        floor_heating_cost = float(room_config.get("floor_heating_cost", 1.0))  # Relative cost factor
        ac_heating_cost = float(room_config.get("ac_heating_cost", 1.5))  # Relative cost factor

        # Get central heater temperature
        heater_temp = self._get_central_heater_temp()

        # Check if we have enough renewable power
        enough_renewable = renewable_power > self.solar_excess_threshold

        # Get expected outdoor temperature trend
        temp_trend = self._get_temperature_trend(weather_forecast)

        # Determine the best heating strategy based on conditions

        # If we have floor heating and the heater is warm enough
        if floor_heating_available and heater_temp > self.heater_min_temp:
            # If temperature difference is small, floor heating alone might be enough
            if temp_difference < 1.5:
                decision["action"] = "heat_with_floor"
                decision["floor_heating"] = True
                decision["reason"] = f"Using floor heating: small temp difference ({temp_difference:.1f}°C)"

            # If temperature difference is larger, might need both AC and floor
            elif ac_heating_available:
                # If we have renewable power or it's very cold
                if enough_renewable or temp_difference > 3.0:
                    decision["action"] = "heat_with_ac_and_floor"
                    decision["ac_mode"] = "heat"
                    decision["ac_temp"] = min(self.ac_max_temp, target_temp + 0.5)
                    decision["floor_heating"] = True
                    if enough_renewable:
                        decision["reason"] = f"Using both AC and floor heating: renewable power available and {temp_difference:.1f}°C difference"
                    else:
                        decision["reason"] = f"Using both AC and floor heating: large temp difference ({temp_difference:.1f}°C)"
                else:
                    # If outdoor temperature is dropping, start floor heating
                    if temp_trend == "dropping":
                        decision["action"] = "heat_with_floor"
                        decision["floor_heating"] = True
                        decision["reason"] = f"Using floor heating: outdoor temp dropping, preparing for colder weather"
                    # Otherwise use the cheaper option
                    elif floor_heating_cost <= ac_heating_cost:
                        decision["action"] = "heat_with_floor"
                        decision["floor_heating"] = True
                        decision["reason"] = f"Using floor heating: more cost-effective than AC"
                    else:
                        decision["action"] = "heat_with_ac"
                        decision["ac_mode"] = "heat"
                        decision["ac_temp"] = min(self.ac_max_temp, target_temp + 0.5)
                        decision["reason"] = f"Using AC heating: more cost-effective than floor heating"
            else:
                # No AC available, use floor heating
                decision["action"] = "heat_with_floor"
                decision["floor_heating"] = True
                decision["reason"] = f"Using floor heating: AC heating not available"

        # If we have AC heating but no floor heating (or heater isn't warm enough)
        elif ac_heating_available:
            decision["action"] = "heat_with_ac"
            decision["ac_mode"] = "heat"
            decision["ac_temp"] = min(self.ac_max_temp, target_temp + 0.5)

            if not floor_heating_available:
                decision["reason"] = f"Using AC heating: floor heating not available"
            else:
                decision["reason"] = f"Using AC heating: central heater temp too low ({heater_temp:.1f}°C)"

        # If no heating options are available
        else:
            decision["reason"] = "No heating options available for this room"

        return decision

    def _get_cooling_decision(self,
                             room_id: str,
                             current_temp: float,
                             target_temp: float,
                             renewable_power: float,
                             weather_forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best cooling strategy."""
        # Start with the base decision
        decision = {
            "action": "no_action",
            "ac_mode": "off",
            "ac_temp": None,
            "floor_heating": False,
            "reason": "Evaluating cooling options"
        }

        # Calculate how much cooling is needed
        temp_difference = current_temp - target_temp

        # Get room-specific config
        room_config = self.controller.rooms.get(room_id, {})
        ac_cooling_available = room_config.get("ac_cooling_available", True)

        # If AC cooling is available
        if ac_cooling_available:
            decision["action"] = "cool_with_ac"
            decision["ac_mode"] = "cool"
            decision["ac_temp"] = max(self.ac_min_temp, target_temp - 0.5)

            # Check if we have renewable power
            if renewable_power > self.solar_excess_threshold:
                decision["reason"] = f"Using AC cooling: {temp_difference:.1f}°C above target, renewable power available"
                # If we have lots of excess power, we can cool more aggressively
                if renewable_power > self.solar_excess_threshold * 3:
                    decision["ac_temp"] = max(self.ac_min_temp, target_temp - 1.0)
                    decision["reason"] = f"Using aggressive AC cooling: high renewable power available ({renewable_power:.0f}W)"
            else:
                decision["reason"] = f"Using AC cooling: {temp_difference:.1f}°C above target"
        else:
            decision["reason"] = "No cooling options available for this room"

        return decision

    def _get_central_heater_temp(self) -> float:
        """Get the current central heater temperature."""
        entity_id = self.controller.entity_manager.get_central_heater_entity()
        if not entity_id:
            return 0.0

        try:
            return float(self.controller.get_state(entity_id))
        except (ValueError, TypeError):
            self.controller.log("Invalid central heater temperature", level="WARNING")
            return 0.0

    def _get_temperature_trend(self, forecast_data: Dict[str, Any]) -> str:
        """Analyze forecast data to determine temperature trend.

        Returns:
            "rising", "steady", or "dropping"
        """
        if not forecast_data or "temperature" not in forecast_data:
            return "steady"

        # Simple logic - compare current to forecast
        try:
            current = forecast_data.get("current_temperature", 0)
            forecast = forecast_data.get("temperature", 0)

            if forecast > current + 1:
                return "rising"
            elif forecast < current - 1:
                return "dropping"
            else:
                return "steady"
        except (TypeError, ValueError):
            return "steady"
