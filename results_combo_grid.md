# All 128 combinations

Sorted by IS Sharpe (the only fair way to choose). Spearman corr of IS vs OOS across combos: 0.28. Median OOS of all combos: 1.50; OOS of the IS-best combo: 2.38.

## Top 10 by IS

| parts                                               |   IS |   OOS |   maxDD |
|:----------------------------------------------------|-----:|------:|--------:|
| buffer+no_short_rally+stop50+top40                  | 1.92 |  2.38 |  -0.248 |
| buffer+no_short_rally+no_short_extreme+stop50+top40 | 1.9  |  2.39 |  -0.254 |
| buffer+stop50+top40                                 | 1.88 |  1.97 |  -0.296 |
| buffer+no_short_rally+stop50                        | 1.78 |  1.54 |  -0.279 |
| buffer+no_short_rally+top40                         | 1.78 |  2.4  |  -0.248 |
| buffer+no_short_rally+no_short_extreme+top40        | 1.77 |  2.41 |  -0.254 |
| buffer+no_short_extreme+stop50+top40                | 1.75 |  1.9  |  -0.345 |
| buffer+no_short_rally+no_short_extreme+stop50       | 1.75 |  1.55 |  -0.277 |
| buffer+beta+no_short_rally+stop50                   | 1.74 |  1.7  |  -0.245 |
| atr+stop50+top40                                    | 1.74 |  1.33 |  -0.368 |

## Average effect of each part across all combos

|                  |   IS gain |   OOS gain |   maxDD gain |
|:-----------------|----------:|-----------:|-------------:|
| atr              |     -0.05 |      -0.25 |        0.071 |
| buffer           |      0.03 |       0.22 |        0.112 |
| beta             |     -0.04 |       0.02 |        0.045 |
| no_short_rally   |      0.03 |       0.3  |        0.063 |
| no_short_extreme |     -0.04 |       0.01 |       -0.007 |
| stop50           |      0.13 |      -0    |        0.027 |
| top40            |      0.07 |       0.37 |       -0.002 |
