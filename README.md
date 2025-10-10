# ENTSO-E energy price integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant integration distributed through HACS that retrieves quarter-hour electricity prices from the ENTSO-E API.

**Current version:** 0.4.11

## Features

- Automatic download of the A44 document for the current and next day (CET/CEST) every 30 minutes.
- Automatically detects whether 15-minute, hourly, or both price series are available for your tariff.
- Support for PT15M resolution (96 points per day) and calculation of an hourly average when needed.
- Conversion of EUR/MWh prices to the selected currency (EUR or PLN) and energy unit (kWh or MWh).
- Optional VAT markup and custom exchange rate configuration.
- Sensors appear only for the resolutions supplied by ENTSO-E, so you see 15-minute, hourly, or both prices depending on your area.
- Sensor attributes provide compact snapshots of today's and tomorrow's prices (including the total available points) so Home Assistant stays free of oversized attribute warnings.

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
