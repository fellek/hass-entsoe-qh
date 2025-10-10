# ENTSO-E energy price integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant integration distributed through HACS that retrieves quarter-hour electricity prices from the ENTSO-E API.

**Current version:** 0.4.3

## Features

- Automatic download of the A44 document for the current and next day (CET/CEST) every 30 minutes.
- Support for PT15M resolution (96 points per day) and calculation of an hourly average.
- Conversion of EUR/MWh prices to the selected currency (EUR or PLN) and energy unit (kWh or MWh).
- Optional VAT markup and custom exchange rate configuration.
- Two sensors available:
  - `15-minute energy price` – current price for the ongoing 15-minute slot.
  - `Hourly energy price` – average price for the current hour (four quarter-hour points).
- Sensor attributes provide compact price lists for today and tomorrow as `[timestamp, value, price_eur_mwh]`, ready for storage and charting.

## Installation

1. Add this repository to HACS as a custom repository.
2. Install the `ENTSO-E Energy Prices` integration.
3. In Home Assistant, go to `Settings → Devices & Services → Add Integration` and select `ENTSO-E Energy Prices`.

   ![ENTSO-E integration add window](images/add_integration_window.png)
4. Provide your ENTSO-E API token (required) and configure the remaining parameters (area, currency, exchange rate, VAT).

## Configuration

| Field | Description |
| ----- | ----------- |
| API token | Required security token obtained from the ENTSO-E portal. |
| Area (country and tariff) | Select the ENTSO-E bidding zone from the dropdown list. The default is `10YPL-AREA-----S` for Poland. |
| Price currency | EUR or PLN. |
| Energy unit | kWh or MWh. |
| Exchange rate versus EUR | Required when using a currency other than EUR. |
| VAT rate (%) | Optional VAT percentage added to the calculated price. |

## Price charts

## License

Released under the MIT License.
