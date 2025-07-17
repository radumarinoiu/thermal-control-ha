from typing import Dict, List, Any, Optional, Set


class PresenceManager:
    """Manages presence detection for rooms and the whole home.

    This class handles tracking occupancy states and providing presence
    information for climate control decisions.
    """

    def __init__(self, controller):
        """Initialize the presence manager.

        Args:
            controller: The parent SmartClimateController instance
        """
        self.controller = controller
        self.config = controller.config
        self.rooms = controller.rooms

        # Initialize presence states
        self.room_presence = {room_id: False for room_id in self.rooms}
        self.global_presence = False

        # Occupancy timeout values
        self.room_timeout = int(self.config.get("room_presence_timeout", 15)) * 60  # Convert to seconds
        self.home_timeout = int(self.config.get("home_presence_timeout", 30)) * 60  # Convert to seconds

        # Room timers (for timeout tracking)
        self.room_timers = {}
        self.home_timer = None

        # Get initial states
        self._update_initial_states()

    def _update_initial_states(self) -> None:
        """Update the initial presence states for all rooms and global presence."""
        # Check room presence sensors
        for room_id in self.rooms:
            entity_id = self.controller.entity_manager.get_presence_entity(room_id)
            if entity_id:
                state = self.controller.get_state(entity_id)
                self.room_presence[room_id] = (state == "on")

        # Check global presence sensors
        global_entities = self.controller.entity_manager.get_global_presence_entities()
        for entity_id in global_entities:
            if entity_id:
                state = self.controller.get_state(entity_id)
                if state == "on":
                    self.global_presence = True
                    break

    def update_room_presence(self, room_id: str, is_present: bool) -> None:
        """Update the presence state for a specific room.

        Args:
            room_id: Room identifier
            is_present: Whether the room is occupied
        """
        # Update room presence state
        self.room_presence[room_id] = is_present

        # If presence detected, update global presence too
        if is_present:
            self.update_global_presence(True)

            # Cancel any existing timeout timer for this room
            if room_id in self.room_timers and self.room_timers[room_id] is not None:
                self.controller.cancel_timer(self.room_timers[room_id])
                self.room_timers[room_id] = None
        else:
            # Start a timeout timer for this room
            if self.room_timeout > 0:
                # Cancel any existing timer first
                if room_id in self.room_timers and self.room_timers[room_id] is not None:
                    self.controller.cancel_timer(self.room_timers[room_id])

                # Start a new timer
                self.room_timers[room_id] = self.controller.run_in(
                    self._on_room_timeout, self.room_timeout, room_id=room_id
                )

    def update_global_presence(self, is_present: bool) -> None:
        """Update the global presence state for the home.

        Args:
            is_present: Whether anyone is home
        """
        # Update global presence state
        self.global_presence = is_present

        # If presence detected, cancel any timeout timer
        if is_present and self.home_timer is not None:
            self.controller.cancel_timer(self.home_timer)
            self.home_timer = None
        elif not is_present and self.home_timeout > 0:
            # Start a timeout timer for global presence
            # Cancel any existing timer first
            if self.home_timer is not None:
                self.controller.cancel_timer(self.home_timer)

            # Start a new timer
            self.home_timer = self.controller.run_in(
                self._on_home_timeout, self.home_timeout
            )

    def _on_room_timeout(self, kwargs: Dict[str, Any]) -> None:
        """Handle room presence timeout."""
        room_id = kwargs.get("room_id")
        if not room_id:
            return

        # Clear the timer reference
        self.room_timers[room_id] = None

        # Check if the presence sensor is still off
        entity_id = self.controller.entity_manager.get_presence_entity(room_id)
        if entity_id and self.controller.get_state(entity_id) == "off":
            self.room_presence[room_id] = False
            self.controller.log(f"Room {room_id} presence timeout: marking as unoccupied", level="INFO")

            # Trigger a room evaluation
            self.controller._evaluate_room(room_id)

    def _on_home_timeout(self, kwargs: Dict[str, Any]) -> None:
        """Handle global presence timeout."""
        # Clear the timer reference
        self.home_timer = None

        # Check if all global presence sensors are still off
        global_entities = self.controller.entity_manager.get_global_presence_entities()
        all_away = True

        for entity_id in global_entities:
            if entity_id and self.controller.get_state(entity_id) == "on":
                all_away = False
                break

        if all_away:
            self.global_presence = False
            self.controller.log("Home presence timeout: marking as unoccupied", level="INFO")

            # Trigger a re-evaluation of all rooms
            for room_id in self.rooms:
                self.controller._evaluate_room(room_id)

    def is_room_occupied(self, room_id: str) -> bool:
        """Check if a room is currently occupied.

        Args:
            room_id: Room identifier

        Returns:
            True if the room is occupied, False otherwise
        """
        return self.room_presence.get(room_id, False)

    def is_home_occupied(self) -> bool:
        """Check if anyone is home.

        Returns:
            True if anyone is home, False otherwise
        """
        return self.global_presence

    def get_occupied_rooms(self) -> List[str]:
        """Get a list of all currently occupied rooms.

        Returns:
            List of room IDs that are currently occupied
        """
        return [room_id for room_id, occupied in self.room_presence.items() if occupied]
