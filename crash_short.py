"""Lead found while testing #19: after a sharp one-day drop (-2.2..-4.2 sigma) far from the 365d high, the coin
kept LOSING vs the market (dip52.py study A: 21d vs-market t = -1.6 IS, -3.7 OOS). Flip it:
short every such coin for H days, hedged with an equal-notional long in the EW top-100 market.
The lead came from looking at OOS, so the IS grid below is the honest part; OOS is not clean here.
"""
import numpy as np
import pandas as pd

import lab
from dip52 import C, IS, OOS, P, U, Z, alpha, dip_book, hedge, net, placebo, sh, DIST, VOL


def book(z_lo=-4.2, z_hi=-2.2, h=21, far_only=True, cap=0.05):
    """cap = max weight per short coin; the rest stays in cash (few events must not mean one big bet)."""
    ev = (Z >= z_lo) & (Z <= z_hi) & U & VOL.notna()
    if far_only:
        ev &= -DIST > 3.3 * VOL
    return -hedge(dip_book(ev, h).clip(upper=cap), "EW")        # short the dips, long the market


def walk_forward(N, train=365, test=30):
    """Every 30d trade the grid point with the best trailing-365d Sharpe."""
    out = []
    for i in range(train, len(N), test):
        best = N.iloc[i - train:i].apply(lambda s: lab.sharpe(s, 365)).idxmax()
        out.append(N[best].iloc[i:i + test])
    return pd.concat(out)


if __name__ == "__main__":
    grid = [(zl, zh, h, far) for zl, zh in ((-4.2, -2.2), (-3, -1.5), (-6, -3), (-99, -2.2)) for h in (7, 21, 63)
            for far in (True, False)]
    N = pd.DataFrame({g: net(book(*g)) for g in grid})
    G = pd.DataFrame([{"drop sigma": f"{g[0]}..{g[1]}", "hold": g[2], "far only": g[3], "IS": sh(N[g], IS),
                       "OOS": sh(N[g], OOS)} for g in grid])
    wf = walk_forward(N)
    isbest = max(grid, key=lambda g: lab.sharpe(N[g].loc[IS], 365))
    fund = net(lab.xs_rank_weights(-P["funding"].rolling(7).mean(), U))       # the live funding strategy
    rows, years = {}, {}
    for tag, g in (("post-like base (-4.2..-2.2, far, 21d)", (-4.2, -2.2, 21, True)), (f"IS-best {isbest}", isbest)):
        w = book(*g); x = net(w); b = lab.backtest(w, P, 7.0); a = alpha(x); pl = placebo(w)
        rows[tag] = {"IS": sh(x, IS), "OOS": sh(x, OOS), "OOS@15bps": sh(net(w, 15), OOS), "OOS +1d": sh(net(w, lag=1), OOS),
                     "placebo p": round(float((pl >= lab.sharpe(x, 365)).mean()), 3), "alpha/yr": a[0], "alpha t": a[1],
                     "b_EW": a[2], "b_BTC": a[3], "maxDD": round(lab.maxdd(x), 2), "ann ret %": round(100 * x.mean() * 365, 1),
                     "funding recv/yr %": round(-100 * b["fund"].mean() * 365, 1), "cost/yr %": round(100 * b["cost"].mean() * 365, 1),
                     "avg short gross": round(float(-w.clip(upper=0).sum(axis=1).mean()), 2), "corr w/ funding strat": round(x.corr(fund), 2)}
        for wgt in (0.25, 0.5):
            bl = (1 - wgt) * fund + wgt * x
            rows[tag][f"blend {int(100 * wgt)}% IS/OOS/maxDD"] = f"{sh(bl, IS)} / {sh(bl, OOS)} / {lab.maxdd(bl):.2f}"
        years[tag] = x.groupby(x.index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1))
    years["funding strat"] = fund.groupby(fund.index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1))
    head = pd.DataFrame(rows)
    summ = (f"Grid (24 points): IS>0 {(G.IS > 0).mean():.2f}, OOS>0 {(G.OOS > 0).mean():.2f}, median IS {G.IS.median():.2f}, "
            f"median OOS {G.OOS.median():.2f}. Walk-forward over the grid (365d train, 30d step): OOS {sh(wf, OOS)}. "
            f"Funding strat alone: IS {sh(fund, IS)}, OOS {sh(fund, OOS)}, maxDD {lab.maxdd(fund):.2f}.")
    print(head.to_string(), summ, pd.DataFrame(years).to_string(), G.to_string(), sep="\n")
    open("results_crash_short.md", "w").write(
        "# Lead from #19: short sharp-drop coins far from their high, hedged with the EW market\n\n"
        "Found by looking at OOS in dip52.py, so the post-like base is NOT a clean OOS test; the IS-best point and the "
        "walk-forward are. Max 5% per short coin (uncapped, one coin could be ~100% of the short leg: PIPPIN 2025-10, "
        "LAB 2026-07 squeezes). 7 bps, real funding, top-100.\n\n" + head.to_markdown() + "\n\n" + summ
        + "\n\n## Return by year (%)\n\n" + pd.DataFrame(years).to_markdown() + "\n\n## Grid\n\n" + G.to_markdown(index=False) + "\n")
