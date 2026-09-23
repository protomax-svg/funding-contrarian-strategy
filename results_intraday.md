# Intraday / pairs results

## #2 Bollinger + VWAP breakout, BTC 1h (posted params; post dated 2025-06-25)

2.5 bps = the post's 0.025% commission. 7 bps = our realistic taker+slippage. `after_post` = 2025-07..2026-08, never seen by the author.

| name                        |   all_sharpe |   all_annret |   IS_sharpe |   OOS_sharpe |   OOS_annret |   maxdd |   p_boot |   after_post_sharpe |   after_post_ret |   trades |   win% |   avg_trade_bps |
|:----------------------------|-------------:|-------------:|------------:|-------------:|-------------:|--------:|---------:|--------------------:|-----------------:|---------:|-------:|----------------:|
| v1 BB only @ 2.5bps         |        -0.38 |       -0.049 |       -0.32 |        -0.49 |       -0.054 |  -0.423 |    0.863 |               -1.17 |           -0.123 |     3373 |   37.4 |            -2.6 |
| v2 BB+VWAP/ADX/RSI @ 2.5bps |         0.41 |        0.126 |        0.54 |         0.19 |        0.052 |  -0.485 |    0.135 |               -0.06 |           -0.017 |     8440 |   40.1 |             3.4 |
| v1 BB only @ 7.0bps         |        -1.53 |       -0.201 |       -1.41 |        -1.79 |       -0.203 |  -0.774 |    1     |               -2.64 |           -0.285 |     3373 |   32.5 |           -11.6 |
| v2 BB+VWAP/ADX/RSI @ 7.0bps |        -0.82 |       -0.254 |       -0.66 |        -1.12 |       -0.312 |  -0.929 |    0.984 |               -1.46 |           -0.43  |     8440 |   37.4 |            -5.6 |

±20% grid (81 variants, 7 bps): median OOS Sharpe -1.19, share OOS>0 0.00, median after-post Sharpe -1.46, median avg trade -6.5 bps.

## #13 Hour-of-day / session effect

Hours ranked on 2020-2023 only, traded 2024+. Each held hour costs a round trip (the edge must beat ~14 bps).

| series    |   k_hours |   rank_corr_IS_vs_OOS |   OOS_gross_bps_per_trade |   OOS_net_ann | IS_best_hours_UTC       | IS_worst_hours_UTC     |
|:----------|----------:|----------------------:|--------------------------:|--------------:|:------------------------|:-----------------------|
| BTC       |         3 |                  0.12 |                      0.61 |        -2.932 | [21, 13, 20]            | [2, 23, 14]            |
| BTC       |         6 |                  0.12 |                      0.37 |        -5.972 | [21, 13, 20, 22, 0, 15] | [2, 23, 14, 4, 17, 3]  |
| EW top-30 |         3 |                 -0.25 |                     -1.69 |        -3.436 | [0, 5, 13]              | [14, 3, 2]             |
| EW top-30 |         6 |                 -0.25 |                     -0.07 |        -6.162 | [0, 5, 13, 15, 21, 7]   | [14, 3, 2, 17, 11, 18] |

## #5 Kalman-filter BTC/ETH pairs (4h)

Kalman delta=1e-4, Ve=1e-3 (Chan defaults, not tuned). Funding on the two legs nearly cancels and is ignored here.

| name                                   |   all_sharpe |   all_annret |   IS_sharpe |   OOS_sharpe |   OOS_annret |   maxdd |   p_boot |   time_in_mkt |
|:---------------------------------------|-------------:|-------------:|------------:|-------------:|-------------:|--------:|---------:|--------------:|
| Chan z=e/sqrt(Q) entry 0.5 exit 0      |        -0.75 |       -0.063 |       -1.06 |         0.83 |        0.016 |  -0.42  |    0.968 |          0.02 |
| Chan z=e/sqrt(Q) entry 1.0 exit 0      |        -0.43 |       -0.025 |       -0.56 |         0    |      nan     |  -0.21  |    0.923 |          0    |
| Chan z=e/sqrt(Q) entry 1.5 exit 0      |        -0.16 |       -0.007 |       -0.2  |         0    |      nan     |  -0.098 |    0.736 |          0    |
| Chan z=e/sqrt(Q) entry 2.0 exit 0      |         0.07 |        0.003 |        0.09 |         0    |      nan     |  -0.069 |    0.141 |          0    |
| post: rolling z lb=10 entry 1.5 exit 0 |        -0.39 |       -0.076 |       -0.05 |        -1.22 |       -0.174 |  -0.662 |    0.851 |          0.62 |
| post: rolling z lb=10 entry 2.0 exit 0 |         0.23 |        0.041 |        0.64 |        -0.68 |       -0.092 |  -0.444 |    0.278 |          0.5  |
| post: rolling z lb=10 entry 2.5 exit 0 |         0.23 |        0.029 |        0.82 |        -1.17 |       -0.109 |  -0.387 |    0.257 |          0.22 |
| post: rolling z lb=30 entry 1.5 exit 0 |         0.29 |        0.06  |        0.41 |         0.03 |        0.005 |  -0.382 |    0.23  |          0.82 |
| post: rolling z lb=30 entry 2.0 exit 0 |         0.41 |        0.085 |        0.61 |         0    |        0     |  -0.372 |    0.143 |          0.77 |
| post: rolling z lb=30 entry 2.5 exit 0 |         0.55 |        0.107 |        0.86 |        -0.11 |       -0.017 |  -0.388 |    0.088 |          0.68 |
| post: rolling z lb=90 entry 1.5 exit 0 |         0.42 |        0.091 |        0.81 |        -0.43 |       -0.067 |  -0.498 |    0.167 |          0.88 |
| post: rolling z lb=90 entry 2.0 exit 0 |         0.52 |        0.111 |        0.98 |        -0.49 |       -0.077 |  -0.45  |    0.108 |          0.85 |
| post: rolling z lb=90 entry 2.5 exit 0 |         0.47 |        0.1   |        0.98 |        -0.68 |       -0.105 |  -0.455 |    0.13  |          0.81 |

## #6 Rolling cointegration pairs, top-20, 4h (90d formation, 30d trading)

Pairs picked only from data before each 30-day window. Up to 5 pairs, 1/5 capital each. 7 bps/side, 2 legs.

| name                          |   all_sharpe |   all_annret |   IS_sharpe |   OOS_sharpe |   OOS_annret |   maxdd |   p_boot |   avg_pairs_found |
|:------------------------------|-------------:|-------------:|------------:|-------------:|-------------:|--------:|---------:|------------------:|
| EG t<-3.9 entry 2.0 stop 4.0  |        -1.71 |       -0.194 |       -1.69 |        -1.74 |       -0.193 |  -0.743 |    1     |               2.7 |
| EG t<-3.34 entry 2.0 stop 4.0 |        -2.36 |       -0.416 |       -2.21 |        -2.75 |       -0.395 |  -0.948 |    1     |               4.5 |
| EG t<-3.9 entry 1.5 stop 3.0  |        -1.6  |       -0.189 |       -1.47 |        -1.78 |       -0.224 |  -0.755 |    1     |               2.7 |
| EG t<-3.9 entry 2.0 stop 99   |        -0.5  |       -0.074 |       -0.58 |        -0.38 |       -0.058 |  -0.482 |    0.905 |               2.7 |
