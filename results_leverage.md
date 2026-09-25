# Leverage check (live rule: top-100 plain)

## Portfolio at 1x

|                 | value               |
|:----------------|:--------------------|
| worst day %     | -9.291089110799081  |
| worst day date  | 2025-09-08          |
| worst week %    | -11.316352613094416 |
| worst month %   | -11.030366146153769 |
| max drawdown %  | -26.966961711926963 |
| days below -5%  | 5                   |
| days below -10% | 0                   |

## Single positions (daily high/low while held, so intraday squeezes count)

|                                     | value                                          |
|:------------------------------------|:-----------------------------------------------|
| positions                           | 11115                                          |
| adverse move p50                    | 8%                                             |
| adverse move p90                    | 30%                                            |
| adverse move p99                    | 94%                                            |
| worst long (drop from entry)        | 100% LUNAUSDT 2022-04-18 00:00:00+00:00        |
| worst short (rise from entry)       | 1450% JELLYJELLYUSDT 2025-09-04 00:00:00+00:00 |
| positions with adverse move >= 20%  | 2145                                           |
| positions with adverse move >= 33%  | 950                                            |
| positions with adverse move >= 50%  | 419                                            |
| positions with adverse move >= 100% | 96                                             |

## Leverage replay 2020-2026 (daily bars; intraday moves inside a day are worse)

| leverage (gross)   |   max drawdown % |   worst day % |   worst month % |   2024-26 total % | ruined (-100%)   |   positions liquidated if isolated |
|:-------------------|-----------------:|--------------:|----------------:|------------------:|:-----------------|-----------------------------------:|
| 1x                 |            -27   |          -9.3 |           -11   |             123.3 | False            |                                  0 |
| 2x                 |            -49.1 |         -18.6 |           -21.3 |             281.1 | False            |                                426 |
| 3x                 |            -66.2 |         -27.9 |           -31.7 |             397.9 | False            |                                955 |
| 4x                 |            -79   |         -37.2 |           -41.5 |             396.8 | False            |                               1609 |
| 5x                 |            -87.9 |         -46.5 |           -50.6 |             276   | False            |                               2208 |
