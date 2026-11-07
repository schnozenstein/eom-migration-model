# CBS Netherlands migration release — extracted source snapshot

- Retrieval timestamp: 2026-11-07T05:43:23Z
- Publisher: Statistics Netherlands (CBS)
- Release date: 30 October 2026
- Official release: https://www.cbs.nl/en-gb/news/2026/44/population-growth-slows-for-fourth-consecutive-year
- Related StatLine table: https://www.cbs.nl/en-gb/figures/detail/83474ENG
- OData service root inspected: https://opendata.cbs.nl/ODataApi/OData/83474ENG
- Extraction method: manually transcribed numeric tables from the official CBS HTML release. The OData service root/metadata was reachable, but the TypedDataSet endpoint could not be retrieved through the available web reader. This is not claimed as a direct API download.
- Observation window: cumulative January–September for each listed year; 2026 provisional.
- Geography: Netherlands national destination.
- Units: thousand persons, rounded to one decimal place.

## Immigration and emigration, first three quarters

| Year | Net migration | Immigration | Emigration (signed source value) |
|---:|---:|---:|---:|
| 2019 | 87.5 | 210.5 | -122.9 |
| 2020 | 52.7 | 165.9 | -113.2 |
| 2021 | 80.1 | 188.4 | -108.3 |
| 2022 | 188.0 | 322.3 | -134.3 |
| 2023 | 109.4 | 260.9 | -151.5 |
| 2024 | 87.3 | 245.7 | -158.4 |
| 2025 | 81.6 | 244.5 | -162.9 |
| 2026* | 66.3 | 226.1 | -159.8 |

*2026 provisional. Source values are rounded; differences of 0.1 thousand may occur when recomputing net values from the rounded immigration and emigration columns.

## Net migration by country of origin, first three quarters

| Origin | 2026* | 2025 | 2024 | 2023 |
|---|---:|---:|---:|---:|
| Syria | 11.9 | 19.8 | 17.0 | 13.1 |
| Ukraine | 9.8 | 9.6 | 10.5 | 12.0 |
| Türkiye | 5.8 | 8.3 | 7.7 | 8.6 |
| Romania | 3.3 | 2.4 | 3.2 | 3.2 |
| India | 3.3 | 2.7 | 3.3 | 6.6 |
| US | 2.8 | 2.1 | 1.3 | 2.1 |
| Eritrea | 2.5 | 1.8 | 1.3 | 1.0 |
| Suriname | 1.9 | 2.6 | 2.3 | 2.0 |
| Portugal | 1.8 | 1.4 | 1.7 | 1.9 |
| Spain | 1.8 | 1.4 | 1.3 | 2.0 |

*2026 provisional. The release states these are the ten countries with the highest net migration in the 2026 first-three-quarter period. The table is not a complete origin universe.

## Definition and comparability notes

The CBS StatLine population-dynamics table defines immigration as arrivals that result in a new municipal population-register entry; the stated criterion is an intended stay of at least four months in the forthcoming six months. Emigration includes administrative corrections; the register-removal criterion refers to at least eight months abroad in the following twelve months. These are registration-based measures and are not equivalent to visa grants, border crossings, or nationality-based counts.

The origin table is stored under the exact CBS release label “country of origin”. The release excerpt does not provide a sufficiently detailed cohort definition to relabel it as nationality or country of birth. The normalized panel therefore preserves the source label and flags the definition for follow-up.

Source page text was captured via the official page reader. The excerpt is a provenance snapshot, not a substitute for the original HTML/CSV or the full StatLine API response.
