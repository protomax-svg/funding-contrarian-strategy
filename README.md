# r/algotrading ideas, tested on crypto

18 ideas harvested from r/algotrading (list with source links: `reddit_ideas_raw.md`).
12 were testable with free data. Tested on Binance USDT-M perps, 50 coins incl. dead ones
(LUNA, SRM, MATIC, EOS, FTT), 1h bars 2020-01 → 2026-08, real 8h funding.

**Rules for every test:** signal on closed bar, fill next bar · 7 bps/side (stress 15) ·
real funding paid/received · point-in-time top-30 by volume · parameters as posted, then a grid ·
IS 2020-2023, OOS 2024-01 → 2026-08.
Survivors also got: +1 day delay, 6m/1m walk-forward, time-shift placebo, alpha vs market, universe size.

## Verdict

| # | Idea | Verdict | Key numbers (OOS = 2024-26) |
|---|---|---|---|
| 7b | **Funding contrarian, cross-sectional** (long lowest 7d funding, short highest) | **PASS — the gem** | OOS Sharpe 0.93 · 15 bps 0.51 · +1d delay 0.66 · walk-fwd 0.86 · placebo p=0.00 · alpha t=3.1 · beta≈0 · works top10/20/50 · uncorrelated with momentum (0.00). **But** −61% drawdown over 2.5 y (2021-09 → 2024-03: long LUNA before collapse, short SHIB/PEPE pumps). |
| 4 | RSI(5) > 70, hold while above | PARTIAL | OOS 0.85, placebo p=0.00, alpha t=2.7. **Dies with 1 day delay (0.12).** Lost in 2022 and 2025. Execution-sensitive. |
| 1 | Z-score trend (EMA/σ 65) on BTC | Risk filter, no alpha | OOS 0.69 vs BTC hold 0.58; max DD −38% vs −79%. Alpha vs BTC negative (t −1.1). Use it to cut drawdown, not to make money. |
| 7a | Funding cash-and-carry | Real, thin | BTC always-carry 15%/y (IS) → 7%/y (OOS) per $ notional, before costs. Chasing high-funding alts: ~0-2%/y after costs. Reddit's "compressed" claim confirmed. |
| 12 | IBS + range dip buy | Weak | OOS 0.52 but placebo p=0.07, alpha t=1.0. Not significant. |
| 3 | SMA50/EMA7 + RSI2>ADX2 | BTC-only, fragile | BTC as posted OOS 1.14; top-30 0.24; IS-best grid point → OOS −0.01. |
| 14 | Order-flow proxy (taker-buy share) | Decayed | IS 2.28 → OOS 0.40 → 0.01 at 15 bps. |
| 17 | Cross-sectional momentum | Decayed | IS 1.45 → OOS 0.12. Top-2 long-only OOS 0.09. |
| 16 | MACD / EMA5-13 | Beta only | top-30 OOS ≈ 0; BTC works only as a long filter. |
| 2 | Bollinger + VWAP breakout, BTC 1h | **FAIL** | 0 of 81 variants positive OOS at 7 bps. After the post date: loses even at the post's own 2.5 bps fee. |
| 5 | Kalman BTC/ETH pairs | **FAIL** | Post's rolling-z variant: OOS −0.7 to 0.0. |
| 6 | Rolling cointegration pairs | **FAIL** | −19%/y. Confirms the Reddit author's own negative result. |
| 13 | Hour-of-day / session effect | **FAIL** | IS hour ranking does not persist (rank corr 0.12 / −0.25). |

Not testable with free data: liquidation heatmaps (#10), L2 order-book imbalance (#14 full),
quarterly basis reversal (#9), staking yields (#8). Difficulty ribbon (#18): only ~2 cycles in range.

## The gem, in detail (`results_funding.md`)

- About 60% of the profit is price (low-funding coins beat high-funding coins), 40% is funding received on the short leg. OOS: price +18%/y, funding +9%/y.
- Not a disguised reversal trade: 7d-reversal alone loses (−61%/y); removing the 7d-return part keeps the edge (OOS 0.98).
- Terciles (q=0.33) look better than quintiles (OOS 1.18, DD −48%) — chosen after seeing results, so treat as a hint.
- 20% vol-targeting: Sharpe 1.19, OOS 1.29, DD −47%. Still a big drawdown.
- Needed before any money: per-coin size cap, a stop on short-leg squeezes, and live paper trading.

## Files

| File | What |
|---|---|
| `fetch_data.py` | Downloads the data (re-runnable). `data/INVENTORY.md` = data quality. |
| `lab.py` | Backtest engine + self-check (`python lab.py`). |
| `daily.py` → `results_daily.md` | Daily ideas, as posted + grids. |
| `intraday.py` → `results_intraday.md` | #2, #13, #5, #6. |
| `robust.py` → `results_robust.md` | Robustness battery + by-year table. |
| `funding_deep.py` → `results_funding.md` | Deep-dive on the gem. |

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python fetch_data.py          # ~270 MB into data/ (not in git)
.venv/bin/python lab.py                 # engine self-check
.venv/bin/python daily.py && .venv/bin/python intraday.py && .venv/bin/python robust.py && .venv/bin/python funding_deep.py
```

## Limits

- Costs are flat bps. Small alts have wider spreads in stress, which hurts #7b's short leg most.
- 2.7 years of OOS. One bear (2022) is in IS only.
- Many ideas and variants were tried. A single OOS Sharpe near 0.9 is good, not proof.

## Fronttest (paper trading, live)

`fronttest.py` (backend) + `fronttest.html` (UI) trade #7b on live Binance data with $10,000 of fake money.
Same rule, same code path as the backtest (`lab.universe` + `lab.xs_rank_weights`). It picks the same coins as the
backtest on 2026-08-20 and 2026-08-30. Rebalances daily at 00:05 UTC. It charges 7 bps/side and applies every real funding
settlement. State is kept in `fronttest.db` (SQLite), so a restart continues where it stopped.

```bash
.venv/bin/python fronttest.py --selfcheck                    # money-logic asserts
setsid nohup .venv/bin/python fronttest.py > fronttest.log 2>&1 < /dev/null &
# UI: http://127.0.0.1:8770      stop: pkill -f fronttest.py
```

Settings via env: `FRONTTEST_DB` (default `./fronttest.db`), `FRONTTEST_HOST` (default `127.0.0.1`), `FRONTTEST_PORT` (default `8770`).

### What the DB holds (`fronttest.db`, SQLite)

| Table | Content |
|---|---|
| `kv` | cash, positions, entry prices, open times, rule settings + candidate list, start time |
| `signals` | full daily ranking: every top-30 coin, its 7d funding, its weight |
| `rebalances` | time, signal day, equity, fees, target weights |
| `trades` | every paper fill: qty, price, fee |
| `funding` | every funding settlement: rate, mark, payment |
| `equity` | equity + long/short notional every 5 min |
| `errors` | API or runtime errors |

### Move to a server

```bash
.venv/bin/python fronttest.py --backup fronttest-copy.db     # safe copy while it runs
pkill -f fronttest.py                                        # stop locally (so only one copy trades)
scp fronttest-copy.db server:/opt/reddit-ideas/fronttest.db
# on the server: clone the repo, create .venv, install requirements, then use deploy/fronttest.service
```

It continues from the same state. Funding paid while it was stopped is booked on the next start.
The UI has no login, so keep `FRONTTEST_HOST=127.0.0.1` on a server and reach it with `ssh -L 8770:127.0.0.1:8770 server`.
Differences from the backtest: rebalances to target from actual holdings (includes drift, so turnover is a bit higher);
fills at mark price with flat 7 bps (no order book). The first rebalance happened mid-day (2026-09-23 17:41 UTC) on the 09-22 signal.
