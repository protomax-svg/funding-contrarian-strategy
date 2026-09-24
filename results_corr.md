# Price correlation to choose longs and shorts (top-100, all crypto perps)

60d daily-return correlation, known at the close. 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.

| variant                             |   IS |   OOS |   OOS@15bps |   OOS +1d |   OOS total % |   ann vol % |   maxDD |   worst month % |   OOS price %/yr |   OOS funding %/yr |
|:------------------------------------|-----:|------:|------------:|----------:|--------------:|------------:|--------:|----------------:|-----------------:|-------------------:|
| base top-100 (live)                 | 2.12 |  1.1  |        0.87 |      0.46 |         123.3 |        26.2 |  -0.27  |           -11.5 |            -21.4 |               63   |
| 1) correlation pairs                | 2.36 |  0.93 |        0.67 |      0.39 |          94.9 |        25.5 |  -0.26  |           -11.3 |            -23.3 |               60.8 |
| 2) skip loners (low corr to market) | 1.81 |  0.95 |        0.61 |      1.66 |         106.4 |        27   |  -0.537 |           -25.7 |              3.8 |               39.9 |
| 3) beta-neutral legs                | 2.07 |  1.02 |        0.77 |      0.35 |         108.2 |        25.9 |  -0.29  |           -11.6 |            -23.7 |               63.1 |
| 1+3) corr pairs + beta-neutral      | 2.27 |  0.85 |        0.57 |      0.28 |          80.9 |        25.1 |  -0.273 |            -9.4 |            -25   |               60.2 |
| 2+3) skip loners + beta-neutral     | 1.83 |  1.04 |        0.67 |      1.62 |         115.3 |        25.6 |  -0.508 |           -19.3 |              4   |               40.9 |
