# Idea #19: buy the dip near the 52-week high (+ nearness-to-high factor)

Source: https://www.reddit.com/r/algotrading/comments/1tzicir/ (QQQ, 2026-06) and follow-up 1ty1rch.
All Binance crypto perps, point-in-time top-100, 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.
Drops/distances in units of each coin's 30d daily vol (QQQ -3.3..-6.3% at ~1.5% vol -> -2.2..-4.2 sigma; within 5% -> within 3.3 sigma).

## A. Event study (entry at the drop-day close; t = month-clustered; 'vs mkt' = minus EW top-100)

| spec                                            | period   | group   |   events |   dates |   ret21d % |   pos21d |   t21d |   vs mkt 21d % |   t vs mkt 21d |   heat21d % |   ret63d % |   pos63d |   t63d |   vs mkt 63d % |   t vs mkt 63d |   heat63d % |
|:------------------------------------------------|:---------|:--------|---------:|--------:|-----------:|---------:|-------:|---------------:|---------------:|------------:|-----------:|---------:|-------:|---------------:|---------------:|------------:|
| BTC only, post's raw % (-3.3..-6.3%, within 5%) | IS       | near    |        2 |       2 |       -2.6 |     0    | nan    |          -16.7 |         nan    |        -8.5 |      -16.8 |     0    | nan    |          -44.7 |         nan    |       -19.2 |
| BTC only, post's raw % (-3.3..-6.3%, within 5%) | IS       | far     |       92 |      92 |        3.7 |     0.57 |   1.97 |           -2.9 |          -0.98 |        -7.8 |       11.6 |     0.6  |   2.21 |          -14.6 |          -0.98 |       -16.2 |
| BTC only, post's raw % (-3.3..-6.3%, within 5%) | OOS      | near    |        1 |       1 |       -1.2 |     0    | nan    |           12.5 |         nan    |        -5.4 |        9.6 |     1    | nan    |            1.6 |         nan    |        -5.9 |
| BTC only, post's raw % (-3.3..-6.3%, within 5%) | OOS      | far     |       56 |      56 |        3.2 |     0.55 |   1.91 |           -2   |          -0.29 |        -6.1 |        8.9 |     0.68 |   1.83 |            2.5 |           0.8  |        -8.4 |
| BTC only, vol-scaled                            | IS       | near    |        1 |       1 |        7.2 |     1    | nan    |          -20.5 |         nan    |         0.3 |       21   |     1    | nan    |           -7.5 |         nan    |        -4.1 |
| BTC only, vol-scaled                            | IS       | far     |       24 |      24 |        4.3 |     0.67 |   1.54 |            2.2 |           0.03 |        -8.2 |        3.1 |     0.46 |   0.86 |           -0.3 |          -0.13 |       -18.8 |
| BTC only, vol-scaled                            | OOS      | near    |        2 |       2 |        4.4 |     0.5  | nan    |            0.5 |         nan    |        -4.1 |        3.7 |     0.5  | nan    |            6.7 |         nan    |        -7.2 |
| BTC only, vol-scaled                            | OOS      | far     |       21 |      21 |       -0.2 |     0.52 |   0.84 |            1.2 |           0.87 |        -8.7 |        2.7 |     0.57 |   0.96 |            3   |           1.33 |       -11.8 |
| top-100, vol-scaled                             | IS       | near    |       12 |      10 |      -12.7 |     0.3  |  -1.24 |          -30.9 |          -5.13 |       -22   |       11.8 |     0.6  |   0.42 |          -53.6 |          -2.55 |       -31.2 |
| top-100, vol-scaled                             | IS       | far     |     1849 |     194 |        1.3 |     0.52 |   1.64 |           -4.7 |          -1.6  |       -13.5 |        6.2 |     0.45 |   1.75 |          -10.5 |          -2.2  |       -24   |
| top-100, vol-scaled                             | OOS      | near    |       14 |      11 |       -8.4 |     0.25 |  -0.49 |           -9.9 |          -0.91 |       -23.5 |       -1.6 |     0.36 |  -0.41 |            3.1 |           0.65 |       -27.8 |
| top-100, vol-scaled                             | OOS      | far     |     1098 |     200 |       -7.8 |     0.34 |  -2.47 |           -9.5 |          -3.66 |       -19.5 |        1.6 |     0.31 |   0.29 |           -1.6 |          -0.24 |       -30   |
| top-100, deeper drop -3..-6 sigma               | IS       | near    |        0 |       0 |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |
| top-100, deeper drop -3..-6 sigma               | IS       | far     |      911 |      95 |        0.4 |     0.46 |   0.71 |           -6   |          -2.78 |       -13.5 |        3.4 |     0.46 |   0.93 |          -17.4 |          -3.17 |       -22.3 |
| top-100, deeper drop -3..-6 sigma               | OOS      | near    |        0 |       0 |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |
| top-100, deeper drop -3..-6 sigma               | OOS      | far     |      368 |      92 |      -10.7 |     0.33 |  -2.75 |          -13.3 |          -3.63 |       -21.7 |      -10.4 |     0.35 |  -1.32 |          -14.1 |          -2.3  |       -31.4 |
| top-100, near = within 2 sigma                  | IS       | near    |        0 |       0 |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |
| top-100, near = within 2 sigma                  | IS       | far     |     1861 |     198 |        0.7 |     0.51 |   1.49 |           -5.6 |          -1.92 |       -13.9 |        5.9 |     0.45 |   1.64 |          -12.4 |          -2.41 |       -24.3 |
| top-100, near = within 2 sigma                  | OOS      | near    |        0 |       0 |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |      nan   |   nan    | nan    |          nan   |         nan    |       nan   |
| top-100, near = within 2 sigma                  | OOS      | far     |     1112 |     204 |       -7.7 |     0.34 |  -2.16 |           -9.5 |          -3.67 |       -19.7 |        2.2 |     0.32 |   0.34 |           -1.1 |          -0.16 |       -29.9 |
| top-100, near = within 5 sigma                  | IS       | near    |       67 |      34 |        2.8 |     0.44 |   0.2  |           -9.8 |          -2.99 |       -17.6 |       31.2 |     0.5  |   1.77 |           -1.8 |          -0.11 |       -26.8 |
| top-100, near = within 5 sigma                  | IS       | far     |     1794 |     186 |        1.6 |     0.52 |   1.79 |           -4.5 |          -1.05 |       -13   |        5.1 |     0.45 |   1.85 |          -11.6 |          -2.02 |       -23.5 |
| top-100, near = within 5 sigma                  | OOS      | near    |       72 |      42 |      -17.4 |     0.29 |  -2.67 |          -17   |          -2.8  |       -28.4 |       29   |     0.21 |   0.54 |           30.7 |           0.52 |       -37.1 |
| top-100, near = within 5 sigma                  | OOS      | far     |     1040 |     186 |       -5.4 |     0.36 |  -1.43 |           -7.4 |          -3.17 |       -17.3 |       -6.2 |     0.33 |  -0.62 |           -9.5 |          -2.27 |       -28.1 |

## B. Trade every dip for H days (gross 1 when any open)

| book                        | hedge   |    IS |   OOS |   OOS@15bps |    +1d |   ann ret % |   maxDD |   alpha/yr |   alpha t |   b_EW |   b_BTC |   time in mkt |
|:----------------------------|:--------|------:|------:|------------:|-------:|------------:|--------:|-----------:|----------:|-------:|--------:|--------------:|
| near dips, hold 21d         | none    | -0.77 |  0.37 |        0.37 |   0.43 |         4.8 |   -0.97 |     -0.375 |     -0.13 |   0.57 |    0.13 |          0.15 |
| near dips, hold 21d         | BTC     | -0.96 |  0.43 |        0.43 |   0.48 |         9.6 |   -0.94 |     -0.192 |     -0.06 |   0.62 |   -0.91 |          0.13 |
| near dips, hold 21d         | EW      | -1.61 |  0.42 |        0.42 |   0.49 |        -6.5 |   -0.98 |      0.083 |      0.03 |  -0.4  |    0.13 |          0.15 |
| far dips, hold 21d          | none    |  0.47 | -1.17 |       -1.23 |  -1.23 |       -16.2 |   -1    |     -0.772 |     -4.53 |   0.9  |    0.06 |          0.85 |
| far dips, hold 21d          | BTC     |  0.09 | -1.93 |       -2.01 |  -2.14 |       -46   |   -0.99 |     -0.673 |     -3.96 |   0.9  |   -0.93 |          0.85 |
| far dips, hold 21d          | EW      | -0.58 | -1.67 |       -1.81 |  -2.19 |       -39.9 |   -0.96 |     -0.441 |     -2.65 |  -0.07 |    0.03 |          0.85 |
| near dips, hold 63d         | none    |  0.14 |  0.5  |        0.5  |   0.52 |        44.1 |   -0.94 |      0.326 |      0.24 |   0.62 |    0.12 |          0.36 |
| near dips, hold 63d         | BTC     | -0.18 |  0.44 |        0.44 |   0.46 |        27.7 |   -0.95 |      0.498 |      0.31 |   0.68 |   -0.94 |          0.31 |
| near dips, hold 63d         | EW      | -0.91 |  0.57 |        0.56 |   0.58 |        14.2 |   -0.98 |      0.801 |      0.58 |  -0.35 |    0.1  |          0.36 |
| far dips, hold 63d          | none    |  0.62 | -0.45 |       -0.47 |  -0.48 |        16.9 |   -0.96 |     -0.442 |     -5.76 |   0.91 |    0.09 |          0.91 |
| far dips, hold 63d          | BTC     |  0.24 | -1.21 |       -1.23 |  -1.25 |       -17.7 |   -0.94 |     -0.336 |     -4.41 |   0.91 |   -0.91 |          0.91 |
| far dips, hold 63d          | EW      | -0.34 | -0.99 |       -1.1  |  -1.12 |       -11   |   -0.6  |     -0.113 |     -1.55 |  -0.06 |    0.07 |          0.91 |
| EW top-100 long (benchmark) | none    |  1.07 |  0.29 |      nan    | nan    |       nan   |   -0.84 |    nan     |    nan    | nan    |  nan    |        nan    |

## C. Cross-sectional nearness to 365d high (long nearest quintile, short farthest)

Headline fixed before looking: 365d, q=0.2, weekly, top-100.

|                       |   value |
|:----------------------|--------:|
| IS                    |   0.71  |
| OOS                   |   0.59  |
| OOS@15bps             |   0.53  |
| OOS +1d               |   0.71  |
| walk-fwd OOS          |   0.7   |
| placebo p             |   0.3   |
| placebo median        |   0.47  |
| alpha/yr              |   0.241 |
| alpha t               |   2.33  |
| b_EW                  |  -0.2   |
| b_BTC                 |   0.16  |
| maxDD                 |  -0.37  |
| OOS maxDD             |  -0.29  |
| corr w/ momentum      |   0.41  |
| alpha vs momentum t   |   1.91  |
| corr w/ funding strat |   0.06  |
| top-30 OOS            |   0.65  |
| top-50 OOS            |   0.42  |
| momentum 365d OOS     |   0.27  |

### Grid (all 18 points)

|   lookback |    q |   rebal d |    IS |   OOS |
|-----------:|-----:|----------:|------:|------:|
|         90 | 0.2  |         1 |  0.83 |  1.22 |
|         90 | 0.2  |         7 |  0.45 |  0.56 |
|         90 | 0.2  |        30 | -0.46 |  0.24 |
|         90 | 0.33 |         1 |  0.68 |  1.08 |
|         90 | 0.33 |         7 |  0.53 |  0.44 |
|         90 | 0.33 |        30 | -0.2  |  0.05 |
|        180 | 0.2  |         1 |  1.06 |  0.65 |
|        180 | 0.2  |         7 |  1.04 |  0.39 |
|        180 | 0.2  |        30 |  0.43 |  0.32 |
|        180 | 0.33 |         1 |  1.09 |  0.47 |
|        180 | 0.33 |         7 |  0.94 |  0.41 |
|        180 | 0.33 |        30 |  0.53 |  0.19 |
|        365 | 0.2  |         1 |  0.82 |  0.82 |
|        365 | 0.2  |         7 |  0.71 |  0.59 |
|        365 | 0.2  |        30 |  0.74 |  0.59 |
|        365 | 0.33 |         1 |  0.41 |  0.46 |
|        365 | 0.33 |         7 |  0.63 |  0.22 |
|        365 | 0.33 |        30 |  0.74 |  0.61 |

### Blend with the live funding strategy

|                        |    IS |   OOS |   maxDD |
|:-----------------------|------:|------:|--------:|
| nearness               |  0.71 |  0.59 |   -0.37 |
| momentum               | -0.38 |  0.27 |   -0.49 |
| funding                |  2.12 |  1.1  |   -0.27 |
| 50/50 funding+nearness |  1.89 |  1.17 |   -0.22 |

### Return by year (%)

|   ts |   nearness |   momentum |   funding |   50/50 funding+nearness |
|-----:|-----------:|-----------:|----------:|-------------------------:|
| 2020 |       63.3 |        0   |      86.5 |                     75.8 |
| 2021 |       18.7 |        8.2 |     146.4 |                     74.4 |
| 2022 |      -18.6 |      -26.1 |      13.4 |                     -2.8 |
| 2023 |       10   |      -16   |       8   |                      9.5 |
| 2024 |       11.2 |       -1.7 |      35   |                     23.9 |
| 2025 |       52.3 |       29.3 |      40.6 |                     50.2 |
| 2026 |      -14.9 |      -13   |      17.7 |                      3   |
