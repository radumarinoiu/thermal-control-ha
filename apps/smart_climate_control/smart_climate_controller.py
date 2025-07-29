import appdaemon.plugins.hass.hassapi as hass
import datetime
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from .utils.entity_manager import EntityManager
from .utils.climate_decision import ClimateDecisionEngine
from .utils.weather_integration import WeatherManager
from .utils.presence_manager import PresenceManager
from .utils.schedule_manager import ScheduleManager
from .utils.power_manager import PowerManager
from .utils.heater_controller import HeaterController


class SmartClimateController(hass.Hass):
    """Main controller for the Smart Climate Control system.

    This app integrates various subsystems to control heating and cooling
    devices in different rooms based on temperature, presence, solar production,
    and other factors.
    """

    def initialize(self) -> None:
        """Initialize the controller and all subcomponents."""
        self.log("Smart Climate Controller initializing", level="INFO")

        # Set up logging
        self.log_level = self.args.get("log_level", "INFO")
        numeric_level = getattr(logging, self.log_level.upper(), None)
        if not isinstance(numeric_level, int):
            self.log(f"Invalid log level: {self.log_level}, defaulting to INFO", level="WARNING")
            numeric_level = logging.INFO

        # Initialize config
        self.config = self.args.copy()

        # Set up rooms configuration
        self.rooms = self.config.get("rooms", {})
        if not self.rooms:
            self.log("No rooms configured! Please check your configuration.", level="ERROR")
            return

        # Set up entity manager
        self.entity_manager = EntityManager(self)

        # Initialize subsystems
        self.weather_manager = WeatherManager(self)
        self.presence_manager = PresenceManager(self)
        self.schedule_manager = ScheduleManager(self)
        self.power_manager = PowerManager(self)
        self.heater_controller = HeaterController(self)
        self.decision_engine = ClimateDecisionEngine(self)

        # Register callbacks for various entities
        self._register_callbacks()

        # Initial state check and control decisions
        self.run_in(self._initial_check, 15)  # Run initial check after 15 seconds

        # Set up regular update intervals
        update_interval = self.config.get("update_interval", 300)  # Default 5 minutes
        self.run_every(self._periodic_update, "now", update_interval)

        # Set up day/night schedule changes
        self._setup_day_night_schedule()

        self.log("Smart Climate Controller initialized successfully", level="INFO")

    def _register_callbacks(self) -> None:
        """Register callbacks for all relevant entities."""
        # Register temperature sensors
        for room_id, room_config in self.rooms.items():
            # Temperature sensors
            temp_entity = self.entity_manager.get_temperature_entity(room_id)
            if temp_entity:
                self.listen_state(self._on_temperature_change, temp_entity, room_id=room_id)

            # Window sensors
            window_entity = self.entity_manager.get_window_entity(room_id)
            if window_entity:
                self.listen_state(self._on_window_change, window_entity, room_id=room_id)

            # Presence sensors (if room-specific and required)
            if room_config.get("presence_required", True):
                presence_entity = self.entity_manager.get_presence_entity(room_id)
                if presence_entity:
                    self.listen_state(self._on_presence_change, presence_entity, room_id=room_id)

        # Global presence sensors
        for presence_entity in self.entity_manager.get_global_presence_entities():
            self.listen_state(self._on_global_presence_change, presence_entity)

        # Solar power excess
        solar_excess_entity = self.entity_manager.get_solar_excess_entity()
        if solar_excess_entity:
            self.listen_state(self._on_solar_excess_change, solar_excess_entity)


        # Battery state of charge
        battery_soc_entity = self.entity_manager.get_battery_soc_entity()
        if battery_soc_entity:
            self.listen_state(self._on_battery_soc_change, battery_soc_entity)

        # Central heater temperature
        heater_temp_entity = self.entity_manager.get_central_heater_entity()
        if heater_temp_entity:
            self.listen_state(self._on_heater_temp_change, heater_temp_entity)

    def _initial_check(self, kwargs: Dict[str, Any]) -> None:
        """Perform initial check of all conditions and set initial states."""
        self.log("Performing initial system check", level="INFO")

        # Check current state of all rooms
        for room_id in self.rooms:
            self._evaluate_room(room_id)

    def _periodic_update(self, kwargs: Dict[str, Any]) -> None:
        """Run periodic updates for all rooms."""
        self.log("Running periodic update", level="DEBUG")

        # Update weather forecast
        self.weather_manager.update_forecast()

        # Update power status
        self.power_manager.update_power_status()

        # Update gas water heater temperature based on weather
        self.heater_controller.update_heater_based_on_weather()

        # Evaluate each room
        for room_id in self.rooms:
            self._evaluate_room(room_id)

    def _setup_day_night_schedule(self) -> None:
        """Set up day/night temperature schedule changes."""
        day_start_time = self.config.get("day_start_time", "07:00:00")
        night_start_time = self.config.get("night_start_time", "22:00:00")

        # Schedule day start
        self.run_daily(self._on_day_period_start, day_start_time)

        # Schedule night start
        self.run_daily(self._on_night_period_start, night_start_time)

        # Set initial mode based on current time
        now = self.datetime()
        day_start = self.parse_time(day_start_time)
        night_start = self.parse_time(night_start_time)

        day_start_datetime = now.replace(
            hour=day_start.hour, minute=day_start.minute, second=day_start.second
        )
        night_start_datetime = now.replace(
            hour=night_start.hour, minute=night_start.minute, second=night_start.second
        )

        if day_start_datetime <= now < night_start_datetime:
            self.schedule_manager.set_period("day")
            self.log("Initial period set to DAY based on current time", level="INFO")
        else:
            self.schedule_manager.set_period("night")
            self.log("Initial period set to NIGHT based on current time", level="INFO")

    def _on_day_period_start(self, kwargs: Dict[str, Any]) -> None:
        """Handle transition to day period."""
        self.log("Switching to DAY temperature settings", level="INFO")
        self.schedule_manager.set_period("day")

        # Re-evaluate all rooms with the new target temperatures
        for room_id in self.rooms:
            self._evaluate_room(room_id)

    def _on_night_period_start(self, kwargs: Dict[str, Any]) -> None:
        """Handle transition to night period."""
        self.log("Switching to NIGHT temperature settings", level="INFO")
        self.schedule_manager.set_period("night")

        # Re-evaluate all rooms with the new target temperatures
        for room_id in self.rooms:
            self._evaluate_room(room_id)

    def _on_temperature_change(self, entity: str, attribute: str, old: str, 
                              new: str, kwargs: Dict[str, Any]) -> None:
        """Handle temperature sensor changes."""
        room_id = kwargs.get("room_id")
        if not room_id:
            self.log(f"Temperature change detected but no room_id provided: {entity}", level="WARNING")
            return

        self.log(f"Temperature change in {room_id}: {old} -> {new}", level="DEBUG")
        self._evaluate_room(room_id)

    def _on_window_change(self, entity: str, attribute: str, old: str, 
                         new: str, kwargs: Dict[str, Any]) -> None:
        """Handle window state changes."""
        room_id = kwargs.get("room_id")
        if not room_id:
            self.log(f"Window state change detected but no room_id provided: {entity}", level="WARNING")
            return

        window_state = "open" if new == "on" else "closed"
        self.log(f"Window in {room_id} is now {window_state}", level="INFO")
        self._evaluate_room(room_id)

    def _on_presence_change(self, entity: str, attribute: str, old: str, 
                           new: str, kwargs: Dict[str, Any]) -> None:
        """Handle presence sensor changes for a specific room."""
        room_id = kwargs.get("room_id")
        if not room_id:
            self.log(f"Presence change detected but no room_id provided: {entity}", level="WARNING")
            return

        presence = "occupied" if new == "on" else "unoccupied"
        self.log(f"Room {room_id} is now {presence}", level="INFO")

        # Update presence status in manager
        self.presence_manager.update_room_presence(room_id, new == "on")
        self._evaluate_room(room_id)

    def _on_global_presence_change(self, entity: str, attribute: str, old: str, 
                                  new: str, kwargs: Dict[str, Any]) -> None:
        """Handle global presence sensor changes (home/away)."""
        presence = "present" if new == "on" else "away"
        self.log(f"Global presence changed to: {presence}", level="INFO")

        # Update global presence status
        self.presence_manager.update_global_presence(new == "on")

        # Re-evaluate all rooms
        for room_id in self.rooms:
            self._evaluate_room(room_id)

    def _on_solar_excess_change(self, entity: str, attribute: str, old: str, 
                               new: str, kwargs: Dict[str, Any]) -> None:
        """Handle changes in solar excess production.

        Note: Negative values indicate exported power (excess).
        """
        try:
            new_value = float(new)
            self.log(f"Solar excess changed: {old} -> {new} W", level="DEBUG")
            self.power_manager.update_solar_excess(new_value)

            # If significant change, re-evaluate all rooms
            old_value = float(old) if old else 0
            if abs(new_value - old_value) > self.config.get("solar_threshold_change", 300):  # 300W default
                self.log(f"Significant solar production change detected ({old} -> {new}), re-evaluating", level="INFO")
                for room_id in self.rooms:
                    self._evaluate_room(room_id)
        except (ValueError, TypeError):
            self.log(f"Invalid solar excess value: {new}", level="WARNING")


    def _on_battery_soc_change(self, entity: str, attribute: str, old: str,
                     new: str, kwargs: Dict[str, Any]) -> None:
        """Handle changes in battery state of charge."""
        try:
            new_value = float(new)
            self.log(f"Battery state of charge changed: {old} -> {new}%", level="DEBUG")
            self.power_manager.update_battery_soc(new_value)
        except (ValueError, TypeError):
            self.log(f"Invalid battery state of charge value: {new}", level="WARNING")

    def _on_heater_temp_change(self, entity: str, attribute: str, old: str, 
                              new: str, kwargs: Dict[str, Any]) -> None:
        """Handle changes in central heater temperature."""
        try:
            new_value = float(new)
            self.log(f"Central heater temperature changed: {old} -> {new}C", level="DEBUG")
            self.power_manager.update_heater_temperature(new_value)
        except (ValueError, TypeError):
            self.log(f"Invalid heater temperature value: {new}", level="WARNING")

    def _evaluate_room(self, room_id: str) -> None:
        """Evaluate a room's current state and take appropriate actions."""
        self.log(f"Evaluating room: {room_id}", level="DEBUG")

        # Get current room state
        current_temp = self.entity_manager.get_current_temperature(room_id)
        if current_temp is None:
            self.log(f"Cannot evaluate {room_id}: temperature sensor unavailable", level="WARNING")
            return

        # Get target temperature based on schedule and presence
        target_temp = self.schedule_manager.get_target_temperature(room_id)

        # Check if window is open
        window_open = self.entity_manager.is_window_open(room_id)

        # Check if room is occupied
        room_occupied = self.presence_manager.is_room_occupied(room_id)

        # Check if anyone is home
        home_occupied = self.presence_manager.is_home_occupied()

        # Get available power from renewables
        renewable_power = self.power_manager.get_available_renewable_power()

        # Get heating decision
        decision = self.decision_engine.get_climate_decision(
            room_id=room_id,
            current_temp=current_temp,
            target_temp=target_temp,
            window_open=window_open,
            room_occupied=room_occupied,
            home_occupied=home_occupied,
            renewable_power=renewable_power,
            weather_forecast=self.weather_manager.get_forecast_data()
        )

        # Apply the decision
        self._apply_climate_decision(room_id, decision)

    def _apply_climate_decision(self, room_id: str, decision: Dict[str, Any]) -> None:
        """Apply the climate control decision to the actual devices."""
        action = decision.get("action")
        reason = decision.get("reason")
        ac_mode = decision.get("ac_mode")
        ac_temp = decision.get("ac_temp")
        floor_heating = decision.get("floor_heating")

        self.log(f"Room {room_id} - Decision: {action} (Reason: {reason})", level="INFO")

        # Apply AC settings if needed
        if action in ["heat_with_ac", "cool_with_ac"]:
            ac_entity = self.entity_manager.get_ac_entity(room_id)
            if ac_entity:
                self.log(f"Setting AC for {room_id} to {ac_mode} mode at {ac_temp}C", level="INFO")
                self._set_ac(ac_entity, ac_mode, ac_temp)
            else:
                self.log(f"Cannot control AC for {room_id}: no entity found", level="WARNING")

        # Apply floor heating settings if needed
        floor_entity = self.entity_manager.get_floor_heating_entity(room_id)
        if floor_entity:
            new_state = "on" if floor_heating else "off"
            current_state = self.get_state(floor_entity)
            if current_state != new_state:
                self.log(f"Setting floor heating for {room_id} to {new_state}", level="INFO")
                self.call_service(f"switch/turn_{new_state}", entity_id=floor_entity)
        else:
            self.log(f"Cannot control floor heating for {room_id}: no entity found", level="WARNING")

    def _set_ac(self, entity_id: str, mode: str, temperature: float) -> None:
        """Set the AC to the specified mode and temperature."""
        try:
            # Get current state to avoid unnecessary calls
            current_state = self.get_state(entity_id, attribute="all")
            current_mode = current_state.get("attributes", {}).get("hvac_mode")
            current_temp = current_state.get("attributes", {}).get("temperature")

            # Check if we need to change anything
            if current_mode != mode or (temperature and current_temp != temperature):
                # Set climate entity
                service_data = {
                    "entity_id": entity_id,
                    "hvac_mode": mode
                }

                if temperature and mode not in ["off", "fan_only"]:
                    service_data["temperature"] = temperature

                self.call_service("climate/set_hvac_mode", **service_data)

                # If temperature needs to be set separately
                if temperature and mode not in ["off", "fan_only"] and current_temp != temperature:
                    self.call_service("climate/set_temperature", 
                                      entity_id=entity_id, 
                                      temperature=temperature)
        except Exception as e:
            self.log(f"Error setting AC state: {e}", level="ERROR")
