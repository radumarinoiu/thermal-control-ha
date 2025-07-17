from typing import Dict, List, Any, Optional


class ScheduleManager:
    """Manages time-based schedules and temperature targets.

    This class handles day/night schedules and determining appropriate
    target temperatures for each room based on time and presence.
    """

    def __init__(self, controller):
        """Initialize the schedule manager.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config
        self.rooms = controller.rooms

        # Current period (day or night)
        self.current_period = "day"  # Default to day

        # Default target temperatures
        self.default_day_temp = float(self.config.get("default_target_temp_day", 21.0))
        self.default_night_temp = float(self.config.get("default_target_temp_night", 18.0))

    def set_period(self, period: str) -> None:
        """Set the current schedule period.

        Args:
            period: Either "day" or "night"
        """
        if period not in ["day", "night"]:
            self.controller.log(f"Invalid period: {period}, must be 'day' or 'night'", level="WARNING")
            return

        self.current_period = period
        self.controller.log(f"Schedule period set to: {period.upper()}", level="INFO")

    def get_target_temperature(self, room_id: str) -> float:
        """Get the target temperature for a room based on schedule and presence.

        Args:
            room_id: Room identifier

        Returns:
            Target temperature in Celsius
        """
        # Get room configuration
        room_config = self.rooms.get(room_id, {})

        # Check if presence affects the target temperature
        presence_required = room_config.get("presence_required", False)
        room_occupied = self.controller.presence_manager.is_room_occupied(room_id)
        home_occupied = self.controller.presence_manager.is_home_occupied()

        # If presence is required but room is unoccupied
        if presence_required and not room_occupied:
            # Use away temperature if available, otherwise fallback to night temp
            away_temp = room_config.get("away_temp")
            if away_temp is not None:
                return float(away_temp)
            else:
                return self._get_period_temp(room_id, "night")

        # Otherwise use the normal period temp
        return self._get_period_temp(room_id, self.current_period)

    def _get_period_temp(self, room_id: str, period: str) -> float:
        """Get the temperature for a specific period for a room.

        Args:
            room_id: Room identifier
            period: Either "day" or "night"

        Returns:
            Target temperature in Celsius
        """
        # Get from entity manager
        if period == "day":
            return self.controller.entity_manager.get_target_day_temp(room_id)
        else:
            return self.controller.entity_manager.get_target_night_temp(room_id)

    def get_schedule_info(self) -> Dict[str, Any]:
        """Get information about the current schedule.

        Returns:
            Dictionary with schedule information
        """
        day_start_time = self.config.get("day_start_time", "07:00:00")
        night_start_time = self.config.get("night_start_time", "22:00:00")

        return {
            "current_period": self.current_period,
            "day_start": day_start_time,
            "night_start": night_start_time
        }
