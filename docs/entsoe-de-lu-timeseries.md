# ENTSO-E day-ahead prices for DE-LU: response structure

Findings from analysing the raw A44 response for the bidding zone DE-LU
(`10Y1001A1001A82H`) on 2026-10-03 and 2026-10-04. They are the basis for the
parsing rules introduced in 0.4.18.

## Request

| Parameter | Value |
|---|---|
| `documentType` | `A44` |
| `contract_MarketAgreement.type` | `A01` |
| `in_Domain` / `out_Domain` | `10Y1001A1001A82H` |
| Period | local midnight today + 2 days |

## Two series per delivery day

ENTSO-E returns **two `TimeSeries` per delivery day**. A response for today
and tomorrow therefore contains four series. The two series of one day share
all metadata except the classification sequence:

| Field | Series A | Series B |
|---|---|---|
| `businessType` | A62 | A62 |
| `auction.type` | A01 | A01 |
| `currency_Unit.name` / `price_Measure_Unit.name` | EUR / MWH | EUR / MWH |
| `curveType` | A03 | A03 |
| `resolution` | PT15M | PT15M |
| `classificationSequence_AttributeInstanceComponent.position` | **1** | **2** |

`mRID` only numbers the series consecutively and is not a stable criterion.

### Which series is the day-ahead price

Series with **sequence 1** match the SDAC day-ahead auction shown on
Energy-Charts ("Day Ahead Auktion (DE-LU)"):

| Slot (UTC) | Local time | Sequence 1 | Sequence 2 | Energy-Charts day-ahead |
|---|---|---|---|---|
| 2026-10-03 21:00Z | 03.10. 23:00 | 204.80 | 194.74 | 204.80 |
| 2026-10-04 00:00Z | 04.10. 02:00 | 192.54 | 180.21 | 192.54 |

The origin of **sequence 2** is unidentified. On 2026-10-03 23:00 local time it
matched none of the series on Energy-Charts (IDA1 202.79, IDA2 210.40,
IDA3 210.60, ID1 176.00, ID3 188.96, intraday average 195.29, intraday low
137.17, intraday high 230.00, ID AEP 165.79). It is usually 5–20 EUR/MWh below
the day-ahead price and contains many round values.

Before 0.4.18 the integration concatenated both series, so every timestamp
appeared twice and the hourly average mixed both auctions.

## Omitted positions (curve type A03)

With `curveType` A03, ENTSO-E omits a position when its price equals the
previous one. Example for 2026-10-04: sequence 1 lacked 1 of 96 positions,
sequence 2 lacked 5. The missing positions must be filled with the previous
price, up to the end of the period (`timeInterval/end`).

## Parsing rules (since 0.4.18)

1. Process series in ascending classification sequence; a series without the
   field counts as sequence 1.
2. Expand A03 periods to the full slot count with forward fill.
3. Keep the first value per timestamp and resolution; drop later ones.

## Known limitation

`prices_today` and `prices_tomorrow` are cut at UTC midnight, not local
midnight. For CEST, `prices_tomorrow` therefore holds 88 instead of 96 quarter
hours, and between 00:00 and 02:00 local time `prices_today` holds only 8.
