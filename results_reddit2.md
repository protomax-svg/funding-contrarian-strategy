# #20 tiered drawdown buying vs DCA, #21 day-of-week

## #20 (same $10/week to both; wealth / money paid in)

| sym     |   years |   starts |   DCA_median |   tiered_median |   tiered beats DCA |
|:--------|--------:|---------:|-------------:|----------------:|-------------------:|
| BTCUSDT |       1 |       68 |         1.26 |            1.06 |               0.38 |
| BTCUSDT |       3 |       44 |         1.82 |            1.82 |               0.5  |
| BTCUSDT |       5 |       20 |         3.03 |            2.9  |               0.5  |
| ETHUSDT |       1 |       68 |         1.13 |            1.14 |               0.62 |
| ETHUSDT |       3 |       44 |         1.27 |            1.27 |               0.75 |
| ETHUSDT |       5 |       20 |         1.59 |            1.32 |               0.45 |

Whole period: {'BTCUSDT': 'DCA 2.75x, tiered 2.56x of $3480 paid (ATH from 2020 only)', 'ETHUSDT': 'DCA 2.44x, tiered 2.18x of $3480 paid (ATH from 2020 only)'}

## #21 BTC by UTC weekday (close-to-close)

| wd   |   ('mean_bps', False) |   ('mean_bps', True) |   ('up_rate', False) |   ('up_rate', True) |   ('n', False) |   ('n', True) |
|:-----|----------------------:|---------------------:|---------------------:|--------------------:|---------------:|--------------:|
| Fri  |                   8.5 |                 14.6 |                0.518 |               0.502 |            139 |           209 |
| Mon  |                  52   |                 37.9 |                0.579 |               0.5   |            140 |           208 |
| Sat  |                  -0.9 |                  9.6 |                0.54  |               0.536 |            139 |           209 |
| Sun  |                  12.7 |                  3.2 |                0.532 |               0.507 |            139 |           209 |
| Thu  |                 -25.6 |                -13.6 |                0.468 |               0.459 |            139 |           209 |
| Tue  |                 -25.6 |                 30.5 |                0.432 |               0.548 |            139 |           208 |
| Wed  |                  44.6 |                 48.7 |                0.504 |               0.529 |            139 |           208 |

|                                   | value                 |
|:----------------------------------|:----------------------|
| IS best 3 days                    | ['Wed', 'Mon', 'Tue'] |
| IS/OOS rank corr of weekday means | 0.58                  |
| strategy IS Sharpe                | 1.18                  |
| strategy OOS Sharpe               | 0.92                  |
| BTC hold OOS Sharpe               | 0.72                  |
| IS Wed up-rate                    | 0.529 (z 0.83, n 208) |
| IS Fri up-rate                    | 0.502 (z 0.07, n 209) |
| OOS Wed up-rate                   | 0.504 (z 0.08, n 139) |
| OOS Fri up-rate                   | 0.518 (z 0.42, n 139) |

OOS Sharpe of all 35 three-day sets: median 0.19; IS-picked Mon/Tue/Wed = 0.92, rank 5/35 (p ~ 0.14)
