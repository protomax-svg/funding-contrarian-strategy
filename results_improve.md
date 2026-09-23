# Mechanical improvements (existing 50-coin data)

One change per row vs base. 7 bps/side, real funding. IS 2020-2023, OOS 2024-01..2026-08. ~12 variants tried: treat gains under ~0.15 Sharpe as noise.

| variant                                    | ATR filter   |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS ann |   maxDD |   turnover/yr |   cost/yr |   net beta |
|:-------------------------------------------|:-------------|-----:|------:|------------:|----------:|----------:|--------:|--------------:|----------:|-----------:|
| base (7d funding, top/bottom 20%)          | no           | 1.31 |  0.93 |        0.51 |      0.66 |     0.198 |  -0.608 |          99.5 |     0.07  |       0.02 |
| base (7d funding, top/bottom 20%)          | yes          | 1.49 |  1.07 |        0.69 |      0.81 |     0.2   |  -0.378 |          76.9 |     0.054 |       0.03 |
| buffer: enter 20%, exit 35%                | no           | 1.44 |  1.19 |        0.82 |      1.03 |     0.216 |  -0.443 |          73.5 |     0.051 |       0.01 |
| buffer: enter 20%, exit 35%                | yes          | 1.33 |  1.28 |        0.9  |      1.08 |     0.201 |  -0.368 |          62.6 |     0.044 |       0.02 |
| buffer: enter 20%, exit 50%                | no           | 1.48 |  0.92 |        0.63 |      0.77 |     0.14  |  -0.417 |          49.4 |     0.035 |       0.01 |
| buffer: enter 20%, exit 50%                | yes          | 1.32 |  1.04 |        0.7  |      0.93 |     0.136 |  -0.359 |          48.5 |     0.034 |       0.02 |
| rank-weighted (all coins)                  | no           | 1.45 |  1.07 |        0.6  |      0.89 |     0.167 |  -0.487 |          81.8 |     0.057 |       0.01 |
| rank-weighted (all coins)                  | yes          | 1.45 |  1.17 |        0.71 |      1    |     0.158 |  -0.366 |          67.4 |     0.047 |       0.02 |
| beta-neutral legs                          | no           | 1.37 |  1.12 |        0.63 |      0.83 |     0.224 |  -0.54  |         108.7 |     0.076 |       0.02 |
| beta-neutral legs                          | yes          | 1.58 |  1.19 |        0.76 |      0.9  |     0.213 |  -0.286 |          82.2 |     0.058 |       0.02 |
| signal: funding z-score vs own 90d         | no           | 0.72 |  0.66 |        0.11 |      0.37 |     0.129 |  -0.626 |         118.4 |     0.083 |       0.03 |
| signal: funding z-score vs own 90d         | yes          | 1.28 |  0.98 |        0.48 |      0.33 |     0.164 |  -0.319 |          87.1 |     0.061 |       0.03 |
| signal: raw + z-score (avg rank)           | no           | 0.98 |  0.9  |        0.26 |      0.56 |     0.181 |  -0.754 |         143.8 |     0.101 |       0.03 |
| signal: raw + z-score (avg rank)           | yes          | 1.18 |  1.12 |        0.54 |      0.74 |     0.192 |  -0.542 |         102.8 |     0.072 |       0.04 |
| signal: horizons 3+7+14 (avg rank)         | no           | 1.26 |  0.96 |        0.46 |      0.93 |     0.201 |  -0.568 |         115.6 |     0.081 |       0.01 |
| signal: horizons 3+7+14 (avg rank)         | yes          | 1.3  |  1.08 |        0.63 |      1.17 |     0.196 |  -0.386 |          85.4 |     0.06  |       0.02 |
| signal: + 28d momentum (avg rank)          | no           | 2.03 |  0.81 |        0.24 |      0.36 |     0.175 |  -0.25  |         143.7 |     0.101 |       0    |
| signal: + 28d momentum (avg rank)          | yes          | 1.88 |  0.86 |        0.35 |      0.72 |     0.158 |  -0.158 |         101.1 |     0.071 |       0.01 |
| universe: min age 120d (skip new listings) | no           | 0.92 |  1.05 |        0.63 |      0.71 |     0.222 |  -0.628 |          98.2 |     0.069 |      -0    |
| universe: min age 120d (skip new listings) | yes          | 1.05 |  1.14 |        0.75 |      0.81 |     0.21  |  -0.452 |          75.1 |     0.053 |       0.01 |
| universe: top-40                           | no           | 1.47 |  1.6  |        1.13 |      0.96 |     0.288 |  -0.569 |          97.7 |     0.068 |       0.02 |
| universe: top-40                           | yes          | 1.59 |  1.31 |        0.86 |      0.79 |     0.203 |  -0.384 |          75.5 |     0.053 |       0.02 |
| buffer 20/35 + beta-neutral                | no           | 1.39 |  1.4  |        1    |      1.18 |     0.244 |  -0.351 |          76.7 |     0.054 |       0.01 |
| buffer 20/35 + beta-neutral                | yes          | 1.31 |  1.35 |        0.96 |      1.07 |     0.208 |  -0.288 |          64.6 |     0.045 |       0.02 |

## Ideas from the literature search (all with the live ATR filter)

| variant                                          | ATR filter   |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS ann |   maxDD |   turnover/yr |   cost/yr |   net beta |
|:-------------------------------------------------|:-------------|-----:|------:|------------:|----------:|----------:|--------:|--------------:|----------:|-----------:|
| base                                             | yes          | 1.49 |  1.07 |        0.69 |      0.81 |     0.2   |  -0.378 |          76.9 |     0.054 |       0.03 |
| base + stop 30% / 7d block                       | yes          | 1.31 |  1.03 |        0.63 |      0.75 |     0.196 |  -0.445 |          82.6 |     0.058 |       0.01 |
| base + stop 50% / 7d block                       | yes          | 1.66 |  1.12 |        0.73 |      0.93 |     0.209 |  -0.333 |          78.7 |     0.055 |       0.02 |
| base + no short if XS funding z > 2.5            | yes          | 1.47 |  1.25 |        0.85 |      0.85 |     0.232 |  -0.381 |          78.6 |     0.055 |       0.03 |
| base + no short if 7d return in top 20%          | yes          | 1.41 |  1.47 |        0.93 |      1.14 |     0.27  |  -0.357 |         103.7 |     0.073 |       0.03 |
| base + no long if 7d return in bottom 20%        | yes          | 1.46 |  0.97 |        0.48 |      0.28 |     0.194 |  -0.389 |         105.1 |     0.074 |      -0.01 |
| buffer+beta                                      | yes          | 1.31 |  1.35 |        0.96 |      1.07 |     0.208 |  -0.288 |          64.6 |     0.045 |       0.02 |
| buffer+beta + stop 30% / 7d block                | yes          | 1.3  |  1.31 |        0.92 |      1.07 |     0.211 |  -0.273 |          69.7 |     0.049 |       0.01 |
| buffer+beta + stop 50% / 7d block                | yes          | 1.55 |  1.29 |        0.9  |      1.01 |     0.202 |  -0.243 |          66.1 |     0.046 |       0.02 |
| buffer+beta + no short if XS funding z > 2.5     | yes          | 1.28 |  1.45 |        1.06 |      1.09 |     0.225 |  -0.302 |          65.8 |     0.046 |       0.02 |
| buffer+beta + no short if 7d return in top 20%   | yes          | 1.3  |  1.62 |        1.11 |      1.31 |     0.255 |  -0.264 |          87.1 |     0.061 |       0.02 |
| buffer+beta + no long if 7d return in bottom 20% | yes          | 1.39 |  1.14 |        0.63 |      0.54 |     0.185 |  -0.256 |          88.9 |     0.062 |      -0    |
