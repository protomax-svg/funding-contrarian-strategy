# Everything combined

Parts: atr, buffer, beta, no_short_rally, no_short_extreme, stop50, top40. 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.

| variant                          |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS total % |   OOS ann % |   maxDD |   OOS maxDD |   cost/yr |   exposure |
|:---------------------------------|-----:|------:|------------:|----------:|--------------:|------------:|--------:|------------:|----------:|-----------:|
| base (no filters)                | 1.31 |  0.93 |        0.51 |      0.66 |          59.6 |        19.8 |  -0.608 |      -0.267 |     0.07  |       0.96 |
| live now: base + ATR             | 1.49 |  1.07 |        0.69 |      0.81 |          62.7 |        20   |  -0.378 |      -0.137 |     0.054 |       0.58 |
| ALL combined                     | 1.48 |  1.67 |        1.12 |      1.17 |          72.3 |        21.2 |  -0.24  |      -0.084 |     0.056 |       0.58 |
| ALL minus atr                    | 1.7  |  2.42 |        1.82 |      2.05 |         148.3 |        35.1 |  -0.25  |      -0.11  |     0.073 |       0.96 |
| ALL minus buffer                 | 1.51 |  1.44 |        0.81 |      1    |          72   |        21.4 |  -0.361 |      -0.127 |     0.072 |       0.58 |
| ALL minus beta                   | 1.57 |  1.84 |        1.29 |      1.22 |          82.3 |        23.3 |  -0.275 |      -0.08  |     0.055 |       0.58 |
| ALL minus no_short_rally         | 1.51 |  1.38 |        0.97 |      0.92 |          58.7 |        18.2 |  -0.263 |      -0.096 |     0.043 |       0.58 |
| ALL minus no_short_extreme       | 1.49 |  1.65 |        1.1  |      1.18 |          71.5 |        21   |  -0.238 |      -0.086 |     0.055 |       0.58 |
| ALL minus stop50                 | 1.36 |  1.68 |        1.14 |      1.2  |          72.9 |        21.3 |  -0.231 |      -0.084 |     0.055 |       0.58 |
| ALL minus top40                  | 1.5  |  1.62 |        1.1  |      1.26 |          90.6 |        25.4 |  -0.227 |      -0.085 |     0.062 |       0.58 |
| robust core: ATR + buffer + beta | 1.31 |  1.35 |        0.96 |      1.07 |          68.8 |        20.8 |  -0.288 |      -0.094 |     0.045 |       0.58 |

`ALL minus X` = drop one part. If OOS goes UP when a part is dropped, that part is not pulling its weight.

## Return by calendar year (%)

|             |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| base        |   66.9 |  215.9 |  -21   |   -0.7 |    3.4 |   19.7 |   28.9 |
| live now    |   30   |  287.5 |   -3.2 |  -11   |   14.5 |   15.9 |   22.6 |
| ALL         |   24.9 |  180.2 |   17.4 |  -16.1 |   26.5 |   14.4 |   19.1 |
| robust core |   12.8 |  197.7 |   -4.5 |   -7.8 |   17.3 |   17.4 |   22.6 |

Placebo (100 time-shifted copies of the ALL book): OOS Sharpe median -0.39, best 1.40; real 1.67; share >= real: 0.00

## The IS-chosen combination (combo_grid.py): buffer + no_short_rally + stop50 + top40

| variant                                             |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS total % |   OOS ann % |   maxDD |   OOS maxDD |   cost/yr |   exposure |
|:----------------------------------------------------|-----:|------:|------------:|----------:|--------------:|------------:|--------:|------------:|----------:|-----------:|
| IS-chosen: buffer + no_short_rally + stop50 + top40 | 1.92 |  2.38 |         1.8 |      1.81 |         148.7 |        35.2 |  -0.248 |       -0.09 |      0.07 |       0.96 |

By year (%): 2020: 74.5, 2021: 226.2, 2022: 9.6, 2023: -4.6, 2024: 35.3, 2025: 33.6, 2026: 37.5

|                           | value         |
|:--------------------------|:--------------|
| OOS price %/yr            | 34.5          |
| OOS funding %/yr          | 8.3           |
| OOS cost %/yr             | 7.6           |
| placebo OOS median / best | (-0.35, 1.58) |
| placebo share >= real     | 0.0           |
| worst day %               | -10.2         |
| worst month %             | -16.6         |
