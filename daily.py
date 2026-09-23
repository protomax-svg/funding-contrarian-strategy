"""Daily-bar Reddit ideas: #1 z-score trend, #3 RSI2>ADX2, #4 RSI5>70, #12 IBS dip, #16 MACD/EMA,
#17 cross-sectional momentum, #7 funding (carry + contrarian), #14 taker-flow proxy.

Every idea is run (a) exactly as posted, then (b) over a small grid so we see the whole
neighbourhood, not the best point. Parameters are picked on IS (2020-2023) only.
"""
import itertools
import sys

import numpy as np
import pandas as pd

import lab

COST = 7.0      # bps per side: 5 taker + 2 slippage. Stress run uses 15.
P = lab.load("1D")
U = lab.universe(P, top_n=30)
BTC = pd.DataFrame(False, index=U.index, columns=U.columns)
BTC["BTCUSDT"] = P["close"]["BTCUSDT"].notna()
out = []


def run(name, w, cost=COST, funding=True):
    bt = lab.backtest(w, P, cost, funding)
    r = lab.report(bt, "1D", name)
    return r, bt


def section(title, rows, grid_rows=None, note=""):
    out.append(f"\n## {title}\n")
    if note:
        out.append(note + "\n")
    out.append(pd.DataFrame(rows).to_markdown(index=False))
    if grid_rows:
        df, s = lab.grid_summary(grid_rows)
        out.append(f"\nGrid ({s['n_variants']} variants): median IS Sharpe {s['median_IS']}, "
                   f"median OOS Sharpe {s['median_OOS']}, share of variants with OOS>0: {s['pct_OOS_pos']}. "
                   f"IS-best `{s['IS_best']}`: IS {s['IS_best_IS']} -> OOS {s['IS_best_OOS']}.")
    print(title, "done", flush=True)


# ---------------- benchmarks ----------------
bench = [run("BTC buy&hold (perp, pays funding)", BTC.astype(float))[0],
         run("EW top-30 buy&hold, daily rebal", lab.ts_weights(U * 1.0, U))[0]]
section("Benchmarks", bench)

C, H, L = P["close"], P["high"], P["low"]


def both(name, sig):
    """Run a time-series long/flat signal on BTC alone and on the top-30 universe."""
    a = run(f"{name} | BTC", lab.ts_weights(sig, BTC))
    b = run(f"{name} | top30", lab.ts_weights(sig, U))
    return a, b


# ---------------- #1 z-score trend sentinel ----------------
def zsig(n, bull, bear):
    z = (C - lab.ema(C, n)) / C.rolling(n).std()
    return lab.hold(z > bull, z < bear)


rows, grid = [], []
for n, bull, bear in itertools.product([40, 65, 90], [0.0, 0.5, 1.0, 1.5], [-1.0, -0.5, 0.0]):
    a, b = both(f"z n={n} bull={bull} bear={bear}", zsig(n, bull, bear))
    grid.append(b[0])
    if (n, bull, bear) == (65, 0.5, 0.0):
        rows += [a[0], b[0]]
section("#1 Z-score trend sentinel (EMA/stdev 65)", rows, grid,
        "Thresholds were never disclosed, so the shown row is a neutral guess (bull 0.5, bear 0); grid is over top-30.")

# ---------------- #3 SMA50 / EMA7 / RSI2 > ADX2 ----------------
def s3(sma=50, e=7, n=2):
    r, a = lab.rsi(C, n), lab.adx(H, L, C, n)
    return lab.hold((C > C.rolling(sma).mean()) & (C > lab.ema(C, e)) & (r > a), r < a)


rows, grid = [], []
a, b = both("as posted (50/7/2)", s3())
rows += [a[0], b[0]]
for sma, e, n in itertools.product([40, 50, 60], [5, 7, 9], [2, 3]):
    grid.append(both(f"sma={sma} ema={e} n={n}", s3(sma, e, n))[1][0])
section("#3 SMA50 + EMA7 + RSI(2) vs ADX(2)", rows, grid)

# ---------------- #4 RSI5 > 70 ----------------
rows, grid = [], []
a, b = both("RSI5>70 as posted", (lab.rsi(C, 5) > 70).astype(float))
rows += [a[0], b[0]]
for n, t in itertools.product([4, 5, 6, 8], [60, 65, 70, 75]):
    grid.append(both(f"RSI{n}>{t}", (lab.rsi(C, n) > t).astype(float))[1][0])
section("#4 RSI(5) > 70 momentum", rows, grid)

# ---------------- #12 IBS + range dip ----------------
def s12(k=2.5, ibs_t=0.3, hh=10, rng=25):
    ibs = (C - L) / (H - L)
    band = H.rolling(hh).max() - k * (H.rolling(rng).mean() - L.rolling(rng).mean())
    return lab.hold((C < band) & (ibs < ibs_t), C > H.shift(1))


rows, grid = [], []
a, b = both("as posted (2.5, 0.3)", s12())
rows += [a[0], b[0]]
for k, t in itertools.product([1.5, 2.0, 2.5, 3.0], [0.2, 0.3, 0.4]):
    grid.append(both(f"k={k} ibs<{t}", s12(k, t))[1][0])
section("#12 IBS + range-contraction dip buy (equity rule on crypto)", rows, grid)

# ---------------- #16 MACD / EMA5-13 ----------------
rows, grid = [], []
macd = lab.ema(C, 12) - lab.ema(C, 26)
m_sig = (macd > lab.ema(macd, 9)).astype(float)
a, b = both("MACD(12,26,9) long/flat", m_sig)
rows += [a[0], b[0]]
e_sig = (lab.ema(C, 5) > lab.ema(C, 13)).astype(float)
a, b = both("EMA5>EMA13 long/flat", e_sig)
rows += [a[0], b[0]]
a, b = both("EMA5/13 long/short", 2 * e_sig - 1)
rows += [a[0], b[0]]
for f, s in itertools.product([3, 5, 8, 12, 20], [13, 26, 50, 100]):
    if f < s:
        grid.append(both(f"EMA{f}>{s}", (lab.ema(C, f) > lab.ema(C, s)).astype(float))[1][0])
section("#16 MACD / EMA crossover trend", rows, grid)

# ---------------- #17 cross-sectional momentum ----------------
rows, grid = [], []
ret7 = C / C.shift(7) - 1
# the SSRN rule from the thread: buy last week's single best coin, hold a week
top1 = lab.xs_rank_weights(ret7, U, q=1 / 30, long_only=True)
rows.append(run("best coin of last week, hold 1w (SSRN 3055498)", lab.every(top1, 7))[0])
rows.append(run("top-2 by 7d return, daily rebal (post)", lab.xs_rank_weights(ret7, U, q=2 / 30, long_only=True))[0])
for lb, hd, q in itertools.product([1, 3, 7, 14, 28, 56], [1, 7], [0.2]):
    sc = C / C.shift(lb) - 1
    grid.append(run(f"L/S lb={lb} hold={hd}", lab.every(lab.xs_rank_weights(sc, U, q), hd))[0])
rows += [g for g in grid if g["name"] in ("L/S lb=28 hold=7", "L/S lb=1 hold=1")]
section("#17 Cross-sectional momentum", rows, grid,
        "Long-only rows are total return (compare to EW top-30 benchmark). L/S = long top quintile, short bottom quintile, dollar-neutral.")

# ---------------- #7 funding ----------------
F = P["funding"]
rows = []
# (a) carry: short perp + long spot on coins whose trailing 3d funding is high; pnl = funding received - 4 legs of costs.
for thr_bps in [0, 1, 3]:   # trailing avg daily funding in bps (0.01%/8h = 3 bps/day)
    for top in [5, 10]:
        f3 = F.rolling(3).mean()
        sel = (f3 > thr_bps / 1e4) & U
        rk = f3.where(sel).rank(axis=1, ascending=False)
        pick = (rk <= top)
        w = pick.div(pick.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        w = lab.every(w, 7)                                # weekly rebalance to keep costs down
        pos = w.shift(1).fillna(0)
        fund = (pos * F).sum(axis=1)                        # short perp receives funding
        turn = (w - w.shift(1).fillna(0)).abs().sum(axis=1).shift(1).fillna(0)
        net = fund - turn * 2 * COST / 1e4                  # spot leg + perp leg
        bt = pd.DataFrame({"net": net, "gross": fund, "cost": turn * 2 * COST / 1e4, "fund": -fund,
                           "turn": turn, "gross_exp": pos.sum(axis=1)})
        rows.append(lab.report(bt, "1D", f"carry top{top} f3>{thr_bps}bps/d weekly"))
btc_c = pd.DataFrame({"net": F["BTCUSDT"], "gross": F["BTCUSDT"], "cost": 0.0, "fund": -F["BTCUSDT"],
                      "turn": 0.0, "gross_exp": 1.0})
rows.append(lab.report(btc_c, "1D", "carry BTC always (no costs)"))
section("#7a Funding cash-and-carry (delta-neutral; returns per $ of short notional)", rows, None,
        "Basis moves and spot-borrow ignored; capital needed is ~1.3-2x notional, so real return on capital is lower.")

rows, grid = [], []
for lb in [1, 3, 7, 14, 30]:
    sc = -F.rolling(lb).mean()                              # long low-funding, short high-funding
    grid.append(run(f"XS contrarian funding lb={lb}", lab.every(lab.xs_rank_weights(sc, U), 1))[0])
    grid.append(run(f"XS contrarian funding lb={lb} weekly", lab.every(lab.xs_rank_weights(sc, U), 7))[0])
fz = (F["BTCUSDT"] - F["BTCUSDT"].rolling(90).mean()) / F["BTCUSDT"].rolling(90).std()
for t in [1.0, 2.0]:
    sig = pd.DataFrame(0.0, index=U.index, columns=U.columns)
    sig["BTCUSDT"] = np.where(fz.rolling(3).mean() < -t, 1.0, np.where(fz.rolling(3).mean() > t, -1.0, 0.0))
    rows.append(run(f"BTC: long if funding z<-{t}, short if >{t}", sig)[0])
rows += grid
section("#7b Funding as a contrarian signal", rows, grid)

# ---------------- #14 taker-flow proxy (order-flow imbalance from klines) ----------------
rows, grid = [], []
imb = P["tbq"] / P["qv"] - 0.5
for lb, sign in itertools.product([1, 3, 7, 14], [1, -1]):
    sc = sign * imb.rolling(lb).mean()
    grid.append(run(f"XS taker imbalance lb={lb} {'follow' if sign > 0 else 'fade'}", lab.xs_rank_weights(sc, U))[0])
section("#14 Order-flow proxy: taker-buy share (daily, cross-sectional)", grid, grid,
        "True order-book imbalance needs L2 history (not free). This uses the taker-buy share inside each kline.")

open("results_daily.md", "w").write("# Daily-bar results\n\nCosts " + str(COST) +
                                    " bps/side, real funding, point-in-time top-30 universe. IS 2020-2023, OOS 2024-01..2026-08.\n"
                                    + "\n".join(out) + "\n")
print("wrote results_daily.md")
