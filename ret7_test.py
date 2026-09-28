"""Robustness battery for lab.drop_falling_longs (live since 2026-09-28): no long in the worst 20% of the long leg by 7d return.
Found on 2026-09-28 after looking at 2024-26, so the OOS numbers are optimistic. -> results_ret7.md"""
import sys
import numpy as np, pandas as pd, lab
from alltest import P, IS, OOS, F7
from improve import without
C, R = P["close"], P["ret"]
def sh(x): return round(lab.sharpe(x, 365), 2)
def run(w, cost=7.0, lag=0): return lab.backtest(w.shift(lag).fillna(0) if lag else w, P, cost)
def line(nm, w):
    b = run(w); o = b.net.loc[OOS]
    return dict(variant=nm, IS=sh(b.net.loc[IS]), OOS=sh(o), OOS15=sh(run(w, 15).net.loc[OOS]), OOS25=sh(run(w, 25).net.loc[OOS]),
                OOS_1d=sh(run(w, 7, 1).net.loc[OOS]), OOS_2d=sh(run(w, 7, 2).net.loc[OOS]),
                OOS_yr=round(o.mean()*365, 3), DD=round(lab.maxdd(b.net), 3), OOS_DD=round(lab.maxdd(o), 3), cost_yr=round(b.cost.mean()*365, 3))
def drop_leg(w, sig, q):
    return lab.drop_falling_longs(w, sig, q)


out = []
U = {n: lab.universe(P, n) for n in (30, 50, 100)}
W = {n: lab.xs_rank_weights(-F7, U[n]) for n in U}
w = W[100]
# 1 as found + other universes
for n in (100, 50, 30):
    out.append(line(f"top-{n} base", W[n]))
    out.append(line(f"top-{n} RULE lb7 q20 (in leg)", drop_leg(W[n], C / C.shift(7) - 1, 0.2)))
# 2 grid: lookback x cutoff (top-100)
grid = []
for lb in (3, 5, 7, 10, 14, 21, 30):
    rl = C / C.shift(lb) - 1
    for q in (0.1, 0.2, 0.3, 0.4):
        b = run(drop_leg(w, rl, q))
        grid.append(dict(lb=lb, q=q, IS=sh(b.net.loc[IS]), OOS=sh(b.net.loc[OOS])))
G = pd.DataFrame(grid)
# 3 other definitions
r7 = C / C.shift(7) - 1
out.append(line("rank over whole universe bottom 20% (improve.py style)", without(w, drop_long=r7.where(U[100]).rank(axis=1, pct=True) <= 0.2)))
for thr in (-0.10, -0.20, -0.30):
    out.append(line(f"absolute: ret7 < {thr:.0%}", without(w, drop_long=r7 < thr)))
vol = R.rolling(30).std() * np.sqrt(7)
out.append(line("vol-scaled: ret7/vol7 in leg bottom 20%", drop_leg(w, r7 / vol, 0.2)))
out.append(line("drop and keep cash (no re-weight)", w.where(~((r7.where(w > 0).rank(axis=1, pct=True) <= 0.2) & (w > 0)), 0.0)))
T = pd.DataFrame(out)
rule = drop_leg(w, r7, 0.2)
# 4 placebo: drop a random 20% of the long leg, 200 seeds
rng = np.random.default_rng(0); pl = []
for _ in range(200):
    rnd = pd.DataFrame(rng.random(w.shape), index=w.index, columns=w.columns)
    pl.append(lab.sharpe(run(drop_leg(w, rnd, 0.2)).net.loc[OOS], 365))
pl = np.array(pl); rs = lab.sharpe(run(rule).net.loc[OOS], 365)
# 5 by year + decomposition
bb, br = run(w), run(rule)
yr = pd.DataFrame({"base %": bb.net.groupby(bb.index.year).apply(lambda x: (1+x).prod()-1),
                   "rule %": br.net.groupby(br.index.year).apply(lambda x: (1+x).prod()-1)}).mul(100).round(1)
dec = pd.DataFrame({k: {"price/yr": b.gross.loc[OOS].mean()*365, "funding/yr": -b.fund.loc[OOS].mean()*365, "cost/yr": -b.cost.loc[OOS].mean()*365}
                    for k, b in (("base", bb), ("rule", br))}).round(3)
# 6 block bootstrap of daily difference (OOS and IS), 30-day blocks
def boot(d, n=2000, blk=30):
    d = d.values; k = len(d) // blk; m = []
    for _ in range(n):
        idx = (rng.integers(0, len(d) - blk, k)[:, None] + np.arange(blk)).ravel()
        m.append(d[idx].mean() * 365)
    return np.percentile(m, [5, 50, 95]).round(3), round(float((np.array(m) <= 0).mean()), 3)
diff = br.net - bb.net
bs = {per: boot(diff.loc[sl]) for per, sl in (("IS", IS), ("OOS", OOS))}
# 7 what happens to dropped coins: next 1/3/7-day return of dropped vs kept longs (price + funding)
m_drop = (r7.where(w > 0).rank(axis=1, pct=True) <= 0.2) & (w > 0); m_keep = (w > 0) & ~m_drop
ev = []
for h in (1, 3, 7):
    fwd = (C.shift(-h) / C - 1) - P["funding"].rolling(h).sum().shift(-h)
    for per, sl in (("IS", IS), ("OOS", OOS)):
        ev.append(dict(h=h, per=per, dropped_bps=round(fwd.where(m_drop).loc[sl].stack().mean()*1e4), kept_bps=round(fwd.where(m_keep).loc[sl].stack().mean()*1e4)))
# 8 walk-forward: every 6 months pick (lb,q) with the best trailing-2y Sharpe, or "off" if base is better
cands = [(lb, q) for lb in (3, 5, 7, 10, 14, 21, 30) for q in (0.1, 0.2, 0.3, 0.4)]
nets = {c: run(drop_leg(w, C / C.shift(c[0]) - 1, c[1])).net for c in cands}; nets["off"] = bb.net
wf = pd.Series(0.0, index=bb.net.index); picks = []
for st in pd.date_range("2022-01-01", "2026-07-01", freq="6MS", tz="UTC"):
    tr = slice(st - pd.DateOffset(years=2), st - pd.Timedelta("1ns")); te = slice(st, st + pd.DateOffset(months=6) - pd.Timedelta("1ns"))
    best = max(nets, key=lambda c: lab.sharpe(nets[c].loc[tr], 365)); picks.append((str(st.date()), best))
    wf.loc[te] = nets[best].loc[te]
with open(lab.D.parent / "results_ret7.md", "w") as f:
    f.write("# Rule: no long in the 20% of the long leg with the worst 7d return (top-100, all perps)\n\n")
    f.write("## Main table (Sharpe; OOS_1d/2d = trade 1/2 days late)\n\n" + T.to_markdown(index=False) + "\n\n")
    f.write("## Grid lookback x cutoff (top-100)\n\nIS:\n\n" + G.pivot(index="lb", columns="q", values="IS").to_markdown() +
            "\n\nOOS:\n\n" + G.pivot(index="lb", columns="q", values="OOS").to_markdown() + "\n\n")
    f.write(f"## Placebo (drop random 20% of longs, 200 runs)\n\nrule OOS {rs:.2f}; placebo mean {pl.mean():.2f}, p95 {np.percentile(pl,95):.2f}, max {pl.max():.2f}; p = {(pl >= rs).mean():.3f}\n\n")
    f.write("## By year\n\n" + yr.to_markdown() + "\n\n## OOS decomposition\n\n" + dec.to_markdown() + "\n\n")
    f.write("## Block bootstrap of (rule - base) per year, 30d blocks: [p5, p50, p95], P(<=0)\n\n" + "\n".join(f"- {k}: {v[0]}, P<=0 {v[1]}" for k, v in bs.items()) + "\n\n")
    f.write("## Dropped vs kept longs: forward return incl. funding (bps)\n\n" + pd.DataFrame(ev).to_markdown(index=False) + "\n\n")
    f.write(f"## Walk-forward (6m steps, pick best of 28 rules or off on trailing 2y)\n\nWF 2022-26 Sharpe {sh(wf.loc['2022':])}, base {sh(bb.net.loc['2022':])}; WF OOS {sh(wf.loc[OOS])}, base OOS {sh(bb.net.loc[OOS])}\n\npicks: {picks}\n")
print(open(lab.D.parent / "results_ret7.md").read())
o = br.net.loc[OOS]
print("stats.py BACKTEST (rule, OOS):", dict(sharpe=sh(o), ann_return_pct=round(o.mean()*36500, 1), daily_mean_pct=round(o.mean()*100, 3),
      daily_std_pct=round(o.std()*100, 2), worst_day_pct=round(o.min()*100, 1), max_dd_pct=round(lab.maxdd(o)*100, 1),
      price_pct_yr=round(br.gross.loc[OOS].mean()*36500, 1), funding_pct_yr=round(-br.fund.loc[OOS].mean()*36500, 1),
      cost_pct_yr=round(br.cost.loc[OOS].mean()*36500, 1)))
