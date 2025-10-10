# Changelog

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
