# Mechanical improvements (existing 50-coin data)

One change per row vs base. 7 bps/side, real funding. IS 2020-2023, OOS 2024-01..2026-08. ~12 variants tried: treat gains under ~0.15 Sharpe as noise.

| variant                                    | ATR filter   |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS ann |   maxDD |   turnover/yr |   cost/yr |   net beta |
|:-------------------------------------------|:-------------|-----:|------:|------------:|----------:|----------:|--------:|--------------:|----------:|-----------:|
| base (7d funding, top/bottom 20%)          | no           | 1.33 |  0.9  |        0.48 |      0.65 |     0.192 |  -0.598 |          99.3 |     0.069 |       0.02 |
| base (7d funding, top/bottom 20%)          | yes          | 1.51 |  1.03 |        0.64 |      0.8  |     0.191 |  -0.366 |          76.8 |     0.054 |       0.03 |
| buffer: enter 20%, exit 35%                | no           | 1.44 |  1.17 |        0.8  |      1.03 |     0.213 |  -0.446 |          73.8 |     0.052 |       0.01 |
| buffer: enter 20%, exit 35%                | yes          | 1.33 |  1.27 |        0.9  |      1.07 |     0.2   |  -0.371 |          62.9 |     0.044 |       0.02 |
| buffer: enter 20%, exit 50%                | no           | 1.47 |  0.97 |        0.67 |      0.82 |     0.147 |  -0.42  |          49.3 |     0.034 |       0.01 |
| buffer: enter 20%, exit 50%                | yes          | 1.32 |  1.09 |        0.74 |      0.97 |     0.143 |  -0.36  |          48.5 |     0.034 |       0.02 |
| rank-weighted (all coins)                  | no           | 1.45 |  1.05 |        0.57 |      0.87 |     0.163 |  -0.488 |          81.8 |     0.057 |       0.01 |
| rank-weighted (all coins)                  | yes          | 1.45 |  1.14 |        0.68 |      0.97 |     0.154 |  -0.369 |          67.4 |     0.047 |       0.02 |
| beta-neutral legs                          | no           | 1.38 |  1.1  |        0.61 |      0.82 |     0.221 |  -0.538 |         108.5 |     0.076 |       0.02 |
| beta-neutral legs                          | yes          | 1.58 |  1.14 |        0.71 |      0.89 |     0.203 |  -0.286 |          82.1 |     0.057 |       0.02 |
| signal: funding z-score vs own 90d         | no           | 0.74 |  0.64 |        0.09 |      0.35 |     0.127 |  -0.617 |         118.1 |     0.083 |       0.03 |
| signal: funding z-score vs own 90d         | yes          | 1.3  |  0.97 |        0.46 |      0.29 |     0.161 |  -0.306 |          87   |     0.061 |       0.03 |
| signal: raw + z-score (avg rank)           | no           | 1    |  0.82 |        0.18 |      0.52 |     0.165 |  -0.747 |         143.7 |     0.101 |       0.03 |
| signal: raw + z-score (avg rank)           | yes          | 1.19 |  1.1  |        0.52 |      0.68 |     0.188 |  -0.536 |         102.7 |     0.072 |       0.03 |
| signal: horizons 3+7+14 (avg rank)         | no           | 1.28 |  0.98 |        0.48 |      0.94 |     0.206 |  -0.56  |         115.1 |     0.081 |       0.01 |
| signal: horizons 3+7+14 (avg rank)         | yes          | 1.31 |  1.11 |        0.66 |      1.16 |     0.201 |  -0.379 |          85.1 |     0.06  |       0.02 |
| signal: + 28d momentum (avg rank)          | no           | 2.01 |  0.73 |        0.16 |      0.28 |     0.158 |  -0.268 |         143.8 |     0.101 |      -0    |
| signal: + 28d momentum (avg rank)          | yes          | 1.86 |  0.76 |        0.26 |      0.63 |     0.14  |  -0.176 |         101.2 |     0.071 |       0.01 |
| universe: min age 120d (skip new listings) | no           | 0.94 |  1.02 |        0.6  |      0.69 |     0.216 |  -0.619 |          97.9 |     0.069 |      -0    |
| universe: min age 120d (skip new listings) | yes          | 1.07 |  1.09 |        0.7  |      0.8  |     0.201 |  -0.441 |          75   |     0.052 |       0.01 |
| universe: top-40                           | no           | 1.47 |  1.66 |        1.18 |      1.01 |     0.296 |  -0.568 |          97.5 |     0.068 |       0.02 |
| universe: top-40                           | yes          | 1.59 |  1.28 |        0.83 |      0.77 |     0.198 |  -0.385 |          75.5 |     0.053 |       0.02 |
| buffer 20/35 + beta-neutral                | no           | 1.37 |  1.38 |        0.98 |      1.18 |     0.241 |  -0.364 |          77   |     0.054 |       0.01 |
| buffer 20/35 + beta-neutral                | yes          | 1.29 |  1.35 |        0.95 |      1.07 |     0.208 |  -0.303 |          64.8 |     0.045 |       0.02 |

## Ideas from the literature search (all with the live ATR filter)

| variant                                          | ATR filter   |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS ann |   maxDD |   turnover/yr |   cost/yr |   net beta |
|:-------------------------------------------------|:-------------|-----:|------:|------------:|----------:|----------:|--------:|--------------:|----------:|-----------:|
| base                                             | yes          | 1.51 |  1.03 |        0.64 |      0.8  |     0.191 |  -0.366 |          76.8 |     0.054 |       0.03 |
| base + stop 30% / 7d block                       | yes          | 1.34 |  0.98 |        0.59 |      0.74 |     0.187 |  -0.431 |          82.5 |     0.058 |       0.01 |
| base + stop 50% / 7d block                       | yes          | 1.68 |  1.07 |        0.68 |      0.92 |     0.2   |  -0.321 |          78.6 |     0.055 |       0.02 |
| base + no short if XS funding z > 2.5            | yes          | 1.49 |  1.2  |        0.8  |      0.86 |     0.222 |  -0.369 |          78.4 |     0.055 |       0.03 |
| base + no short if 7d return in top 20%          | yes          | 1.43 |  1.4  |        0.87 |      1.13 |     0.259 |  -0.343 |         103.4 |     0.072 |       0.03 |
| base + no long if 7d return in bottom 20%        | yes          | 1.49 |  0.93 |        0.44 |      0.27 |     0.184 |  -0.373 |         104.9 |     0.073 |      -0.01 |
| buffer+beta                                      | yes          | 1.29 |  1.35 |        0.95 |      1.07 |     0.208 |  -0.303 |          64.8 |     0.045 |       0.02 |
| buffer+beta + stop 30% / 7d block                | yes          | 1.28 |  1.3  |        0.91 |      1.07 |     0.211 |  -0.287 |          69.9 |     0.049 |       0.01 |
| buffer+beta + stop 50% / 7d block                | yes          | 1.53 |  1.29 |        0.9  |      1.01 |     0.201 |  -0.26  |          66.3 |     0.046 |       0.02 |
| buffer+beta + no short if XS funding z > 2.5     | yes          | 1.26 |  1.44 |        1.05 |      1.1  |     0.223 |  -0.316 |          66   |     0.046 |       0.02 |
| buffer+beta + no short if 7d return in top 20%   | yes          | 1.3  |  1.61 |        1.1  |      1.29 |     0.253 |  -0.266 |          87.2 |     0.061 |       0.02 |
| buffer+beta + no long if 7d return in bottom 20% | yes          | 1.39 |  1.15 |        0.63 |      0.53 |     0.185 |  -0.257 |          89.1 |     0.062 |      -0    |
