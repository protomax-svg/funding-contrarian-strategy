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

## Group-matched pairs (`pairs_test.py` → `results_pairs.md`)

The same signal, but inside every group #longs == #shorts (sector labels, or price clusters refit every 30 days).

| Variant | OOS Sharpe | at 15 bps | +1 day | Max DD |
|---|---|---|---|---|
| Base (fronttest) | **0.93** | **0.51** | **0.66** | −61% |
| Sector pairs, N=5 | 0.47 | −0.02 | −0.20 | −48% |
| Price-cluster pairs, N=5 | 0.47 | 0.05 | 0.43 | −44% |
| Price-cluster pairs, N=6 | 0.29 | −0.15 | 0.19 | −34% |

Pairing cuts the drawdown a little and the edge about in half, and the edge no longer survives costs or delay.
Part of the edge is *between* groups (whole sectors get crowded at once), which pairing removes. The fronttest stays on the base rule.

## Regime study (`regime.py` → `results_regime.md`)

States known at close t, trailing-365d percentiles, filter chosen on 2020-23, read on 2024-26.

| Filter | OOS Sharpe | Max DD | Time in market |
|---|---|---|---|
| none (base) | 0.93 | −61% | 100% |
| off when BTC ATR is in its low third | 1.07 | −38% | 62% |
| off when BTC is far above its 200d average (top third) | 1.54 | −52% | 81% |
| off when the strategy's own 60d return is in its low third | 1.16 | −43% | 75% |
| vol target 15%/yr (30d) | 1.26 | −38% | avg 0.81x |
| walk-forward choice among 25 filters | 1.07 | −47% | – |

The strategy earns ~0 in calm markets (low ATR) and loses in euphoric BTC rallies (high-funding coins keep squeezing).
Combinations reach OOS 1.7, but the pieces were chosen after seeing OOS consistency, so treat that as optimistic.
Per-coin ATR sizing or excluding the most volatile coins changes little (OOS 0.98-0.99).

## Jev model pilot (`jev_pilot.py` → `results_jev.txt`)

190 random days from 2024-26, anonymised state (no dates or coin names), 200 requests.
Jev's "profitable next week" probability had a **negative** rank correlation with the real next-7-day result
(−0.18, 90% CI −0.29 to −0.05); its exposure score had none (0.00). Its answers stayed near a coin flip (0.35-0.62)
and correlated 0.58 with the simple ATR/trend rule. Not good enough to spend the 1,000-request budget.

## BTC Risk Index (private API) as a filter (`risk_test.py` → `results_risk.md`)

Tested 2022-07 → 2026-08: pause on zone 2 / zone ≥1 / index > 0.65-0.75, at the daily rebalance and intraday.
None helped reliably. Zone-2 days were good in 2022-23 and bad in 2024-26 (the sign flips); pausing above 0.70 lowered
Sharpe in both periods (−0.23 → −0.42 and 0.93 → 0.87). The strategy is market-neutral and earns *more* in wild markets,
so a directional risk gauge removes good days. Not used. Needs the private API; its data and doc are git-ignored.

## All Binance crypto perps (`alltest.py` → `results_all.md`) — this is what the fronttest now runs

676 USDT-M crypto perps incl. delisted (stocks/commodities/index perps excluded), point-in-time top-N by 30d volume,
zero-volume (delisted) bars excluded. The hand-picked 50-coin list had hindsight bias: on the full list the
"combination" and the ATR filter no longer beat the plain rule.

| Top-N, plain rule | 2020-23 | 2024-26 | 2024-26 total | Max DD |
|---|---|---|---|---|
| 30 | 1.92 | 0.84 | +142% | −55% |
| 50 | 1.88 | 0.71 | +79% | −35% |
| **100 (live)** | **2.12** | **1.10** | **+123%** | **−27%** |

Top-100 by year: 2020 +87%, 2021 +146%, 2022 +13%, 2023 +8%, 2024 +35%, 2025 +41%, 2026 (Jan-Aug) +18%.
2024-26 split: price −21%/yr, funding received +63%/yr, costs −6%/yr. It is mostly a funding harvest on small
high-funding coins (spread out: top-5 coins = 12% of the funding, 10 best days = 6%). Main risk: short squeezes on small caps.
~41 positions on average, so with $1,000 each is ~$25 (fine for paper; check Binance minimum order sizes before real money).
Live and backtest pick identical books on 2026-08-20 and 2026-08-30 (41/41).

## Files

| File | What |
|---|---|
| `fetch_data.py` | Downloads the data (re-runnable). `data/INVENTORY.md` = data quality. |
| `lab.py` | Backtest engine + self-check (`python lab.py`). |
| `daily.py` → `results_daily.md` | Daily ideas, as posted + grids. |
| `intraday.py` → `results_intraday.md` | #2, #13, #5, #6. |
| `robust.py` → `results_robust.md` | Robustness battery + by-year table. |
| `funding_deep.py` → `results_funding.md` | Deep-dive on the gem. |
| `pairs_test.py` → `results_pairs.md` | Same signal with group-matched long/short pairs. |
| `regime.py` → `results_regime.md` | Market-state filters, ATR, vol targeting, walk-forward. |
| `jev_pilot.py` → `results_jev.txt`, `jev_pilot.jsonl` | Jev pilot (needs `JEV_API_KEY` in `.env`). |

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

`fronttest.py` (backend) + `fronttest.html` (UI) trade #7b on live Binance data with $1,000 of fake money.
Data feed: one websocket (`wss://fstream.binance.com/market/ws/!markPrice@arr`) gives mark prices and funding
times for all perps, with 0 REST weight. REST is used only for (a) the daily signal at 00:05 UTC (~80 weight), (b) one
`/fapi/v1/fundingRate` call per held coin right after each settlement (separate 500/5min limit), and (c) mark prices while the
websocket is down. The UI header shows the feed state, our REST calls in the last hour, and the IP-wide weight Binance reports.
Same rule, same code path as the backtest (`lab.universe` + `lab.xs_rank_weights`). It picks the same coins as the
backtest on 2026-08-20 and 2026-08-30. Rebalances daily at 00:05 UTC. A fresh DB waits for the next 00:05 UTC before its first trade. It charges 7 bps/side and applies every real funding
settlement. State is kept in `fronttest.db` (SQLite), so a restart continues where it stopped.

```bash
.venv/bin/python fronttest.py --selfcheck                    # money-logic asserts
setsid nohup .venv/bin/python fronttest.py > fronttest.log 2>&1 < /dev/null &
# UI: http://127.0.0.1:8770      stop: pkill -f fronttest.py
```

Settings via env: `FRONTTEST_DB` (default `./fronttest.db`), `FRONTTEST_HOST` (default `127.0.0.1`), `FRONTTEST_PORT` (default `8770`).

**Statistics page:** `http://127.0.0.1:8770/stats` — every coin ever traded (longs/shorts, days held, price vs funding vs fees,
win rate, worst/best move while held, market state at entry), every round trip, long vs short, daily P&L, live vs backtest,
and a check that price + funding − fees equals the equity change. Logic in `stats.py` (`python stats.py` = self-check).

### What the DB holds (`fronttest.db`, SQLite)

| Table | Content |
|---|---|
| `kv` | cash, positions, entry prices, open times, rule settings + candidate list, start time |
| `signals` | full daily ranking: every top-30 coin, its 7d funding, its weight |
| `rebalances` | time, signal day, equity, fees, target weights |
| `trades` | every paper fill: qty, price, fee |
| `funding` | every funding settlement: rate, mark, payment |
| `equity` | equity + long/short notional every minute |
| `errors` | API or runtime errors |
| `features` | market state of every top-100 coin at each rebalance: volume rank, 30d volume, ATR14, 30d vol, 1d/7d return, 7d funding, predicted funding, basis vs spot |
| `marks` | mark price of every held coin every 15 min (worst/best move per trade) |

### Move to a server

```bash
.venv/bin/python fronttest.py --backup fronttest-copy.db     # safe copy while it runs
pkill -f fronttest.py                                        # stop locally (so only one copy trades)
scp fronttest-copy.db server:/opt/reddit-ideas/fronttest.db
# on the server: clone the repo, create .venv, install requirements, then use deploy/fronttest.service
```

It continues from the same state. Funding paid while it was stopped is booked on the next start.
The UI has no login, so keep `FRONTTEST_HOST=127.0.0.1` on a server and reach it with `ssh -L 8770:127.0.0.1:8770 server`.
**Market filter (now shadow only, since the full-universe test).** Was live: flat when BTC's 14d ATR% is in the low third of its last 365 days (`regime.py`: OOS Sharpe 0.93 → 1.07,
max DD −61% → −38%, 31 separate off-episodes). Shadow (logged, not applied): BTC close/SMA200 in the top third of its last year;
its backtest benefit comes almost entirely from one episode (the Oct 2023 – Apr 2024 ETF rally), so it has to earn its place live.
Both values are in the `filters` table and match the backtest values exactly on 2025-03-10, 2026-08-20 and 2026-08-30.

**Fills (since 2026-09-26):** buy at the real best ask, sell at the real best bid (`/fapi/v1/ticker/bookTicker`, weight 5 per
rebalance), plus the 5 bps taker fee. Measured on a real rebalance: spread 3.0 bps + fee 5 bps = 8 bps, vs 7 bps assumed in the
backtest. Earlier trades were filled at the mark price and stamped with the rebalance start time (both fixed).

**Audit:** `python audit.py fronttest.db` re-derives everything from Binance with independent code (no imports from the
fronttest): cash and positions from the trade log, every real funding event while a position was open (missing / extra /
double / wrong amount), every fill vs the real 1-minute range, look-ahead (signal day, saved close, 7d funding from raw events),
and that positions match the signal. It caught 5 of 5 deliberate corruptions of a test DB.

Differences from the backtest: rebalances to target from actual holdings (includes drift, so turnover is a bit higher);
fills at mark price with flat 7 bps (no order book). The first rebalance happened mid-day (2026-09-23 17:41 UTC) on the 09-22 signal.
