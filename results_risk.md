# Risk Index (BTC 1h) as a filter for the funding-contrarian strategy

Index values from 2022-07-13; IS 2022-07-13..2023-12, OOS 2024-01..2026-08. 7 bps/side, real funding.

## Daily filter at the 00:05 UTC rebalance

| variant                                      |   Sharpe 22-26 |   IS 22-23 |   OOS 24-26 |   OOS total % |   maxDD |
|:---------------------------------------------|---------------:|-----------:|------------:|--------------:|--------:|
| base (no filter)                             |           0.51 |      -0.23 |        0.93 |          59.6 |  -0.388 |
| ATR filter (live now)                        |           0.75 |       0.07 |        1.07 |          62.7 |  -0.3   |
| pause when zone at close = 2 (p90)           |           0.56 |      -0.48 |        1.11 |          70.4 |  -0.333 |
| ATR + pause when zone at close = 2 (p90)     |           0.82 |      -0.39 |        1.32 |          75   |  -0.237 |
| pause when zone at close >= 1                |          -0.22 |      -0.89 |        0.12 |           1.4 |  -0.473 |
| ATR + pause when zone at close >= 1          |          -0    |      -0.33 |        0.13 |           2.1 |  -0.343 |
| pause when any zone-2 hour in last 24h       |           0.52 |      -0.62 |        1.12 |          65   |  -0.383 |
| ATR + pause when any zone-2 hour in last 24h |           0.76 |      -0.3  |        1.23 |          60.1 |  -0.276 |
| pause when zone at close = 0 (inverse)       |           0.47 |       0.01 |        0.78 |          28.4 |  -0.173 |
| ATR + pause when zone at close = 0 (inverse) |           0.74 |       0.17 |        1.04 |          38.2 |  -0.186 |

## Next-day strategy return by index zone at the close (annualised)

| period    |   zone 0 ann |   zone 1 ann |   zone 2 ann |   zone 0 days |   zone 1 days |   zone 2 days |
|:----------|-------------:|-------------:|-------------:|--------------:|--------------:|--------------:|
| IS 22-23  |       -0.217 |         0.11 |        0.161 |           310 |           151 |            76 |
| OOS 24-26 |        0.115 |         0.78 |       -0.398 |           644 |           227 |           103 |

## Overlap with the ATR filter

|                                                          |   value |
|:---------------------------------------------------------|--------:|
| corr(regime at close, BTC ATR percentile)                |   0.451 |
| share of zone>=1 days that the ATR filter already trades |   0.65  |

## Intraday exit on a spike (hourly P&L, daily Sharpe)

| variant                                        |   Sharpe 22-26 |   IS 22-23 |   OOS 24-26 |   OOS total % |   maxDD |   time in market |
|:-----------------------------------------------|---------------:|-----------:|------------:|--------------:|--------:|-----------------:|
| hourly base (daily book, hourly marks)         |           0.46 |      -0.31 |        0.92 |          55.6 |  -0.372 |             1    |
| hourly + ATR filter                            |           0.75 |       0.09 |        1.06 |          58.2 |  -0.286 |             0.56 |
| flat on zone-2 hour, back when zone <= 1       |           0.17 |      -1.01 |        0.8  |          43.2 |  -0.419 |             0.88 |
| ATR + flat on zone-2 hour, back when zone <= 1 |           0.48 |      -0.65 |        0.95 |          46.4 |  -0.269 |             0.47 |
| flat on zone-2 hour, back when zone <= 0       |           0.36 |      -0.92 |        1.05 |          56.3 |  -0.374 |             0.79 |
| ATR + flat on zone-2 hour, back when zone <= 0 |           0.56 |      -0.62 |        1.07 |          48   |  -0.247 |             0.41 |

## Fixed threshold (index > 0.65 / 0.70 / 0.75)

|                       |   value |
|:----------------------|--------:|
| share of hours > 0.6  |   0.167 |
| share of hours > 0.65 |   0.082 |
| share of hours > 0.7  |   0.034 |
| share of hours > 0.75 |   0.004 |
| share of hours > 0.8  |   0     |

### Daily filter

| variant                                |   Sharpe 22-26 |   IS 22-23 |   OOS 24-26 |   OOS total % |   maxDD |   IS next-day ann when > 0.65 |   IS days > 0.65 |   OOS next-day ann when > 0.65 |   OOS days > 0.65 |   IS next-day ann when > 0.7 |   IS days > 0.7 |   OOS next-day ann when > 0.7 |   OOS days > 0.7 |   IS next-day ann when > 0.75 |   IS days > 0.75 |   OOS next-day ann when > 0.75 |   OOS days > 0.75 |
|:---------------------------------------|---------------:|-----------:|------------:|--------------:|--------:|------------------------------:|-----------------:|-------------------------------:|------------------:|-----------------------------:|----------------:|------------------------------:|-----------------:|------------------------------:|-----------------:|-------------------------------:|------------------:|
| pause when index at close > 0.65       |           0.48 |      -0.37 |        0.95 |          55.8 |  -0.355 |                         0.143 |               32 |                          -0.07 |                96 |                      nan     |             nan |                       nan     |              nan |                       nan     |              nan |                        nan     |               nan |
| ATR + pause when index at close > 0.65 |           0.67 |      -0.38 |        1.12 |          59   |  -0.262 |                       nan     |              nan |                         nan    |               nan |                      nan     |             nan |                       nan     |              nan |                       nan     |              nan |                        nan     |               nan |
| pause when index at close > 0.7        |           0.42 |      -0.42 |        0.87 |          53.8 |  -0.385 |                       nan     |              nan |                         nan    |               nan |                        1.136 |              13 |                         0.091 |               42 |                       nan     |              nan |                        nan     |               nan |
| ATR + pause when index at close > 0.7  |           0.66 |      -0.19 |        1.01 |          56.5 |  -0.296 |                       nan     |              nan |                         nan    |               nan |                      nan     |             nan |                       nan     |              nan |                       nan     |              nan |                        nan     |               nan |
| pause when index at close > 0.75       |           0.49 |      -0.24 |        0.91 |          57.4 |  -0.388 |                       nan     |              nan |                         nan    |               nan |                      nan     |             nan |                       nan     |              nan |                         0.041 |                2 |                          0.263 |                 7 |
| ATR + pause when index at close > 0.75 |           0.72 |       0.05 |        1.03 |          58.9 |  -0.3   |                       nan     |              nan |                         nan    |               nan |                      nan     |             nan |                       nan     |              nan |                       nan     |              nan |                        nan     |               nan |

### Intraday: flat while above the threshold

| variant                                         |   Sharpe 22-26 |   IS 22-23 |   OOS 24-26 |   OOS total % |   maxDD |   time in market |
|:------------------------------------------------|---------------:|-----------:|------------:|--------------:|--------:|-----------------:|
| flat while index > 0.65 (back below 0.60)       |           0.19 |      -0.57 |        0.61 |          28.9 |  -0.359 |             0.88 |
| ATR + flat while index > 0.65 (back below 0.60) |           0.36 |      -0.43 |        0.71 |          30.4 |  -0.253 |             0.46 |
| flat while index > 0.7 (back below 0.65)        |           0.39 |      -0.25 |        0.74 |          39.7 |  -0.356 |             0.95 |
| ATR + flat while index > 0.7 (back below 0.65)  |           0.57 |      -0.21 |        0.9  |          44.4 |  -0.267 |             0.52 |
| flat while index > 0.75 (back below 0.70)       |           0.42 |      -0.36 |        0.88 |          52.2 |  -0.372 |             0.99 |
| ATR + flat while index > 0.75 (back below 0.70) |           0.72 |       0.06 |        1.03 |          56   |  -0.286 |             0.55 |
