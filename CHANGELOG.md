# Changelog

## 1.2.2 - Weather-Based Season Detection

- Enhanced eco mode to use actual outdoor temperature and weather forecast to determine heating/cooling seasons
- Fixed issue where system would heat during summer when room temperature was below eco cooling threshold
- Added more detailed logging of weather-based decision making
- Added cooling_threshold configuration parameter

## 1.2.1 - Eco Mode & Summer Cooling Fix

- Fixed eco mode logic to prevent heating during summer when eco temp is higher than current temp
- Improved season detection for better climate control decisions
- Added more descriptive logging for climate decisions

## 1.2.0 - Window Detection Improvements & Solar Export Fix

- Added option to disable window detection for rooms
- Fixed solar excess handling to work with negative values (exported power)
- Improved system stability

## 1.1.0 - Gas Water Heater Support

- Added support for on-demand gas water heaters
- Dynamic water temperature adjustment based on outdoor conditions
- Automatic optimization of heating efficiency

## 1.0.0 - Initial Release

- Complete room-by-room climate control system
- Integration with renewable energy sources (solar/battery)
- Support for air conditioners and in-floor heating
- Presence-based control and scheduling
- Weather forecast integration
- Window state monitoring
- Day/night scheduling
