"""Idea #19: "Buy the dip near the 52-week high" (r/algotrading 1tzicir, 2026-06) + the cross-sectional
"nearness to 52-week high" factor it points at (George & Hwang 2004), on all Binance crypto perps.

Post (QQQ, 25 y): a one-day drop of -3.3%..-6.3% while within 5% of the 52w high -> +4.7% after 3 months,
80% positive, half the drawdown of the same drop far from the high (N=20 vs 164).
Crypto moves ~2.5x more, so drops and distances are scaled by each coin's own 30d daily vol:
QQQ daily vol ~1.5% -> drop = -2.2..-4.2 sigma, "near" = within 3.3 sigma of the high.

A. event study as posted (per coin-day events, date-clustered stats)
B. tradeable version: hold every near-high dip for H days, raw and BTC/market-hedged
C. cross-sectional factor: long coins closest to their 365d high, short the farthest
Rules as in lab.py: signal on close t, earn t+1, 7 bps/side, real funding, point-in-time top-N, IS 2020-23 / OOS 2024+.
"""
import numpy as np
import pandas as pd

import lab

D = lab.D / "all"
SYMS = [l.strip() for l in open(D / "crypto_symbols.txt") if l.strip()]
COST = 7.0
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))
OOS = slice(lab.SPLIT, None)


def panel():
    P = {}
    for k in ("open", "high", "low", "close", "quote_volume", "funding_daily"):
        x = pd.read_parquet(D / f"{k}.parquet")
        P[{"quote_volume": "qv", "funding_daily": "funding"}.get(k, k)] = x
    idx = P["close"].index
    idx = idx[(idx >= "2020-01-01") & (idx <= "2026-08-31")]
    cols = [s for s in SYMS if s in P["close"].columns]
    for k in P:
        P[k] = P[k].reindex(index=idx, columns=cols)
        if P[k].index.tz is None:
            P[k].index = P[k].index.tz_localize("UTC")
    P["funding"] = P["funding"].fillna(0.0)
    P["ret"] = P["close"].pct_change(fill_method=None)
    return P


P = panel()
C, R = P["close"], P["ret"]
U = lab.universe(P, 100)
HI = P["high"].rolling(365, min_periods=180).max()
DIST = C / HI - 1                                       # 0 = at the 365d high, known at close t
VOL = R.rolling(30, min_periods=20).std().shift(1)      # vol before today's move
Z = R / VOL
EW = R.where(U).mean(axis=1)                            # equal-weight top-100 market
BTC = R["BTCUSDT"]


def sh(x, sl=slice(None)):
    return round(lab.sharpe(x.loc[sl], 365), 2)


def net(w, cost=COST, lag=0):
    return lab.backtest(w.shift(lag).fillna(0.0) if lag else w, P, cost)["net"]


def alpha(x):
    """Daily net ~ a + b1*EW + b2*BTC -> (annual alpha, t, b_EW, b_BTC)."""
    df = pd.concat([x, EW, BTC], axis=1).dropna()
    df = df[df.iloc[:, 0] != 0]
    X = np.column_stack([np.ones(len(df)), df.iloc[:, 1], df.iloc[:, 2]])
    b, *_ = np.linalg.lstsq(X, df.iloc[:, 0].values, rcond=None)
    r = df.iloc[:, 0].values - X @ b
    se = np.sqrt(r @ r / (len(df) - 3) * np.linalg.inv(X.T @ X)[0, 0])
    return round(b[0] * 365, 3), round(b[0] / se, 2), round(b[1], 2), round(b[2], 2)


def placebo(w, n=100, seed=0):
    """Circular time-shift of each coin's weight path: keeps exposure and persistence, kills timing."""
    rng = np.random.default_rng(seed)
    v, out = w.values, []
    for _ in range(n):
        s = np.column_stack([np.roll(v[:, j], rng.integers(200, len(v) - 200)) for j in range(v.shape[1])])
        out.append(lab.sharpe(net(pd.DataFrame(s, index=w.index, columns=w.columns)), 365))
    return np.array(out)


# ---------------- A. event study ----------------
def fwd(h):
    c = C.ffill()                                        # a coin that dies keeps its last price
    f = c.shift(-h) / c - 1
    mdd = c.rolling(h).min().shift(-h) / c - 1          # worst close in t+1..t+h
    ewf = (1 + EW.fillna(0)).cumprod()
    return f, mdd, f.sub(ewf.shift(-h) / ewf - 1, axis=0)


def events(z_lo=-4.2, z_hi=-2.2, near_sig=3.3, raw=None):
    """raw=(lo, hi, near) uses plain % thresholds instead of vol units (the post's own numbers)."""
    if raw:
        drop = (R >= raw[0]) & (R <= raw[1])
        near = DIST >= -raw[2]
    else:
        drop = (Z >= z_lo) & (Z <= z_hi)
        near = -DIST <= near_sig * VOL
    ok = U & HI.notna() & VOL.notna()
    return drop & near & ok, drop & ~near & ok


def clustered(ev, val):
    """Mean per event-date first (events on one day are one bet), then stats over dates."""
    d = val.where(ev).stack()
    by_day = d.groupby(level=0).mean()
    months = by_day.groupby(by_day.index.to_period("M")).mean()          # month clusters for the t-stat
    t = months.mean() / months.std() * np.sqrt(len(months)) if len(months) > 2 else np.nan
    return len(d), len(by_day), by_day.mean(), (by_day > 0).mean(), t


def study_A():
    rows = []
    H = {21: fwd(21), 63: fwd(63)}
    specs = {"BTC only, post's raw % (-3.3..-6.3%, within 5%)": ("BTC", dict(raw=(-0.063, -0.033, 0.05))),
             "BTC only, vol-scaled": ("BTC", {}),
             "top-100, vol-scaled": ("ALL", {}),
             "top-100, deeper drop -3..-6 sigma": ("ALL", dict(z_lo=-6, z_hi=-3)),
             "top-100, near = within 2 sigma": ("ALL", dict(near_sig=2.0)),
             "top-100, near = within 5 sigma": ("ALL", dict(near_sig=5.0))}
    for name, (who, kw) in specs.items():
        near, far = events(**kw)
        if who == "BTC":
            keep = pd.DataFrame(False, index=C.index, columns=C.columns); keep["BTCUSDT"] = True
            near, far = near & keep, far & keep
        for per, sl in (("IS", IS), ("OOS", OOS)):
            for grp, ev in (("near", near), ("far", far)):
                e = ev.loc[sl]
                r = {"spec": name, "period": per, "group": grp}
                for h, (f, mdd, xs) in H.items():
                    n, nd, m, pos, t = clustered(e, f.loc[sl])
                    r.update({"events": n, "dates": nd, f"ret{h}d %": round(100 * m, 1), f"pos{h}d": round(pos, 2),
                              f"t{h}d": round(t, 2)})
                    _, _, mx, _, tx = clustered(e, xs.loc[sl])
                    r.update({f"vs mkt {h}d %": round(100 * mx, 1), f"t vs mkt {h}d": round(tx, 2)})
                    r[f"heat{h}d %"] = round(100 * clustered(e, mdd.loc[sl])[2], 1)
                rows.append(r)
    return pd.DataFrame(rows)


# ---------------- B. tradeable dip-near-high ----------------
def dip_book(ev, h):
    """Long every event for h days, equal weight across open events, gross <= 1."""
    act = ev.astype(float).rolling(h, min_periods=1).max().fillna(0.0).where(P["qv"] > 0, 0.0)   # drop once it stops trading
    return act.div(act.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def hedge(w, how):
    g = w.sum(axis=1)
    if how == "BTC":
        w = w.copy(); w["BTCUSDT"] = w["BTCUSDT"] - g
    elif how == "EW":
        m = U.astype(float); m = m.div(m.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        w = w - m.mul(g, axis=0)
    return w


def study_B():
    rows = []
    near, far = events()
    for h in (21, 63):
        for grp, ev in (("near", near), ("far", far)):
            for hg in ("none", "BTC", "EW"):
                w = hedge(dip_book(ev, h), hg)
                x = net(w)
                a = alpha(x)
                rows.append({"book": f"{grp} dips, hold {h}d", "hedge": hg, "IS": sh(x, IS), "OOS": sh(x, OOS),
                             "OOS@15bps": sh(net(w, 15), OOS), "+1d": sh(net(w, lag=1), OOS),
                             "ann ret %": round(100 * x.mean() * 365, 1), "maxDD": round(lab.maxdd(x), 2),
                             "alpha/yr": a[0], "alpha t": a[1], "b_EW": a[2], "b_BTC": a[3],
                             "time in mkt": round(float((w.abs().sum(axis=1) > 0).mean()), 2)})
    x = EW.fillna(0).where(EW.index >= EW.first_valid_index())
    rows.append({"book": "EW top-100 long (benchmark)", "hedge": "none", "IS": sh(x, IS), "OOS": sh(x, OOS),
                 "maxDD": round(lab.maxdd(x), 2)})
    return pd.DataFrame(rows)


# ---------------- C. cross-sectional nearness to the 365d high ----------------
def xs(lb=365, q=0.2, k=7, n=100, score="dist"):
    Un = lab.universe(P, n)
    hi = P["high"].rolling(lb, min_periods=lb // 2).max()
    s = C / hi - 1 if score == "dist" else C / C.shift(lb) - 1       # "mom" = plain momentum, same lookback
    return lab.every(lab.xs_rank_weights(s, Un & hi.notna(), q), k)


def walk_forward(grid, train=365, test=30):
    """Every 30d pick the grid point with the best trailing-365d Sharpe, trade it for the next 30d."""
    nets = {g: net(xs(*g)) for g in grid}
    N = pd.DataFrame(nets)
    out = []
    for i in range(train, len(N), test):
        best = N.iloc[i - train:i].apply(lambda s: lab.sharpe(s, 365)).idxmax()
        out.append(N[best].iloc[i:i + test])
    return pd.concat(out)


def study_C():
    rows, curves = [], {}
    grid = [(lb, q, k) for lb in (90, 180, 365) for q in (0.2, 0.33) for k in (1, 7, 30)]
    for lb, q, k in grid:
        x = net(xs(lb, q, k)); curves[(lb, q, k)] = x
        rows.append({"lookback": lb, "q": q, "rebal d": k, "IS": sh(x, IS), "OOS": sh(x, OOS)})
    G = pd.DataFrame(rows)
    # the headline variant is fixed a priori: George-Hwang's 52w (365d), quintiles, weekly
    w = xs(365, 0.2, 7); x = net(w)
    mom = net(xs(365, 0.2, 7, score="mom"))
    F7 = P["funding"].rolling(7).mean()
    fund = net(lab.xs_rank_weights(-F7, U))                         # the live funding strategy
    pl = placebo(w)
    a = alpha(x)
    # residual after momentum: does nearness add anything once plain 365d momentum is known?
    df = pd.concat([x, mom], axis=1).dropna(); df = df[df.iloc[:, 0] != 0]
    X = np.column_stack([np.ones(len(df)), df.iloc[:, 1]])
    b, *_ = np.linalg.lstsq(X, df.iloc[:, 0].values, rcond=None)
    res = df.iloc[:, 0].values - X @ b
    t_res = b[0] / np.sqrt(res @ res / (len(df) - 2) * np.linalg.inv(X.T @ X)[0, 0])
    wf = walk_forward(grid)
    head = {"IS": sh(x, IS), "OOS": sh(x, OOS), "OOS@15bps": sh(net(w, 15), OOS), "OOS +1d": sh(net(w, lag=1), OOS),
            "walk-fwd OOS": sh(wf, OOS), "placebo p": round(float((pl >= lab.sharpe(x, 365)).mean()), 3),
            "placebo median": round(float(np.median(pl)), 2), "alpha/yr": a[0], "alpha t": a[1],
            "b_EW": a[2], "b_BTC": a[3], "maxDD": round(lab.maxdd(x), 2), "OOS maxDD": round(lab.maxdd(x.loc[OOS]), 2),
            "corr w/ momentum": round(x.corr(mom), 2), "alpha vs momentum t": round(t_res, 2),
            "corr w/ funding strat": round(x.corr(fund), 2)}
    for n in (30, 50):
        xn = net(xs(365, 0.2, 7, n)); head[f"top-{n} OOS"] = sh(xn, OOS)
    head["momentum 365d OOS"] = sh(mom, OOS)
    yr = pd.DataFrame({"nearness": x, "momentum": mom, "funding": fund, "50/50 funding+nearness": 0.5 * fund + 0.5 * x})
    blend = {c: {"IS": sh(yr[c], IS), "OOS": sh(yr[c], OOS), "maxDD": round(lab.maxdd(yr[c]), 2)} for c in yr}
    by_year = yr.groupby(yr.index.year).apply(lambda d: (100 * ((1 + d).prod() - 1)).round(1))
    return G, head, pd.DataFrame(blend).T, by_year


if __name__ == "__main__":
    A = study_A(); print(A.to_string(), flush=True)
    B = study_B(); print(B.to_string(), flush=True)
    G, head, blend, yr = study_C(); print(G.to_string(), head, blend, yr, sep="\n", flush=True)
    md = ("# Idea #19: buy the dip near the 52-week high (+ nearness-to-high factor)\n\n"
          "Source: https://www.reddit.com/r/algotrading/comments/1tzicir/ (QQQ, 2026-06) and follow-up 1ty1rch.\n"
          "All Binance crypto perps, point-in-time top-100, 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.\n"
          "Drops/distances in units of each coin's 30d daily vol (QQQ -3.3..-6.3% at ~1.5% vol -> -2.2..-4.2 sigma; "
          "within 5% -> within 3.3 sigma).\n\n"
          "## A. Event study (entry at the drop-day close; t = month-clustered; 'vs mkt' = minus EW top-100)\n\n"
          + A.to_markdown(index=False) +
          "\n\n## B. Trade every dip for H days (gross 1 when any open)\n\n" + B.to_markdown(index=False) +
          "\n\n## C. Cross-sectional nearness to 365d high (long nearest quintile, short farthest)\n\n"
          "Headline fixed before looking: 365d, q=0.2, weekly, top-100.\n\n"
          + pd.Series(head).to_frame("value").to_markdown() +
          "\n\n### Grid (all 18 points)\n\n" + G.to_markdown(index=False) +
          "\n\n### Blend with the live funding strategy\n\n" + blend.to_markdown() +
          "\n\n### Return by year (%)\n\n" + yr.to_markdown() + "\n")
    open("results_dip52.md", "w").write(md)
