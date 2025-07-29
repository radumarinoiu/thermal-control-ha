# Smart Climate Control for Home Assistant

This AppDaemon application provides an intelligent climate control system for Home Assistant that integrates various sensors and devices to optimize heating and cooling across multiple rooms.

## Features

- Room-by-room temperature control
- Integration with renewable energy sources (solar/battery)
- Smart decisions between AC and in-floor heating
- Presence-based control
- Day/night scheduling
- Weather forecast integration
- Window state monitoring
- Highly configurable via YAML

## Required Entities

The system works with the following entity types:

**Per Room:**
- Temperature sensors
- Humidity sensors
- Window sensors
- Air conditioner climate controls
- In-floor heating switches
- Lux sensors (per window)
- Presence sensors
- Target temperature settings (day/night)

**Global:**
- Central heater water temperature
- Solar power excess
- Battery capacity
- Outside temperature/humidity
- Weather forecast
- Home presence sensors

## Installation

### HACS Installation (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations > Three dots (top right) > Custom repositories
   - Add the URL of this repository
   - Category: AppDaemon
3. Click "Install" on the Smart Climate Control card
4. Add the configuration to your `apps.yaml` file (see example below)
5. Restart AppDaemon

### Manual Installation

1. Install AppDaemon for Home Assistant if you haven't already
2. Copy the `apps/smart_climate_control` directory to your AppDaemon `apps` directory
3. Copy the configuration from `apps/apps.yaml` to your AppDaemon `apps.yaml` file
4. Customize the configuration to match your entities and preferences
5. Restart AppDaemon

## Configuration

The system is configured through the `apps.yaml` file. All entity mappings, room settings, and control parameters can be customized. See the included configuration file for detailed examples.

### Entity Naming

By default, the system expects entities to follow this naming convention:
- `sensor.{room_id}_thermohygrometer_temperature`
- `sensor.{room_id}_thermohygrometer_humidity`
- `binary_sensor.{room_id}_window`
- `climate.{room_id}_ac`
- `switch.{room_id}_floor_heating`

These can be customized in the configuration.

## How It Works

The system continuously monitors room conditions and makes intelligent decisions about which heating/cooling method to use based on:

1. Current and target temperatures
2. Time of day (day/night schedule)
3. Room occupancy
4. Available renewable energy
5. Weather conditions and forecast
6. Window states (can be disabled per room if needed)

It will automatically choose between air conditioning and in-floor heating based on efficiency, available energy sources, and temperature requirements.

## Rooms

The system is pre-configured with the following rooms (easily customizable):
- Radu's Office (radu_s_office)
- Cristina's Office (cristina_s_office)
- Living Room (living_room)
- Kitchen (kitchen)
- Bedroom (bedroom)
- Hallway (hallway)

## Decision Logic

The climate decision engine considers multiple factors:

- For heating: It can use floor heating, AC heating, or both depending on:
  - Available renewable energy
  - Temperature difference to target
  - Weather forecast trends
  - The gas water heater temperature is automatically adjusted based on outdoor conditions

- For cooling: It uses AC cooling, potentially more aggressively when excess solar power is available

## Logging

The system logs decision processes and major state changes while keeping routine updates at DEBUG level to avoid cluttering logs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
