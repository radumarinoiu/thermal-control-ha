import datetime
from typing import Dict, List, Any, Optional


class WeatherManager:
    """Manages weather forecast data and analysis.

    This class handles retrieving weather forecast information and providing
    analyzed data for climate control decisions.
    """

    def __init__(self, controller):
        """Initialize the weather manager.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config

        # Weather forecast configuration
        self.forecast_hours = int(self.config.get("forecast_hours", 12))

        # Initialize forecast data
        self.forecast_data = {}
        self.last_update = None

        # Update forecast immediately
        self.update_forecast()

    def update_forecast(self) -> None:
        """Update the weather forecast data."""
        # Get forecast entity
        entity_id = self.controller.entity_manager.get_weather_forecast_entity()
        if not entity_id:
            self.controller.log("Weather forecast entity not configured", level="WARNING")
            return

        try:
            # Get current state and forecast
            forecast_state = self.controller.get_state(entity_id, attribute="all")
            outside_temp_entity = self.controller.entity_manager.get_outside_temp_entity()
            outside_humidity_entity = self.controller.entity_manager.get_outside_humidity_entity()

            # Extract forecast data
            forecast_data = {}

            # Get current temperature and humidity
            if outside_temp_entity:
                try:
                    forecast_data["current_temperature"] = float(self.controller.get_state(outside_temp_entity))
                except (ValueError, TypeError):
                    forecast_data["current_temperature"] = forecast_state.get("attributes", {}).get("temperature")
            else:
                forecast_data["current_temperature"] = forecast_state.get("attributes", {}).get("temperature")

            if outside_humidity_entity:
                try:
                    forecast_data["current_humidity"] = float(self.controller.get_state(outside_humidity_entity))
                except (ValueError, TypeError):
                    forecast_data["current_humidity"] = forecast_state.get("attributes", {}).get("humidity")
            else:
                forecast_data["current_humidity"] = forecast_state.get("attributes", {}).get("humidity")

            # Get forecast attributes
            attributes = forecast_state.get("attributes", {})
            forecast_data["condition"] = attributes.get("forecast", [{}])[0].get("condition", "unknown")
            forecast_data["temperature"] = attributes.get("forecast", [{}])[0].get("temperature")
            forecast_data["wind_speed"] = attributes.get("forecast", [{}])[0].get("wind_speed", 0)
            forecast_data["precipitation"] = attributes.get("forecast", [{}])[0].get("precipitation", 0)

            # Get more detailed forecast data if available
            forecast_data["hourly"] = []
            for hour in range(min(self.forecast_hours, len(attributes.get("forecast", [])))):
                if hour < len(attributes.get("forecast", [])):
                    forecast_data["hourly"].append(attributes.get("forecast", [])[hour])

            # Calculate temperature trend
            if forecast_data["hourly"] and len(forecast_data["hourly"]) > 1:
                current = forecast_data["current_temperature"]
                future = forecast_data["hourly"][-1].get("temperature")
                if future is not None and current is not None:
                    forecast_data["trend"] = future - current
                else:
                    forecast_data["trend"] = 0
            else:
                forecast_data["trend"] = 0

            # Update internal data
            self.forecast_data = forecast_data
            self.last_update = self.controller.datetime()

            self.controller.log(f"Weather forecast updated. Current temp: {forecast_data['current_temperature']}°C", 
                                level="INFO")
        except Exception as e:
            self.controller.log(f"Error updating weather forecast: {e}", level="ERROR")

    def get_forecast_data(self) -> Dict[str, Any]:
        """Get the latest forecast data.

        Returns:
            Dictionary with forecast information
        """
        # Check if we need to update
        now = self.controller.datetime()
        if (self.last_update is None or 
                (now - self.last_update).total_seconds() > 1800):  # Update every 30 minutes
            self.update_forecast()

        return self.forecast_data

    def get_outdoor_temperature(self) -> Optional[float]:
        """Get the current outdoor temperature."""
        if "current_temperature" in self.forecast_data:
            return self.forecast_data["current_temperature"]

        # Try to get it directly from the entity
        entity_id = self.controller.entity_manager.get_outside_temp_entity()
        if entity_id:
            try:
                return float(self.controller.get_state(entity_id))
            except (ValueError, TypeError):
                pass

        return None

    def get_outdoor_humidity(self) -> Optional[float]:
        """Get the current outdoor humidity."""
        if "current_humidity" in self.forecast_data:
            return self.forecast_data["current_humidity"]

        # Try to get it directly from the entity
        entity_id = self.controller.entity_manager.get_outside_humidity_entity()
        if entity_id:
            try:
                return float(self.controller.get_state(entity_id))
            except (ValueError, TypeError):
                pass

        return None

    def is_heating_favorable(self) -> bool:
        """Determine if weather conditions favor heating operations."""
        forecast = self.get_forecast_data()

        # Check if it's going to get colder
        if forecast.get("trend", 0) < -1.0:
            return True

        # Check if it's already cold
        current_temp = forecast.get("current_temperature")
        if current_temp is not None and current_temp < 10.0:
            return True

        return False

    def is_cooling_favorable(self) -> bool:
        """Determine if weather conditions favor cooling operations."""
        forecast = self.get_forecast_data()

        # Check if it's going to get warmer
        if forecast.get("trend", 0) > 1.0:
            return True

        # Check if it's already warm
        current_temp = forecast.get("current_temperature")
        if current_temp is not None and current_temp > 25.0:
            return True

        return False
