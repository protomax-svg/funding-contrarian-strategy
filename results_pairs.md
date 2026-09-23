# Funding contrarian with group-matched pairs

In every group: #longs == #shorts, equal size. 7 bps/side, real funding, top-30 universe, IS 2020-2023, OOS 2024-01..2026-08.

| variant                                                    |   Sharpe_all |   IS |   OOS |   OOS@15bps |   OOS +1d |   ann_ret |   ann_vol |   maxDD | DD_period                |   worst_1coin_day |   OOS_price |   OOS_funding |   avg_pairs_long |
|:-----------------------------------------------------------|-------------:|-----:|------:|------------:|----------:|----------:|----------:|--------:|:-------------------------|------------------:|------------:|--------------:|-----------------:|
| base: top/bottom 20%, no pairing (what the fronttest runs) |         1.19 | 1.35 |  0.93 |        0.51 |      0.66 |     0.33  |     0.276 |  -0.608 | 2021-09-03 -> 2024-03-14 |            -0.071 |       0.184 |         0.092 |              6.6 |
| A) sector pairs, N=5                                       |         0.7  | 0.83 |  0.47 |       -0.02 |     -0.2  |     0.179 |     0.255 |  -0.476 | 2021-10-18 -> 2024-12-06 |            -0.099 |       0.08  |         0.095 |              5   |
| A) sector pairs, N=6                                       |         0.51 | 0.58 |  0.4  |       -0.14 |      0.01 |     0.115 |     0.224 |  -0.496 | 2021-09-05 -> 2024-12-05 |            -0.083 |       0.067 |         0.084 |              5.9 |
| B) price-cluster pairs, N=5                                |         1.22 | 1.73 |  0.47 |        0.05 |      0.43 |     0.29  |     0.237 |  -0.436 | 2023-11-26 -> 2024-03-20 |            -0.072 |       0.111 |         0.077 |              5   |
| B) price-cluster pairs, N=6                                |         1.08 | 1.6  |  0.29 |       -0.15 |      0.19 |     0.228 |     0.211 |  -0.342 | 2023-12-13 -> 2024-03-20 |            -0.06  |       0.07  |         0.068 |              5.9 |

## Sharpe by year

|               |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:--------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| base (tested) |   2.51 |   2.75 |  -0.84 |   0.07 |   0.26 |   0.99 |   2.61 |
| sector N=5    |   1.72 |   1.71 |  -0.75 |   0.78 |  -0.94 |   0.73 |   2.94 |
| sector N=6    |   1.62 |   1.46 |  -1.02 |   0.31 |  -0.94 |   0.83 |   2.5  |
| cluster N=5   |   0.31 |   4.03 |   1.18 |  -0.28 |  -0.25 |   0.45 |   1.92 |
| cluster N=6   |   0.11 |   4.02 |   0.44 |   0.06 |  -0.36 |   0.24 |   1.68 |

## Correlation of daily returns

|               |   base (tested) |   sector N=5 |   sector N=6 |   cluster N=5 |   cluster N=6 |
|:--------------|----------------:|-------------:|-------------:|--------------:|--------------:|
| base (tested) |            1    |         0.64 |         0.65 |          0.6  |          0.61 |
| sector N=5    |            0.64 |         1    |         0.94 |          0.51 |          0.49 |
| sector N=6    |            0.65 |         0.94 |         1    |          0.53 |          0.52 |
| cluster N=5   |            0.6  |         0.51 |         0.53 |          1    |          0.94 |
| cluster N=6   |            0.61 |         0.49 |         0.52 |          0.94 |          1    |

## Sector version: where the pairs are (share of pair-days)

|                 |   share |
|:----------------|--------:|
| majors/payments |   0.382 |
| L1              |   0.363 |
| DeFi/oracle     |   0.098 |
| gaming/media    |   0.064 |
| meme            |   0.046 |
| infra/other     |   0.032 |
| L2              |   0.015 |

Sector labels: **majors/payments**: BTC ETH BNB XRP LTC BCH ETC XLM TRX EOS; **L1**: SOL ADA AVAX DOT ATOM NEAR ALGO XTZ FTM APT SUI SEI INJ TIA WAVES LUNA; **L2**: MATIC POL ARB OP; **DeFi/oracle**: UNI AAVE SUSHI CRV COMP SNX 1INCH SRM LINK; **meme**: DOGE 1000SHIB 1000PEPE; **gaming/media**: AXS SAND MANA THETA; **infra/other**: FIL VET WLD FTT
