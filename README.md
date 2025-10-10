# ENTSO-E energy price integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant integration distributed through HACS that retrieves electricity prices from the ENTSO-E API in the finest resolution available for your bidding zone.

**Current version:** 0.4.13

## Features

- Automatic download of the A44 document for the current and next day (CET/CEST) every 30 minutes.
- Detects whether 15-minute and 30-minute market series are published for your bidding zone and always delivers an hourly view (from ENTSO-E data or an on-the-fly average).
- Converts the EUR/MWh prices returned by ENTSO-E to your preferred currency (EUR or PLN) and energy unit (kWh or MWh), with optional VAT and a custom exchange rate.
- Sensors appear only for the resolutions supplied by ENTSO-E, so you see 15-minute, 30-minute, or hourly prices depending on your area.
- Sensor attributes expose compact snapshots of today's and tomorrow's prices (with metadata and totals) so Home Assistant stays free of oversized attribute warnings.

## How it works

- The integration queries the ENTSO-E Transparency Platform REST API (`documentType=A44`) with your selected bidding zone used for both the `in_Domain` and `out_Domain` parameters. The request window spans from midnight of the current day in CET/CEST to the end of the following day, ensuring tomorrow's data is downloaded as soon as ENTSO-E publishes it.
- Every successful refresh produces a unified payload containing the measurement unit (for example `EUR/kWh`), the raw ENTSO-E price series grouped by resolution, and a timestamp marking when the update completed.
- When ENTSO-E omits hourly values, the integration calculates hourly averages from the available finer-grained points so dashboards and automations can always rely on an hourly sensor.
- Price lists for today and tomorrow are trimmed to the first 10 entries in the sensor attributes. The full number of available points is reported, allowing you to decide whether to fetch the rest through the API if needed.

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
| Exchange rate versus EUR | Required when using a currency other than EUR. Leave at `1.0` for EUR. |
| VAT rate (%) | Optional VAT percentage added to the calculated price. |

After completing the setup you can revisit `Settings → Devices & Services → ENTSO-E Energy Prices → Configure` to adjust any of the parameters above. The integration validates the token, bidding zone, and exchange-rate rules before applying your updates.

## Entities

The integration creates a dedicated sensor for each price resolution returned by ENTSO-E. The names now highlight the time span they represent so that it is easier to spot the right entity when building dashboards.

| Resolution | Entity name (English UI) | Default entity ID (English UI) |
| ---------- | ------------------------ | ------------------------------ |
| 15 minutes | ENTSO-E Energy Prices 15 min | `sensor.entso_e_energy_prices_15_min` |
| 30 minutes | ENTSO-E Energy Prices 30 min | `sensor.entso_e_energy_prices_30_min` |
| 1 hour     | ENTSO-E Energy Prices 1 h | `sensor.entso_e_energy_prices_1_h` |

> ℹ️ When Home Assistant runs in Polish, the device name becomes `ENTSO-E Ceny energii`, so the entity IDs start with `sensor.entso_e_ceny_energii_…`. Adjust the examples below to match the entity IDs shown in your instance.

## Price charts

You can visualise the ENTSO-E price sensors in Home Assistant dashboards by using Lovelace custom cards. Replace the entity ID with the hourly or 30-minute sensor if that better suits your tariff.

## Sensor attributes

Each sensor exposes a compact attribute payload that follows the same structure for all resolutions:

- `unit`: Set on the sensor state and matches the configured currency and energy unit (for example `PLN/kWh`).
- `updated_at`: ISO 8601 timestamp of the last successful download.
- `price_fields`: Ordered list of keys describing how to read the price arrays (`id`, `start`, `value`, `price_eur_mwh`).
- `prices_today` / `prices_tomorrow`: Contain the first 10 entries published by ENTSO-E for the given resolution, the total number of available points, and a flag indicating whether the list was truncated. Timestamps are normalised to UTC so they are easy to compare inside templates and automations.

Tomorrow's list stays empty until ENTSO-E releases the data for your bidding zone.

### Mini Graph Card

```yaml
type: custom:mini-graph-card
name: Energy prices (EUR/kWh)
entities:
  - entity: sensor.entso_e_energy_prices_15_min
    name: Price
hours_to_show: 48
points_per_hour: 4
group_by: interval
aggregate_func: last
line_width: 3
lower_bound: 0
show:
  fill: fade
  extrema: true
  average: true
  labels: true
color_thresholds:
  - value: 0.1
    color: "#2ecc71"
  - value: 0.2
    color: "#f1c40f"
  - value: 0.35
    color: "#e67e22"
  - value: 0.5
    color: "#e74c3c"
```

### ApexCharts Card

```yaml
type: custom:apexcharts-card
header:
  title: Energy prices (EUR/kWh)
  show: true
graph_span: 48h
now:
  show: true
  color: gray
yaxis:
  - min: 0.05
    decimals: 2
apex_config:
  stroke:
    width: 3
    curve: stepline
  fill:
    type: gradient
  dataLabels:
    enabled: false
  tooltip:
    "y":
      formatter: |
        EVAL: (val) => (val == null ? '' : `€${val.toFixed(3)}/kWh`)
  yaxis:
    labels:
      formatter: |
        EVAL: (val) => (val == null ? '' : `${val.toFixed(2)}`)
  annotations:
    yaxis:
      - "y": 0.1
        borderColor: "#2ecc71"
        label:
          text: 0.10 € cheap
      - "y": 0.2
        borderColor: "#f1c40f"
        label:
          text: 0.20 € typical
      - "y": 0.35
        borderColor: "#e67e22"
        label:
          text: 0.35 € expensive
      - "y": 0.5
        borderColor: "#e74c3c"
        label:
          text: 0.50 € very expensive
    regions:
      - "y": 0
        y2: 0.1
        fillColor: rgba(46,204,113,0.10)
      - "y": 0.1
        y2: 0.2
        fillColor: rgba(241,196,15,0.10)
      - "y": 0.2
        y2: 0.35
        fillColor: rgba(230,126,34,0.08)
      - "y": 0.35
        y2: 5.5
        fillColor: rgba(231,76,60,0.08)
series:
  - entity: sensor.entso_e_energy_prices_15_min
    name: Price
    type: line
    group_by:
      duration: 15min
      func: last
    show:
      extremas: true
```

## License

Released under the MIT License.
