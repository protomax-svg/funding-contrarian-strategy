"""Own crypto-only ideas, rules fixed BEFORE any run (2026-09-27). Pick on IS 2020-23, read OOS 2024-01..2026-08 once.

H1 New-listing short. New Binance perps drift down in their first weeks: low float / high FDV, airdrop and
   unlock selling, listing hype fades. Short every coin listed inside the sample from age `a0` to `a1` days,
   max 5% per coin, hedged with an equal-notional EW top-100 long. Real funding (new listings often pay shorts
   badly) is charged. Base a0=3, a1=60; IS grid a0 in {1,3,7}, a1 in {30,60,90}.
H2 Attention reversal. A sudden jump in trading volume (7d avg / 90d avg) = retail attention, priced too high.
   Short the top quintile, long the bottom quintile, top-100, weekly. Direction fixed in advance.
H3 Funding-settlement dip (1h, 50 coins). Before a settlement with high funding, longs close to avoid paying,
   so price dips into the settlement and recovers after. Event study only (hour -4..+4 around each real
   settlement, by the last settled rate); a trade needs the move to beat 2 x 7 bps.
"""
import numpy as np
import pandas as pd

import lab
from dip52 import C, IS, OOS, P, R, U, alpha, hedge, net, placebo, sh

AGE = C.notna().cumsum().where(C.notna())
FIRST = C.apply(pd.Series.first_valid_index)
NEW = FIRST > pd.Timestamp("2020-01-10", tz="UTC")            # listed inside the sample (a real listing date)
ALIVE = P["qv"] > 0


def h1(a0=3, a1=60, cap=0.05, min_qv=5e6):
    s = (AGE >= a0) & (AGE <= a1) & NEW.values[None, :] & ALIVE & (P["qv"] >= min_qv)
    n = s.sum(axis=1).replace(0, np.nan)
    w = s.astype(float).div(n, axis=0).fillna(0.0).clip(upper=cap)
    return -hedge(w, "EW")


def h2(q=0.2, k=7):
    att = P["qv"].rolling(7, min_periods=5).mean() / P["qv"].rolling(90, min_periods=60).mean()
    return lab.every(lab.xs_rank_weights(-att, U & att.notna(), q), k)


def full(tag, w, fund):
    x = net(w); a = alpha(x); pl = placebo(w, 100); b = lab.backtest(w, P, 7.0)
    return {"rule": tag, "IS": sh(x, IS), "OOS": sh(x, OOS), "OOS@15bps": sh(net(w, 15), OOS), "OOS +1d": sh(net(w, lag=1), OOS),
            "placebo p": round(float((pl >= lab.sharpe(x, 365)).mean()), 2), "alpha t": a[1], "b_EW": a[2],
            "ann %": round(100 * x.mean() * 365, 1), "funding/yr %": round(-100 * b["fund"].mean() * 365, 1),
            "maxDD": round(lab.maxdd(x), 2), "corr funding strat": round(x.corr(fund), 2)}, x


def h3():
    H = lab.load("1h")
    r, f = H["ret"], H["funding"]
    rows = []
    for j in r.columns:
        ev = f[j][f[j] != 0]                                    # real settlements of this coin (bar that pays)
        pos = r.index.get_indexer(ev.index)
        last = ev.shift(1)                                      # last settled rate, known before this settlement
        rr = r[j].values
        for p, lr, t in zip(pos, last.values, ev.index):
            if p < 5 or p + 5 >= len(rr) or not np.isfinite(lr):
                continue
            rows.append([t, lr] + [rr[p + k] for k in range(-4, 5)])
    E = pd.DataFrame(rows, columns=["t", "last"] + [f"h{k:+d}" for k in range(-4, 5)])
    E["bucket"] = pd.cut(E["last"], [-1, -0.0003, 0.0001, 0.0003, 1], labels=["<-0.03%", "~0", "0.01-0.03%", ">0.03%"])
    E["period"] = np.where(E.t < lab.SPLIT, "IS", "OOS")
    out = (E.groupby(["period", "bucket"], observed=True)[[c for c in E if c.startswith("h")]].mean() * 1e4).round(1)
    out["n"] = E.groupby(["period", "bucket"], observed=True).size()
    # trade: short the 2 bars before + the settlement bar when last > 0.03% => price part + funding received
    hi = E[E["last"] > 0.0003]
    tr = -(hi[["h-2", "h-1", "h+0"]].sum(axis=1)) * 1e4
    trade = hi.assign(bps=tr).groupby("period")["bps"].agg(["mean", "count"]).round(1)
    return out, trade


if __name__ == "__main__":
    F7 = P["funding"].rolling(7).mean()
    fund = net(lab.xs_rank_weights(-F7, U))
    grid = [(a0, a1) for a0 in (1, 3, 7) for a1 in (30, 60, 90)]
    G = pd.DataFrame([{"a0": a0, "a1": a1, "IS": sh(net(h1(a0, a1)), IS)} for a0, a1 in grid])
    best = tuple(G.loc[G.IS.idxmax(), ["a0", "a1"]].astype(int))
    rows, curves = [], {}
    for tag, w in ((f"H1 base a0=3 a1=60", h1()), (f"H1 IS-best a0={best[0]} a1={best[1]}", h1(*best)),
                   ("H2 attention reversal", h2())):
        r, x = full(tag, w, fund); rows.append(r); curves[tag] = x
    G["OOS"] = [sh(net(h1(a0, a1)), OOS) for a0, a1 in grid]        # shown after the pick, for the record
    T = pd.DataFrame(rows)
    n_new = s = ((AGE == 3) & NEW.values[None, :]).sum(axis=1)
    listings = n_new.groupby(n_new.index.year).sum()
    yr = pd.DataFrame(curves).groupby(lambda d: d.year).apply(lambda d: (100 * ((1 + d).prod() - 1)).round(1))
    print(T.to_string(), G.to_string(), listings.to_dict(), yr.to_string(), sep="\n", flush=True)
    ev, trade = h3()
    print(ev.to_string(), trade.to_string(), sep="\n")
    open("results_own.md", "w").write(
        "# Own crypto-only ideas (rules fixed before running; see own_ideas.py docstring)\n\n"
        "7 bps/side, real funding, IS 2020-23, OOS 2024-01..2026-08. H1/H2 via lab.backtest.\n\n"
        + T.to_markdown(index=False) + "\n\n## H1 grid (picked on IS; OOS shown after the pick)\n\n" + G.to_markdown(index=False)
        + "\n\nNew listings per year (in sample): " + str(listings.to_dict())
        + "\n\n## Return by year (%)\n\n" + yr.to_markdown()
        + "\n\n## H3 funding-settlement event study (mean return per 1h bar, bps; h+0 = the bar that pays)\n\n"
        + ev.to_markdown() + "\n\nTrade (short h-2..h+0 when last rate > 0.03%, price only, before 14 bps round trip "
        "and before the funding received):\n\n" + trade.to_markdown() + "\n")


def h4(win=90, q=0.2, k=7):
    """H4 betting-against-beta (fixed before running): long lowest-beta quintile, short highest, each leg scaled
    to beta 1 vs BTC so the book is BTC-neutral; gross capped at 2. Weekly."""
    b = R.rolling(win, min_periods=60).cov(R["BTCUSDT"]).div(R["BTCUSDT"].rolling(win, min_periods=60).var(), axis=0)
    base = lab.xs_rank_weights(b, U & b.notna(), q)                 # +0.5 on high beta, -0.5 on low beta
    lo, hi = -base.clip(upper=0), base.clip(lower=0)
    bl = (lo * b).sum(axis=1).replace(0, np.nan); bh = (hi * b).sum(axis=1).replace(0, np.nan)
    w = lo.div(bl, axis=0).clip(upper=1).fillna(0) * 0.5 - hi.div(bh, axis=0).clip(upper=1).fillna(0) * 0.5
    w = w.mul((2 / w.abs().sum(axis=1)).clip(upper=1), axis=0).fillna(0)
    return lab.every(w, k)
