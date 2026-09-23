# Robustness battery (daily survivors)

Base params = as posted / neutral guess, never re-fit. 7 bps/side unless noted. placebo_p = share of 100-200 time-shifted copies with Sharpe >= the real one.

| candidate                   |   Sharpe_all |   IS |   OOS |   OOS@15bps |   OOS +1d delay |   walkfwd_OOS |   placebo_p |   placebo_median |   alpha_ann |   alpha_t |   beta_EW |   beta_BTC |   OOS top10 |   OOS top20 |   OOS top50 |
|:----------------------------|-------------:|-----:|------:|------------:|----------------:|--------------:|------------:|-----------------:|------------:|----------:|----------:|-----------:|------------:|------------:|------------:|
| RSI TS-momentum (#4)        |         1.05 | 1.18 |  0.85 |        0.71 |            0.12 |          0.69 |       0     |             0.27 |       0.239 |      2.7  |      0.22 |      -0.03 |        1.12 |        0.81 |        0.98 |
| RSI TS-momentum on BTC (#4) |         1.16 | 1.42 |  0.64 |        0.47 |           -0.17 |          0.54 |       0.005 |             0.22 |       0.234 |      1.4  |     -0.08 |       0.87 |      nan    |      nan    |      nan    |
| Funding contrarian XS (#7b) |         1.17 | 1.31 |  0.93 |        0.51 |            0.66 |          0.86 |       0     |            -0.17 |       0.332 |      3.06 |      0.05 |      -0.05 |        0.81 |        1.09 |        1.58 |
| IBS dip (#12)               |         0.74 | 0.87 |  0.52 |        0.44 |            0.32 |          0.32 |       0.07  |             0.44 |       0.122 |      1    |      0.35 |      -0.02 |        0.57 |        0.65 |        0.44 |
| Z-score trend on BTC (#1)   |         1    | 1.17 |  0.69 |        0.66 |            0.62 |          0.5  |       0.03  |             0.34 |      -0.075 |     -1.14 |     -0.02 |       0.97 |      nan    |      nan    |      nan    |
| Taker-flow follow XS (#14)  |         1.64 | 2.28 |  0.4  |        0.01 |            0.72 |          0.57 |       0     |             0.17 |       0.415 |      4.34 |     -0.12 |       0.12 |        0.7  |        0.62 |        0.39 |
| XS momentum L/S (#17)       |         1    | 1.45 |  0.12 |       -0.01 |            0.01 |          0.14 |       0.02  |            -0.04 |       0.328 |      2.69 |     -0.05 |       0.02 |        0.63 |        0.42 |        0.23 |

## Sharpe by calendar year

|                             |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:----------------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| RSI TS-momentum (#4)        |   1.21 |   2.59 |  -1.48 |   1.18 |   1.96 |  -0.19 |   0.62 |
| RSI TS-momentum on BTC (#4) |   1.88 |   1.98 |  -1.01 |   1.84 |   1.12 |  -0.19 |   0.64 |
| Funding contrarian XS (#7b) |   2.22 |   2.75 |  -0.84 |   0.07 |   0.26 |   0.99 |   2.61 |
| IBS dip (#12)               |   2.01 |   1.78 |  -0.37 |   0.69 |   1.17 |   0.83 |  -0.84 |
| Z-score trend on BTC (#1)   |   2.29 |   0.9  |  -1.49 |   1.76 |   0.92 |   0.27 |   1.01 |
| Taker-flow follow XS (#14)  |   3.99 |   2.65 |   1.56 |   0.63 |  -0.24 |   1.93 |  -0.28 |
| XS momentum L/S (#17)       |   1.49 |   2.51 |   0.31 |   0.96 |   0.72 |  -0.11 |  -0.81 |

## Correlation of the market-neutral survivors (daily net)

|                             |   Funding contrarian XS (#7b) |   Taker-flow follow XS (#14) |   XS momentum L/S (#17) |
|:----------------------------|------------------------------:|-----------------------------:|------------------------:|
| Funding contrarian XS (#7b) |                          1    |                         0.21 |                    0    |
| Taker-flow follow XS (#14)  |                          0.21 |                         1    |                    0.43 |
| XS momentum L/S (#17)       |                          0    |                         0.43 |                    1    |
