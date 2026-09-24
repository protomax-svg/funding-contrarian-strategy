"""Does price correlation help choose longs and shorts? Top-100 of all Binance crypto perps (alltest.py).

1) corr pairs: each day, among the long candidates (lowest 20% funding) and short candidates (highest 20%),
   greedily match the most correlated long/short pair (trailing 60d daily returns), then the next, ...
   Equal weight per pair (0.5/N long, 0.5/N short).
2) skip loners: drop candidates whose 60d correlation to the equal-weight market is in the bottom third.
3) beta-neutral legs: scale the long vs short leg to zero beta to the market.
All inputs use data up to the close of day t only.
"""
import numpy as np
import pandas as pd

import lab
from alltest import P, F7, IS, OOS

COST = 7.0
U = lab.universe(P, 100)
R = P["ret"]
MKT = R.where(U).mean(axis=1)
LB = 60
BASE = lab.xs_rank_weights(-F7, U)


def corr_pairs(base, lb=LB):
    W = np.zeros(base.shape)
    Rv = R.values
    for i in range(lb, len(base)):
        row = base.values[i]
        L, S = np.where(row > 0)[0], np.where(row < 0)[0]
        if len(L) == 0 or len(S) == 0:
            continue
        win = Rv[i - lb + 1:i + 1][:, np.r_[L, S]]
        ok = np.isfinite(win).sum(axis=0) >= lb * 0.8
        c = pd.DataFrame(win).corr(min_periods=int(lb * 0.8)).values
        c = c[:len(L), len(L):]                              # long x short block
        c[~ok[:len(L)], :] = np.nan
        c[:, ~ok[len(L):]] = np.nan
        pairs = []
        c = np.where(np.isfinite(c), c, -9)
        while True:
            k = np.unravel_index(np.argmax(c), c.shape)
            if c[k] <= -9:
                break
            pairs.append(k)
            c[k[0], :] = -9
            c[:, k[1]] = -9
        for a, b in pairs:
            W[i, L[a]] += 0.5 / len(pairs)
            W[i, S[b]] -= 0.5 / len(pairs)
    return pd.DataFrame(W, index=base.index, columns=base.columns)


def skip_loners(base, lb=LB):
    cm = R.rolling(lb, min_periods=int(lb * 0.8)).corr(MKT)
    low = cm.where(U).rank(axis=1, pct=True) <= 1 / 3
    lo, sh = base.clip(lower=0).where(~low.fillna(True), 0), (-base.clip(upper=0)).where(~low.fillna(True), 0)
    return (0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0) - \
        (0.5 * sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0)


def beta_neutral(w, lb=LB):
    beta = R.rolling(lb, min_periods=30).cov(MKT).div(MKT.rolling(lb, min_periods=30).var(), axis=0)
    bl = (w.clip(lower=0) * beta).sum(axis=1)
    bs = (-w.clip(upper=0) * beta).sum(axis=1)
    a = (bs / (bl + bs)).where((bl > 0) & (bs > 0), 0.5).clip(0.25, 0.75)
    return w.clip(lower=0).mul(2 * a, axis=0) + w.clip(upper=0).mul(2 * (1 - a), axis=0)


def stats(name, w):
    b = lab.backtest(w, P, COST); x = b["net"]; o = x.loc[OOS]
    return {"variant": name, "IS": round(lab.sharpe(x.loc[IS], 365), 2), "OOS": round(lab.sharpe(o, 365), 2),
            "OOS@15bps": round(lab.sharpe(lab.backtest(w, P, 15)["net"].loc[OOS], 365), 2),
            "OOS +1d": round(lab.sharpe(lab.backtest(w.shift(1).fillna(0), P, COST)["net"].loc[OOS], 365), 2),
            "OOS total %": round(100 * ((1 + o).prod() - 1), 1), "ann vol %": round(100 * x.std() * 365 ** 0.5, 1),
            "maxDD": round(lab.maxdd(x), 3), "worst month %": round(100 * x.resample("ME").sum().min(), 1),
            "OOS price %/yr": round(100 * b["gross"].loc[OOS].mean() * 365, 1),
            "OOS funding %/yr": round(-100 * b["fund"].loc[OOS].mean() * 365, 1)}


if __name__ == "__main__":
    CP = corr_pairs(BASE)
    rows = [stats("base top-100 (live)", BASE),
            stats("1) correlation pairs", CP),
            stats("2) skip loners (low corr to market)", skip_loners(BASE)),
            stats("3) beta-neutral legs", beta_neutral(BASE)),
            stats("1+3) corr pairs + beta-neutral", beta_neutral(CP)),
            stats("2+3) skip loners + beta-neutral", beta_neutral(skip_loners(BASE)))]
    # how correlated are the matched pairs, and how much does pairing lower daily risk?
    df = pd.DataFrame(rows)
    md = ("# Price correlation to choose longs and shorts (top-100, all crypto perps)\n\n"
          "60d daily-return correlation, known at the close. 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.\n\n"
          + df.to_markdown(index=False) + "\n")
    open("results_corr.md", "w").write(md)
    print(md)
