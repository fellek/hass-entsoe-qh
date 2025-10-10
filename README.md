# ENTSO-E energy price integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant integration distributed through HACS that retrieves quarter-hour electricity prices from the ENTSO-E API.

**Current version:** 0.5.0

## Features

- Automatic download of the A44 document for the current and next day (CET/CEST) every 30 minutes.
- Support for PT15M resolution (96 points per day) and calculation of an hourly average.
- Conversion of EUR/MWh prices to the selected currency (EUR or PLN) and energy unit (kWh or MWh).
- Optional VAT markup and custom exchange rate configuration.
- Two sensors available:
  - `15-minute energy price` – current price for the ongoing 15-minute slot.
  - `Hourly energy price` – average price for the current hour (four quarter-hour points).
- Sensor attributes expose lightweight daily price arrays that remain comfortably below the Home Assistant recorder limits.

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

## Using the price series in Home Assistant

Each sensor keeps the entity state equal to the current converted price and publishes a concise attribute payload that contains:

- `unit_of_measurement` and `currency` – matching the integration configuration for quick reference.
- `start` – ISO 8601 timestamp of the midnight that corresponds to the `today` series (CET/CEST, including the offset).
- `step_minutes` – either `15`, `30` or `60` depending on the market resolution.
- `today` – list of floats for every slot of the current day (maximum 96 entries for PT15M).
- `today_min`, `today_max`, `today_avg` – rounded statistics for the values included in `today`.
- `tomorrow` – optional list of floats that appears only when the next-day schedule is available (also limited to 96 entries).
- `tomorrow_min`, `tomorrow_max`, `tomorrow_avg` – statistics published only when `tomorrow` exists.
- `updated_at` – ISO 8601 timestamp of the last successful refresh.
- `source`, `in_domain`, `out_domain` – metadata describing the origin and bidding zone of the data.

All lists are rounded to four decimal places and trimmed to guarantee that attribute size remains well below the 16 KB recorder limit. Dashboards (for example ApexCharts) can continue to reference `today` and `tomorrow` without additional processing.

### Polish translation / Tłumaczenie na język polski

- `current` – bieżąca cena przeliczona dla odpowiedniej rozdzielczości (`quarter_hour` lub `hour`).
- `today` – lista liczb zmiennoprzecinkowych opisujących ceny na dziś.
- `today_min`, `today_max`, `today_avg` – statystyki obliczone z listy `today`.
- `tomorrow` – lista liczb z prognozą na jutro, obecna tylko wtedy, gdy dane są dostępne.
- `tomorrow_min`, `tomorrow_max`, `tomorrow_avg` – statystyki pojawiają się wraz z listą `tomorrow`.
- `start` – północ dnia odpowiadającego liście `today` w czasie CET/CEST.
- `step_minutes` – długość pojedynczego przedziału w minutach (15, 30 lub 60).
- `updated_at` – znacznik czasu ostatniego udanego odświeżenia.
- `source`, `in_domain`, `out_domain` – metadane wskazujące źródło i strefę taryfową.

Historia Home Assistanta przechowuje wyłącznie stan `current`, a kompaktowe atrybuty nie przekraczają limitu rozmiaru rekordera.

## License

Released under the MIT License.
