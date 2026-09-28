# Lead from #19: short sharp-drop coins far from their high, hedged with the EW market

Found by looking at OOS in dip52.py, so the post-like base is NOT a clean OOS test; the IS-best point and the walk-forward are. Max 5% per short coin (uncapped, one coin could be ~100% of the short leg: PIPPIN 2025-10, LAB 2026-07 squeezes). 7 bps, real funding, top-100.

|                        | post-like base (-4.2..-2.2, far, 21d)   | IS-best (-99, -2.2, 7, False)   |
|:-----------------------|:----------------------------------------|:--------------------------------|
| IS                     | 0.67                                    | 1.49                            |
| OOS                    | 1.49                                    | 0.29                            |
| OOS@15bps              | 1.31                                    | 0.09                            |
| OOS +1d                | 1.87                                    | 0.08                            |
| placebo p              | 0.0                                     | 0.0                             |
| alpha/yr               | 0.175                                   | 0.13                            |
| alpha t                | 2.59                                    | 1.65                            |
| b_EW                   | 0.04                                    | 0.02                            |
| b_BTC                  | -0.02                                   | -0.01                           |
| maxDD                  | -0.25                                   | -0.28                           |
| ann ret %              | 15.9                                    | 10.1                            |
| funding recv/yr %      | 2.9                                     | -1.7                            |
| cost/yr %              | 2.5                                     | 3.1                             |
| avg short gross        | 0.39                                    | 0.2                             |
| corr w/ funding strat  | -0.03                                   | 0.0                             |
| blend 25% IS/OOS/maxDD | 2.18 / 1.38 / -0.19                     | 2.28 / 1.14 / -0.24             |
| blend 50% IS/OOS/maxDD | 2.12 / 1.76 / -0.14                     | 2.46 / 1.09 / -0.22             |

Grid (24 points): IS>0 0.75, OOS>0 0.83, median IS 0.52, median OOS 0.66. Walk-forward over the grid (365d train, 30d step): OOS 1.45. Funding strat alone: IS 2.12, OOS 1.1, maxDD -0.27.

## Return by year (%)

|   ts |   post-like base (-4.2..-2.2, far, 21d) |   IS-best (-99, -2.2, 7, False) |   funding strat |
|-----:|----------------------------------------:|--------------------------------:|----------------:|
| 2020 |                                    10.9 |                             8.4 |            86.5 |
| 2021 |                                    40.2 |                            29.4 |           146.4 |
| 2022 |                                    -3.9 |                            13.3 |            13.4 |
| 2023 |                                   -10.9 |                             3.7 |             8   |
| 2024 |                                     7.7 |                             5.2 |            35   |
| 2025 |                                    35   |                           -17.1 |            40.6 |
| 2026 |                                    38.8 |                            26.7 |            17.7 |

## Grid

| drop sigma   |   hold | far only   |    IS |   OOS |
|:-------------|-------:|:-----------|------:|------:|
| -4.2..-2.2   |      7 | True       |  1.22 |  0.41 |
| -4.2..-2.2   |      7 | False      |  1.32 | -0.03 |
| -4.2..-2.2   |     21 | True       |  0.67 |  1.49 |
| -4.2..-2.2   |     21 | False      |  0.8  |  0.83 |
| -4.2..-2.2   |     63 | True       |  0.15 |  0.81 |
| -4.2..-2.2   |     63 | False      | -0.18 |  0.61 |
| -3..-1.5     |      7 | True       |  0.3  | -0.42 |
| -3..-1.5     |      7 | False      |  0.45 | -0.63 |
| -3..-1.5     |     21 | True       | -0.26 |  0.38 |
| -3..-1.5     |     21 | False      | -0.44 |  0.09 |
| -3..-1.5     |     63 | True       | -0.05 |  0.22 |
| -3..-1.5     |     63 | False      | -0.87 | -0.43 |
| -6..-3       |      7 | True       |  0.5  |  1.18 |
| -6..-3       |      7 | False      |  0.68 |  0.42 |
| -6..-3       |     21 | True       |  0.7  |  1.93 |
| -6..-3       |     21 | False      |  1.04 |  1.21 |
| -6..-3       |     63 | True       |  0.53 |  1.85 |
| -6..-3       |     63 | False      |  0.29 |  1.45 |
| -99..-2.2    |      7 | True       |  1.31 |  0.7  |
| -99..-2.2    |      7 | False      |  1.49 |  0.29 |
| -99..-2.2    |     21 | True       |  0.64 |  1.66 |
| -99..-2.2    |     21 | False      |  0.81 |  1.19 |
| -99..-2.2    |     63 | True       |  0.11 |  0.91 |
| -99..-2.2    |     63 | False      | -0.15 |  0.6  |
