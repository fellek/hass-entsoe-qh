# Changelog

## 0.4.17 - 2025-10-14

- Swapped the custom helpers for assertpy assertions so your local checks use a familiar, well-supported library.

## 0.4.16 - 2025-10-13

- Restored the detailed ENTSO-E parsing checks alongside the live call so unit tests keep guarding data conversion.
- Relaxed the live verification to accept extra resolutions delivered by ENTSO-E while still confirming expected ones.

## 0.4.15 - 2025-10-12

- Restored the real ENTSO-E integration test so you can verify authentic price data flows with your token.
- Unified the API token environment variable in the docs and tests to make setup quicker.

## 0.4.14 - 2025-10-11

- Added live verification across all supported bidding zones so you can trust the integration fetches the right ENTSO-E periods.

## 0.4.13 - 2025-10-20

- Updated the README so it tells you the integration delivers whichever ENTSO-E resolution your area publishes, not just quarter-hour prices.

## 0.4.12 - 2025-10-19

- Clarified the README so it mirrors how the integration really works, covering the A44 download window, hourly averaging, and the sensor attributes you can use in dashboards.

## 0.4.11 - 2025-10-18

- Price sensors now show their exact interval (15 min, 30 min, 1 h) in both the name and entity ID, making it easy to pick the right one for automations and dashboards.

## 0.4.10 - 2025-10-17

- Fixes the options screen so you can update your ENTSO-E token and area without restarting the integration.

## 0.4.9 - 2025-10-16

- Price sensor names now spell out their resolution (15 min, 30 min, 1h) so you can instantly pick the right entity.
- Refreshed the Lovelace chart examples to match the updated entity IDs and highlight the available resolutions.

## 0.4.8 - 2025-10-15

- Added ready-to-use Lovelace chart examples so you can visualise the ENTSO-E prices without manual tweaking.

## 0.4.7 - 2025-10-14

- Price sensors now align with Home Assistant's measurement rules, removing the monetary device warnings while keeping long-term statistics intact.

## 0.4.6 - 2025-10-13

- Restored long-term statistics for the monetary sensors while keeping their history reliable.
- Trimmed the exposed price samples so Home Assistant no longer warns about oversized attributes.

## 0.4.5 - 2025-10-12

- Sensors now show up only when ENTSO-E actually provides that resolution, so you no longer see empty hourly or quarter-hour entities.
- Hourly averages are created automatically when the API offers only 15-minute data, so you still get a familiar hourly view.
- Documentation now explains that availability depends on your selected bidding zone.

## 0.4.4 - 2025-10-11

- Tests now run smoothly on both Windows and Linux without requiring a Home Assistant environment.
- Broader migration coverage reassures you that your existing setup stays intact during upgrades.
- More ENTSO-E data scenarios are validated so unexpected API quirks will not surprise you.

## 0.4.3 - 2025-10-10

- Removed Home Assistant warnings by aligning the monetary sensor behaviour with its device class.
- Kept the sensor attribute lists compact so the Home Assistant database stays responsive.
- Included the ENTSO-E contract_MarketAgreement type flag to stay aligned with the API rules.

## 0.4.2 - 2025-10-10

- Improved log messages so you can clearly see when ENTSO-E prices are downloaded and how many points arrived.
- Adjusted the release configuration to prevent HACS from failing to install the integration.
