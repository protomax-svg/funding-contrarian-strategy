# Regime study for the funding-contrarian strategy

State at close t scales the book on t+1. Buckets = trailing-365d percentile terciles. 7 bps/side, real funding.

## 1) Next-day return (annualised) by market state

| state                                     |   IS low |   IS mid |   IS high |   OOS low |   OOS mid |   OOS high | worst bucket IS -> OOS   |
|:------------------------------------------|---------:|---------:|----------:|----------:|----------:|-----------:|:-------------------------|
| BTC ATR% (market ATR)                     |   -0.031 |    0.344 |     1.36  |    -0.04  |     0.598 |      0.11  | low -> low               |
| universe median ATR%                      |    0.01  |    0.033 |     1.24  |     0.147 |     0.207 |      0.299 | low -> low               |
| market 30d realized vol                   |    0.004 |    0.422 |     0.84  |     0.169 |     0.2   |      0.274 | low -> low               |
| funding dispersion (XS std of 7d funding) |    0.102 |    0.367 |     0.845 |     0.419 |     0.073 |      0.091 | low -> mid               |
| funding level (XS mean of 7d funding)     |    0.224 |    0.304 |     0.636 |     0.326 |     0.241 |      0.012 | low -> high              |
| BTC trend (close / SMA200)                |    0.277 |    0.67  |    -0.068 |     0.429 |     0.192 |     -0.196 | high -> high             |
| market 30d return                         |    0.348 |   -0.155 |     0.872 |     0.307 |     0.293 |     -0.009 | mid -> high              |
| strategy own trailing 60d return          |   -0.113 |    0.236 |     0.929 |     0.058 |     0.515 |      0.132 | low -> low               |

A state is only useful if the worst bucket is the same in IS and OOS.

## 2) Switch off / halve in the IS-worst bucket

| filter                                                   |   IS |   OOS |   OOS ann |   maxDD |   time_on |
|:---------------------------------------------------------|-----:|------:|----------:|--------:|----------:|
| none (base)                                              | 1.31 |  0.93 |     0.198 |  -0.608 |      1    |
| BTC ATR% (market ATR): x0.0 when low                     | 1.49 |  1.07 |     0.2   |  -0.378 |      0.62 |
| BTC ATR% (market ATR): x0.5 when low                     | 1.43 |  1.03 |     0.199 |  -0.496 |      0.81 |
| universe median ATR%: x0.0 when low                      | 1.38 |  0.72 |     0.136 |  -0.492 |      0.63 |
| universe median ATR%: x0.5 when low                      | 1.38 |  0.86 |     0.167 |  -0.545 |      0.82 |
| market 30d realized vol: x0.0 when low                   | 1.42 |  0.7  |     0.127 |  -0.419 |      0.64 |
| market 30d realized vol: x0.5 when low                   | 1.39 |  0.86 |     0.163 |  -0.513 |      0.82 |
| funding dispersion (XS std of 7d funding): x0.0 when low | 1.3  |  0.11 |     0.02  |  -0.554 |      0.64 |
| funding dispersion (XS std of 7d funding): x0.5 when low | 1.35 |  0.58 |     0.109 |  -0.571 |      0.82 |
| funding level (XS mean of 7d funding): x0.0 when low     | 1.21 |  0.35 |     0.061 |  -0.514 |      0.65 |
| funding level (XS mean of 7d funding): x0.5 when low     | 1.31 |  0.71 |     0.129 |  -0.56  |      0.83 |
| BTC trend (close / SMA200): x0.0 when high               | 1.38 |  1.54 |     0.249 |  -0.516 |      0.81 |
| BTC trend (close / SMA200): x0.5 when high               | 1.36 |  1.27 |     0.223 |  -0.518 |      0.9  |
| market 30d return: x0.0 when mid                         | 1.54 |  0.28 |     0.052 |  -0.406 |      0.68 |
| market 30d return: x0.5 when mid                         | 1.46 |  0.65 |     0.125 |  -0.513 |      0.84 |
| strategy own trailing 60d return: x0.0 when low          | 1.47 |  1.16 |     0.185 |  -0.425 |      0.75 |
| strategy own trailing 60d return: x0.5 when low          | 1.42 |  1.1  |     0.191 |  -0.511 |      0.88 |

## 3) ATR filters

| ATR rule                               |    IS |   OOS |   OOS ann |   maxDD |
|:---------------------------------------|------:|------:|----------:|--------:|
| off when BTC ATR pct > 0.5             | -0.02 |  0.16 |     0.02  |  -0.546 |
| off when BTC ATR pct < 0.5             |  1.43 |  0.93 |     0.16  |  -0.291 |
| off when BTC ATR pct > 0.7             |  0.59 |  0.87 |     0.136 |  -0.474 |
| off when BTC ATR pct < 0.3             |  1.44 |  0.94 |     0.179 |  -0.324 |
| off when BTC ATR pct > 0.9             |  0.74 |  1.22 |     0.236 |  -0.625 |
| off when BTC ATR pct < 0.1             |  1.28 |  0.98 |     0.197 |  -0.564 |
| per-coin size ∝ 1/ATR (risk parity)    |  1.37 |  0.99 |     0.2   |  -0.529 |
| exclude top-20% ATR coins (both sides) |  1.18 |  0.98 |     0.212 |  -0.52  |

## 4) Volatility targeting on the strategy

| vol target                    |   IS |   OOS |   OOS ann |   maxDD |   avg lev |
|:------------------------------|-----:|------:|----------:|--------:|----------:|
| 15% ann, lookback 30d, max 2x | 1.07 |  1.26 |     0.211 |  -0.382 |      0.81 |
| 15% ann, lookback 60d, max 2x | 1.05 |  1.17 |     0.187 |  -0.369 |      0.75 |
| 20% ann, lookback 30d, max 2x | 1.08 |  1.26 |     0.282 |  -0.479 |      1.06 |
| 20% ann, lookback 60d, max 2x | 1.05 |  1.17 |     0.249 |  -0.468 |      0.99 |
| 30% ann, lookback 30d, max 2x | 1.09 |  1.18 |     0.372 |  -0.648 |      1.47 |
| 30% ann, lookback 60d, max 2x | 1.03 |  1.12 |     0.346 |  -0.629 |      1.42 |

## 5) Walk-forward choice among filters

| walk-forward filter choice                     |   OOS |   base OOS same span |   OOS ann |   maxDD |
|:-----------------------------------------------|------:|---------------------:|----------:|--------:|
| every 90d, best of 25 filters on trailing 365d |  1.07 |                 0.93 |     0.164 |  -0.471 |

Picks: 2021-07-19: funding dispersion (XS std of 7d funding) off mid; 2021-10-17: BTC ATR% (market ATR) off low; 2022-01-15: strategy own trailing 60d return off low; 2022-04-15: strategy own trailing 60d return off low; 2022-07-14: strategy own trailing 60d return off low; 2022-10-12: strategy own trailing 60d return off low; 2023-01-10: BTC trend (close / SMA200) off mid; 2023-04-10: BTC ATR% (market ATR) off low; 2023-07-09: strategy own trailing 60d return off mid; 2023-10-07: strategy own trailing 60d return off mid; 2024-01-05: market 30d return off high; 2024-04-04: BTC trend (close / SMA200) off high; 2024-07-03: BTC trend (close / SMA200) off high; 2024-10-01: BTC trend (close / SMA200) off high; 2024-12-30: BTC trend (close / SMA200) off high; 2025-03-30: strategy own trailing 60d return off high; 2025-06-28: strategy own trailing 60d return off high; 2025-09-26: strategy own trailing 60d return off high; 2025-12-25: market 30d realized vol off mid; 2026-03-25: BTC trend (close / SMA200) off mid; 2026-06-23: market 30d realized vol off mid

## 6) Combinations (each piece was consistent IS and OOS in section 1; cut points not tuned)

| combo                                         |   IS |   OOS |   OOS@15bps |   OOS total % |   maxDD |   OOS maxDD |   avg exposure |
|:----------------------------------------------|-----:|------:|------------:|--------------:|--------:|------------:|---------------:|
| base                                          | 1.31 |  0.93 |        0.51 |          59.6 |  -0.608 |      -0.267 |           1    |
| ATR-low off                                   | 1.4  |  1.07 |        0.69 |          62.7 |  -0.378 |      -0.137 |           0.54 |
| ATR-low off + trend-high off                  | 1.46 |  1.68 |        1.24 |          80   |  -0.308 |      -0.078 |           0.39 |
| ATR-low off + vol target 15%                  | 1.23 |  1.46 |        0.98 |          66.1 |  -0.223 |      -0.084 |           0.38 |
| ATR-low off + trend-high off + vol target 15% | 1.22 |  1.73 |        1.24 |          70.5 |  -0.2   |      -0.071 |           0.29 |
