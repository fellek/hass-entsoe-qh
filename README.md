# ENTSO-E energy price integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant integration distributed through HACS that retrieves quarter-hour electricity prices from the ENTSO-E API.

**Current version:** 0.4.0

## Features

- Automatic download of the A44 document for the current and next day (CET/CEST) every 30 minutes.
- Support for PT15M resolution (96 points per day) and calculation of an hourly average.
- Conversion of EUR/MWh prices to the selected currency (EUR or PLN) and energy unit (kWh or MWh).
- Optional VAT markup and custom exchange rate configuration.
- Two sensors available:
  - `15-minute energy price` – current price for the ongoing 15-minute slot.
  - `Hourly energy price` – average price for the current hour (four quarter-hour points).
- Sensor attributes provide compact price series with per-slot identifiers, timestamps, durations and converted values that stay well below the Home Assistant recorder limits.

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

Both sensors publish a dedicated price series under the `series` attribute of their state. Each series contains:

- `current` – current converted price for the associated resolution (`quarter_hour` or `hour`).
- `prices_today` – list of dictionaries for the current day; each dictionary contains the fields listed in the `prices_fields` attribute:
  - `id` – unique identifier built from the resolution and the slot start epoch. Use this value to de-duplicate history entries.
  - `start` – ISO 8601 timestamp in UTC pointing to the beginning of the slot.
  - `duration_minutes` – slot length in minutes (`15` for quarter-hour, `60` for hourly averages).
  - `value` – converted price in the configured currency and energy unit.
  - `price_eur_mwh` – original ENTSO-E price for reference.
- `prices_tomorrow` – list of dictionaries formatted exactly like `prices_today`, containing the next-day forecast. These values are **not** intended for recorder history; they can be used in automations and dashboards without storing them in the database.

Home Assistant history automatically retains the `current` state value. Because every update keeps the `id` stable for a given slot, no duplicate entries are generated when the integration refreshes data from ENTSO-E. When iterating over `prices_today`, insert or update records in your own helpers or statistics tables by checking the `id` to avoid storing duplicates.

Price points are compact and do not exceed the Home Assistant recorder attribute size limit, ensuring that state attributes remain persistent even when the integration exposes the entire daily schedule.

### Polish translation / Tłumaczenie na język polski

- `current` – bieżąca cena przeliczona dla odpowiedniej rozdzielczości (`quarter_hour` lub `hour`).
- `prices_today` – lista słowników dla bieżącego dnia, każdy zawiera pola opisane w `prices_fields`:
  - `id` – unikalny identyfikator zbudowany z rozdzielczości i początku przedziału czasowego (UTC).
  - `start` – znacznik czasu ISO 8601 w UTC wskazujący początek przedziału.
  - `duration_minutes` – długość przedziału w minutach (`15` dla kwadransa, `60` dla godziny).
  - `value` – cena po przeliczeniu na konfigurację waluty i jednostki energii.
  - `price_eur_mwh` – pierwotna cena ENTSO-E jako odniesienie.
- `prices_tomorrow` – lista słowników w tym samym formacie co `prices_today`, zawiera prognozę na jutro. Nie musi być zapisywana w historii – można z niej korzystać w automatyzacjach i na dashboardach.

Historia Home Assistanta przechowuje wyłącznie stan `current`, a identyfikatory `id` zapewniają brak duplikatów przy ponownym pobieraniu danych z ENTSO-E.

## License

Released under the MIT License.
