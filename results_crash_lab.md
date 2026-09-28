# Crash-short book: filters, exits, sizing, hedges

One change at a time on top of the live base. 7 bps, real funding, top-100, all perps. IS 2020-23, OOS 2024-01..2026-08. events kept = share of the base's events that pass the filter.

22 variants. IS-best: **filter: volume spike on the drop day (> 2x 30d avg)** (IS 1.96 -> OOS 1.32; base IS 0.67 -> OOS 1.49). Rank correlation IS vs OOS across variants: -0.45 (near 0 = the IS ranking does not carry over). Variants with IS > base and OOS > base: 0.

| variant                                                     |    IS |   OOS |   OOS@15bps |   OOS +1d |   IS %/yr |   OOS %/yr |   maxDD |   events kept |   avg short gross |
|:------------------------------------------------------------|------:|------:|------------:|----------:|----------:|-----------:|--------:|--------------:|------------------:|
| base (live)                                                 |  0.67 |  1.49 |        1.31 |      1.87 |       7.8 |       28.1 |  -0.246 |          1    |              0.39 |
| filter: market vol high (30d EW vol >= median of last year) |  1.33 |  1    |        0.82 |      0.81 |      12.3 |       10.4 |  -0.159 |          0.43 |              0.19 |
| filter: market vol top third                                |  1.49 |  1.19 |        1.04 |      1.14 |       9.1 |       10.8 |  -0.093 |          0.32 |              0.13 |
| filter: market vol low (below median)                       | -0.85 |  1.28 |        1.17 |      1.84 |      -6.5 |       21   |  -0.311 |          0.56 |              0.23 |
| filter: market vol rising (7d/60d EW vol > 1)               |  0.25 |  1.58 |        1.43 |      1.74 |       2.4 |       23.3 |  -0.28  |          0.69 |              0.26 |
| filter: market vol rising strongly (> 1.25)                 |  0.73 |  1.27 |        1.15 |      1.66 |       5   |       16.2 |  -0.159 |          0.46 |              0.15 |
| filter: BTC ATR not in its low third                        |  0.93 |  1.36 |        1.2  |      1.59 |       9.7 |       21.8 |  -0.189 |          0.6  |              0.28 |
| filter: coin vol rising before the drop (7d/60d > 1)        |  0.22 |  1.04 |        0.91 |      1.1  |       2.1 |       16.2 |  -0.258 |          0.36 |              0.26 |
| filter: coin vol calm before the drop (7d/60d <= 1)         |  0.37 |  1.41 |        1.24 |      1.67 |       4.2 |       23.9 |  -0.229 |          0.61 |              0.35 |
| filter: idiosyncratic: market that day > -1 sigma           |  1.17 |  1.25 |        1.19 |      2.02 |       6.9 |       18.4 |  -0.155 |          0.08 |              0.1  |
| filter: market-wide crash day (market <= -1 sigma)          |  0.44 |  1.39 |        1.19 |      1.12 |       5   |       20.3 |  -0.301 |          0.92 |              0.35 |
| filter: volume spike on the drop day (> 2x 30d avg)         |  1.96 |  1.32 |        1.23 |      1.64 |      17.6 |       21.5 |  -0.152 |          0.22 |              0.2  |
| filter: no volume spike (<= 2x)                             | -0.42 |  1.36 |        1.18 |      1.41 |      -4.4 |       21.6 |  -0.333 |          0.78 |              0.35 |
| filter: 7d funding >= 0 (shorts not crowded)                |  0.57 |  1.19 |        1.01 |      1.09 |       6.5 |       19.7 |  -0.336 |          0.76 |              0.37 |
| filter: 7d funding < 0 (shorts crowded)                     |  0.27 |  1.55 |        1.45 |      2.08 |       2   |       22.4 |  -0.127 |          0.24 |              0.19 |
| exit: squeeze stop +30%                                     |  0.45 |  0.64 |        0.43 |      0.79 |       4.8 |       11.1 |  -0.281 |          1    |              0.38 |
| exit: squeeze stop +50%                                     |  0.81 |  0.86 |        0.66 |      1.21 |       9.3 |       15.3 |  -0.277 |          1    |              0.39 |
| exit: back above pre-drop close                             |  1.21 |  0.96 |        0.75 |      1.28 |      11.2 |       17.5 |  -0.266 |          1    |              0.34 |
| cap 3%                                                      |  0.56 |  1.56 |        1.38 |      1.76 |       4.8 |       22.3 |  -0.221 |          1    |              0.31 |
| cap 10%                                                     |  0.71 |  1.33 |        1.17 |      2.03 |      12   |       37   |  -0.267 |          1    |              0.5  |
| inverse-vol size                                            |  0.7  |  1.22 |        1.04 |      1.39 |       8.4 |       21.1 |  -0.205 |          1    |              0.38 |
| hedge: BTC only                                             | -0.29 |  1.26 |        1.18 |      1.46 |     -11.1 |       51.8 |  -0.739 |          1    |              0.57 |
| hedge: top-10 EW                                            | -0.62 |  1.83 |        1.72 |      1.81 |     -14.9 |       61.8 |  -0.585 |          1    |              0.52 |

## Top 3 by IS: placebo, alpha, blend with the live funding book

| variant                                                     |   IS |   OOS |   placebo p (all years) |   alpha t |   corr w/ funding book |   50/50 with funding OOS |   50/50 maxDD |
|:------------------------------------------------------------|-----:|------:|------------------------:|----------:|-----------------------:|-------------------------:|--------------:|
| filter: volume spike on the drop day (> 2x 30d avg)         | 1.96 |  1.32 |                       0 |      3.88 |                   0.02 |                     1.71 |        -0.187 |
| filter: market vol top third                                | 1.49 |  1.19 |                       0 |      3.36 |                   0.02 |                     1.53 |        -0.148 |
| filter: market vol high (30d EW vol >= median of last year) | 1.33 |  1    |                       0 |      2.8  |                   0.01 |                     1.52 |        -0.148 |
| base (live)                                                 | 0.67 |  1.49 |                     nan |      2.59 |                   0    |                     1.84 |        -0.156 |

## Return by year (%)

|   ts |   base |   volume spike on the drop day (> 2x 30d avg) |   market vol top third |   market vol high (30d EW vol >= median of last year) |
|-----:|-------:|----------------------------------------------:|-----------------------:|------------------------------------------------------:|
| 2020 |   10.9 |                                           6.8 |                    0   |                                                   5.7 |
| 2021 |   40.2 |                                          61.6 |                   30.4 |                                                  43.5 |
| 2022 |   -3.9 |                                          16.6 |                    5.7 |                                                   6.3 |
| 2023 |  -10.9 |                                          -1   |                    3.6 |                                                  -0.4 |
| 2024 |    7.7 |                                           2.5 |                    5.2 |                                                   3.3 |
| 2025 |   35   |                                          22   |                   25.5 |                                                  26   |
| 2026 |   38.8 |                                          36.9 |                    0   |                                                   0   |
