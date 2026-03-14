# Watercryst

Watercryst is a Home Assistant custom integration for WATERCryst myBIOCAT systems.

It keeps API usage intentionally low by polling only the supported endpoints:

- `GET /state`
- `GET /statistics/daily/direct`
- `GET /absence/enable`
- `GET /absence/disable`
- `GET /watersupply/open`
- `GET /watersupply/close`

There is no webhook server, no callback endpoint, no Cloudflare tunnel, and no fast measurement polling.

## What it does

The integration lets you:

- enable or disable absence mode
- open or close the water supply
- monitor online state
- expose leak detection status
- store and surface daily/direct water consumption statistics
- bridge supported entities into Apple Home with Home Assistant HomeKit Bridge

## Supported entities

### Switches

- `switch.watercryst_absence_mode`
- `switch.watercryst_water_supply`

### Binary sensors

- `binary_sensor.watercryst_online`
- `binary_sensor.watercryst_leak_detected`

### Sensors

- `sensor.watercryst_mode`
- `sensor.watercryst_current_event`
- `sensor.watercryst_consumption_latest_l`
- `sensor.watercryst_consumption_latest_date`
- `sensor.watercryst_consumption_yesterday_l`

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository of type `Integration`.
3. Install `Watercryst`.
4. Restart Home Assistant.

### Manual installation

1. Copy `custom_components/watercryst` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

Configuration is done entirely through the Home Assistant UI:

1. Go to `Settings` -> `Devices & services`.
2. Select `Add integration`.
3. Search for `Watercryst`.
4. Enter your WATERCryst API key.
5. Optionally set a display name and a state polling interval.

The default state polling interval is 300 seconds. Statistics are fetched once at startup and then refreshed daily.

## Apple Home with HomeKit Bridge

This integration is designed to export cleanly through Home Assistant HomeKit Bridge:

- `Absence Mode` is exposed as a switch
- `Water Supply` is exposed as a switch
- `Leak Detected` is exposed as a moisture binary sensor
- `Online` is exposed as a connectivity binary sensor

After you expose the Watercryst entities in HomeKit Bridge, they can be used in Apple Home scenes and automations.

## Example Apple Home automations

### Last person leaves home

Use an Apple Home automation such as:

- Trigger: `When the last person leaves home`
- Action: turn on `Watercryst Absence Mode`

### Leak sensor detects water

Use an Apple Home automation such as:

- Trigger: a HomeKit leak sensor detects water
- Action: turn off `Watercryst Water Supply`

## Design notes

- State is refreshed on startup and then on a configurable interval.
- Statistics are refreshed on startup and then once per day.
- Successful switch actions trigger an immediate state refresh.
- HTTP 429 responses are handled gracefully without aggressive retries.
- The integration keeps entity naming simple and HomeKit Bridge friendly.
