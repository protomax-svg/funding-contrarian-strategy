# Daily-bar results

Costs 7.0 bps/side, real funding, point-in-time top-30 universe. IS 2020-2023, OOS 2024-01..2026-08.

## Benchmarks

| name                              |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:----------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| BTC buy&hold (perp, pays funding) |         0.71 |        0.428 |        0.78 |       0.531 |         0.58 |        0.274 |  -0.789 |           0.1 |       1    |      0     |      0.118 |    0.026 |
| EW top-30 buy&hold, daily rebal   |         0.61 |        0.515 |        0.97 |       0.888 |        -0.03 |       -0.021 |  -0.867 |           4.3 |       0.98 |      0.003 |      0.083 |    0.049 |

## #1 Z-score trend sentinel (EMA/stdev 65)

Thresholds were never disclosed, so the shown row is a neutral guess (bull 0.5, bear 0); grid is over top-30.

| name                             |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:---------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| z n=65 bull=0.5 bear=0.0 | BTC   |         1.03 |        0.409 |        1.22 |       0.547 |         0.69 |        0.219 |  -0.379 |           9.7 |       0.48 |      0.007 |      0.089 |    0.011 |
| z n=65 bull=0.5 bear=0.0 | top30 |         0.99 |        0.435 |        1.4  |       0.692 |         0.2  |        0.068 |  -0.509 |          12   |       0.36 |      0.008 |      0.081 |    0.022 |

Grid (36 variants): median IS Sharpe 1.34, median OOS Sharpe 0.1, share of variants with OOS>0: 0.89. IS-best `z n=40 bull=1.5 bear=0.0 | top30`: IS 1.64 -> OOS 0.27.

## #3 SMA50 + EMA7 + RSI(2) vs ADX(2)

| name                       |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:---------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| as posted (50/7/2) | BTC   |         1.1  |        0.322 |        1.1  |       0.36  |         1.14 |        0.266 |  -0.343 |          65.7 |       0.27 |      0.046 |      0.052 |    0.008 |
| as posted (50/7/2) | top30 |         0.69 |        0.173 |        0.96 |       0.256 |         0.24 |        0.054 |  -0.397 |          61.2 |       0.21 |      0.043 |      0.047 |    0.06  |

Grid (18 variants): median IS Sharpe 0.97, median OOS Sharpe 0.14, share of variants with OOS>0: 0.67. IS-best `sma=40 ema=7 n=3 | top30`: IS 1.03 -> OOS -0.01.

## #4 RSI(5) > 70 momentum

| name                      |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:--------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| RSI5>70 as posted | BTC   |         1.16 |        0.32  |        1.43 |       0.442 |         0.64 |        0.137 |  -0.267 |          40.8 |       0.22 |      0.029 |      0.05  |    0.012 |
| RSI5>70 as posted | top30 |         1.07 |        0.242 |        1.22 |       0.286 |         0.85 |        0.18  |  -0.278 |          41.3 |       0.16 |      0.029 |      0.035 |    0.018 |

Grid (16 variants): median IS Sharpe 1.21, median OOS Sharpe 0.72, share of variants with OOS>0: 1.0. IS-best `RSI8>75 | top30`: IS 1.65 -> OOS 1.02.

## #12 IBS + range-contraction dip buy (equity rule on crypto)

| name                         |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:-----------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| as posted (2.5, 0.3) | BTC   |         0.43 |        0.146 |        0.45 |       0.174 |         0.43 |        0.108 |  -0.409 |          25.8 |       0.17 |      0.018 |      0.008 |    0.068 |
| as posted (2.5, 0.3) | top30 |         0.75 |        0.273 |        0.89 |       0.356 |         0.52 |        0.154 |  -0.443 |          27.3 |       0.2  |      0.019 |     -0.007 |    0.002 |

Grid (12 variants): median IS Sharpe 0.77, median OOS Sharpe 0.43, share of variants with OOS>0: 0.83. IS-best `k=3.0 ibs<0.3 | top30`: IS 0.93 -> OOS 0.68.

## #16 MACD / EMA crossover trend

| name                            |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:--------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| MACD(12,26,9) long/flat | BTC   |         0.84 |        0.336 |        0.97 |       0.438 |         0.6  |        0.188 |  -0.577 |          25.6 |       0.5  |      0.018 |      0.069 |    0.021 |
| MACD(12,26,9) long/flat | top30 |         0.8  |        0.388 |        1.39 |       0.709 |        -0.15 |       -0.068 |  -0.722 |          27.5 |       0.52 |      0.019 |      0.06  |    0.043 |
| EMA5>EMA13 long/flat | BTC      |         0.89 |        0.362 |        0.92 |       0.418 |         0.87 |        0.281 |  -0.563 |          23.5 |       0.53 |      0.016 |      0.093 |    0.021 |
| EMA5>EMA13 long/flat | top30    |         0.95 |        0.436 |        1.51 |       0.764 |        -0.07 |       -0.028 |  -0.636 |          26.8 |       0.45 |      0.019 |      0.078 |    0.024 |
| EMA5/13 long/short | BTC        |         0.48 |        0.293 |        0.44 |       0.297 |         0.6  |        0.287 |  -0.594 |          47.2 |       1    |      0.033 |      0.067 |    0.086 |
| EMA5/13 long/short | top30      |         0.53 |        0.344 |        0.84 |       0.609 |        -0.07 |       -0.037 |  -0.624 |          53.8 |       0.98 |      0.038 |      0.073 |    0.075 |

Grid (19 variants): median IS Sharpe 1.43, median OOS Sharpe 0.01, share of variants with OOS>0: 0.53. IS-best `EMA8>13 | top30`: IS 1.61 -> OOS -0.03.

## #17 Cross-sectional momentum

Long-only rows are total return (compare to EW top-30 benchmark). L/S = long top quintile, short bottom quintile, dollar-neutral.

| name                                           |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:-----------------------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| best coin of last week, hold 1w (SSRN 3055498) |         1.04 |        1.232 |        1.44 |       1.897 |         0.31 |        0.293 |  -0.934 |          88.9 |       0.97 |      0.062 |      0.007 |    0.007 |
| top-2 by 7d return, daily rebal (post)         |         1.37 |        1.537 |        2.09 |       2.559 |         0.09 |        0.087 |  -0.926 |         227   |       0.97 |      0.159 |      0.012 |    0.002 |
| L/S lb=1 hold=1                                |        -0.51 |       -0.16  |       -0.3  |      -0.106 |        -0.95 |       -0.236 |  -0.853 |         535.4 |       0.97 |      0.375 |      0.009 |    0.944 |
| L/S lb=28 hold=7                               |         1.02 |        0.316 |        1.5  |       0.518 |         0.12 |        0.03  |  -0.288 |          39.7 |       0.97 |      0.028 |     -0.006 |    0.005 |

Grid (12 variants): median IS Sharpe 1.15, median OOS Sharpe 0.12, share of variants with OOS>0: 0.58. IS-best `L/S lb=28 hold=1`: IS 1.7 -> OOS 0.29.

## #7a Funding cash-and-carry (delta-neutral; returns per $ of short notional)

Basis moves and spot-borrow ignored; capital needed is ~1.3-2x notional, so real return on capital is lower.

| name                         |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:-----------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| carry top5 f3>0bps/d weekly  |         3.6  |        0.079 |        5.77 |       0.144 |        -0.96 |       -0.015 |  -0.106 |          65.3 |       0.91 |      0.091 |     -0.168 |    0.004 |
| carry top10 f3>0bps/d weekly |         4.78 |        0.095 |        6.91 |       0.158 |         0.27 |        0.003 |  -0.073 |          50.5 |       0.97 |      0.071 |     -0.163 |    0.001 |
| carry top5 f3>1bps/d weekly  |         3.45 |        0.076 |        5.65 |       0.142 |        -1.13 |       -0.018 |  -0.112 |          66.9 |       0.91 |      0.094 |     -0.168 |    0.004 |
| carry top10 f3>1bps/d weekly |         4.34 |        0.089 |        6.71 |       0.155 |        -0.5  |       -0.007 |  -0.096 |          54.9 |       0.97 |      0.077 |     -0.163 |    0.001 |
| carry top5 f3>3bps/d weekly  |         4.67 |        0.095 |        6.03 |       0.148 |         1.78 |        0.019 |  -0.038 |          45.4 |       0.58 |      0.064 |     -0.156 |    0.001 |
| carry top10 f3>3bps/d weekly |         5.04 |        0.098 |        6.57 |       0.153 |         1.8  |        0.019 |  -0.035 |          41.6 |       0.63 |      0.058 |     -0.154 |    0.001 |
| carry BTC always (no costs)  |        10.67 |        0.118 |       11.08 |       0.15  |        14.98 |        0.07  |  -0.015 |           0   |       1    |      0     |     -0.118 |    0     |

## #7b Funding as a contrarian signal

| name                                       |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:-------------------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| BTC: long if funding z<-1.0, short if >1.0 |         0.28 |        0.09  |        0.43 |       0.149 |         0.02 |        0.006 |  -0.468 |          39.1 |       0.26 |      0.027 |     -0.039 |    0.263 |
| BTC: long if funding z<-2.0, short if >2.0 |        -0.46 |       -0.066 |        0.19 |       0.028 |        -1.44 |       -0.187 |  -0.417 |          10.5 |       0.05 |      0.007 |     -0.016 |    0.924 |
| XS contrarian funding lb=1                 |         0.58 |        0.205 |        1.18 |       0.49  |        -0.86 |       -0.199 |  -0.742 |         305   |       0.9  |      0.213 |     -0.158 |    0.085 |
| XS contrarian funding lb=1 weekly          |         0.69 |        0.238 |        0.84 |       0.345 |         0.39 |        0.087 |  -0.601 |          59.5 |       0.9  |      0.042 |     -0.12  |    0.061 |
| XS contrarian funding lb=3                 |         1.19 |        0.341 |        1.71 |       0.556 |         0.16 |        0.036 |  -0.463 |         169.9 |       0.95 |      0.119 |     -0.154 |    0.012 |
| XS contrarian funding lb=3 weekly          |         0.7  |        0.201 |        0.81 |       0.27  |         0.48 |        0.102 |  -0.589 |          54   |       0.94 |      0.038 |     -0.127 |    0.059 |
| XS contrarian funding lb=7                 |         1.19 |        0.33  |        1.35 |       0.423 |         0.93 |        0.198 |  -0.608 |          99.5 |       0.96 |      0.07  |     -0.15  |    0.009 |
| XS contrarian funding lb=7 weekly          |         1.03 |        0.28  |        1.11 |       0.343 |         0.91 |        0.19  |  -0.534 |          47   |       0.96 |      0.033 |     -0.128 |    0.018 |
| XS contrarian funding lb=14                |         1.01 |        0.253 |        1.11 |       0.311 |         0.84 |        0.17  |  -0.453 |          63.5 |       0.97 |      0.044 |     -0.142 |    0.012 |
| XS contrarian funding lb=14 weekly         |         1.06 |        0.27  |        1.41 |       0.4   |         0.42 |        0.086 |  -0.39  |          32.9 |       0.96 |      0.023 |     -0.123 |    0.013 |
| XS contrarian funding lb=30                |         0.72 |        0.176 |        1.04 |       0.283 |         0.12 |        0.025 |  -0.465 |          39.3 |       0.97 |      0.028 |     -0.132 |    0.057 |
| XS contrarian funding lb=30 weekly         |         0.36 |        0.085 |        0.66 |       0.173 |        -0.2  |       -0.04  |  -0.513 |          22.2 |       0.97 |      0.016 |     -0.115 |    0.232 |

Grid (10 variants): median IS Sharpe 1.11, median OOS Sharpe 0.41, share of variants with OOS>0: 0.8. IS-best `XS contrarian funding lb=3`: IS 1.71 -> OOS 0.16.

## #14 Order-flow proxy: taker-buy share (daily, cross-sectional)

True order-book imbalance needs L2 history (not free). This uses the taker-buy share inside each kline.

| name                            |   all_sharpe |   all_annret |   IS_sharpe |   IS_annret |   OOS_sharpe |   OOS_annret |   maxdd |   turn_per_yr |   exposure |   cost_ann |   fund_ann |   p_boot |
|:--------------------------------|-------------:|-------------:|------------:|------------:|-------------:|-------------:|--------:|--------------:|-----------:|-----------:|-----------:|---------:|
| XS taker imbalance lb=1 follow  |        -0.15 |       -0.039 |        0.69 |       0.197 |        -1.89 |       -0.373 |  -0.865 |         451.9 |       0.97 |      0.316 |     -0.034 |    0.634 |
| XS taker imbalance lb=1 fade    |        -2.46 |       -0.642 |       -3.02 |      -0.907 |        -1.39 |       -0.266 |  -0.988 |         449.5 |       0.97 |      0.315 |      0.039 |    1     |
| XS taker imbalance lb=3 follow  |         0.99 |        0.259 |        1.79 |       0.53  |        -0.63 |       -0.127 |  -0.57  |         227.1 |       0.97 |      0.159 |     -0.035 |    0.012 |
| XS taker imbalance lb=3 fade    |        -2.25 |       -0.622 |       -2.77 |      -0.879 |        -1.26 |       -0.257 |  -0.987 |         227.5 |       0.97 |      0.159 |      0.041 |    1     |
| XS taker imbalance lb=7 follow  |         1.49 |        0.383 |        2.13 |       0.616 |         0.27 |        0.054 |  -0.284 |         131.8 |       0.97 |      0.092 |     -0.035 |    0.001 |
| XS taker imbalance lb=7 fade    |        -2.24 |       -0.59  |       -2.75 |      -0.824 |        -1.3  |       -0.258 |  -0.984 |         130.1 |       0.97 |      0.091 |      0.04  |    1     |
| XS taker imbalance lb=14 follow |         1.67 |        0.416 |        2.34 |       0.653 |         0.4  |        0.08  |  -0.248 |          82.4 |       0.97 |      0.058 |     -0.025 |    0     |
| XS taker imbalance lb=14 fade   |        -1.99 |       -0.503 |       -2.44 |      -0.689 |        -1.19 |       -0.24  |  -0.971 |          81.7 |       0.97 |      0.057 |      0.03  |    1     |

Grid (8 variants): median IS Sharpe -0.88, median OOS Sharpe -1.23, share of variants with OOS>0: 0.25. IS-best `XS taker imbalance lb=14 follow`: IS 2.34 -> OOS 0.4.
