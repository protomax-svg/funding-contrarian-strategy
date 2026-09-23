"""Robustness battery for the daily survivors. Each candidate is a function params -> weights."""
import itertools

import numpy as np
import pandas as pd

import lab

COST = 7.0
P = lab.load("1D")
C, H, L, F = P["close"], P["high"], P["low"], P["funding"]
UNI = {n: lab.universe(P, top_n=n) for n in (10, 20, 30, 50)}
U = UNI[30]
BTC = pd.DataFrame(False, index=U.index, columns=U.columns)
BTC["BTCUSDT"] = C["BTCUSDT"].notna()
EW = lab.backtest(lab.ts_weights(U * 1.0, U), P, COST)["net"]
BTCR = P["ret"]["BTCUSDT"].fillna(0)


def rsi_tsmom(p, mask):
    return lab.ts_weights((lab.rsi(C, p["n"]) > p["t"]).astype(float), mask)


def fund_xs(p, mask):
    return lab.every(lab.xs_rank_weights(-F.rolling(p["lb"]).mean(), mask), p["hold"])


def ibs(p, mask):
    ib = (C - L) / (H - L)
    band = H.rolling(10).max() - p["k"] * (H.rolling(25).mean() - L.rolling(25).mean())
    return lab.ts_weights(lab.hold((C < band) & (ib < p["t"]), C > H.shift(1)), mask)


def zscore(p, mask):
    z = (C - lab.ema(C, p["n"])) / C.rolling(p["n"]).std()
    return lab.ts_weights(lab.hold(z > p["bull"], z < p["bear"]), mask)


def taker(p, mask):
    return lab.xs_rank_weights((P["tbq"] / P["qv"] - 0.5).rolling(p["lb"]).mean(), mask)


def mom_xs(p, mask):
    return lab.every(lab.xs_rank_weights(C / C.shift(p["lb"]) - 1, mask), p["hold"])


CANDS = {
    "RSI TS-momentum (#4)": (rsi_tsmom, {"n": 5, "t": 70}, dict(n=[4, 5, 6], t=[65, 70, 75]), "U"),
    "RSI TS-momentum on BTC (#4)": (rsi_tsmom, {"n": 5, "t": 70}, dict(n=[4, 5, 6], t=[65, 70, 75]), "BTC"),
    "Funding contrarian XS (#7b)": (fund_xs, {"lb": 7, "hold": 1}, dict(lb=[3, 5, 7, 10, 14], hold=[1, 7]), "U"),
    "IBS dip (#12)": (ibs, {"k": 2.5, "t": 0.3}, dict(k=[2.0, 2.5, 3.0], t=[0.2, 0.3, 0.4]), "U"),
    "Z-score trend on BTC (#1)": (zscore, {"n": 65, "bull": 0.5, "bear": 0.0},
                                  dict(n=[50, 65, 80], bull=[0.25, 0.5, 1.0], bear=[-0.5, 0.0]), "BTC"),
    "Taker-flow follow XS (#14)": (taker, {"lb": 14}, dict(lb=[7, 10, 14, 21]), "U"),
    "XS momentum L/S (#17)": (mom_xs, {"lb": 28, "hold": 7}, dict(lb=[14, 21, 28, 42], hold=[1, 7]), "U"),
}


def net(w, cost=COST, lag=0):
    return lab.backtest(w.shift(lag).fillna(0) if lag else w, P, cost)["net"]


def sh(x, sl=slice(None)):
    return round(lab.sharpe(x.loc[sl], 365), 2)


OOS = slice(lab.SPLIT, None)
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))


def walk_forward(fn, grid, mask, train=180, test=30):
    """#11 method: every 30 days pick the grid point with the best trailing-180d Sharpe, trade it 30 days."""
    combos = [dict(zip(grid, v)) for v in itertools.product(*grid.values())]
    nets = pd.DataFrame({i: net(fn(c, mask)) for i, c in enumerate(combos)})
    out = pd.Series(0.0, index=nets.index)
    start = nets.index.get_loc(nets.index[0]) + 400      # skip warm-up
    for s0 in range(start, len(nets), test):
        tr = nets.iloc[s0 - train:s0]
        best = (tr.mean() / tr.std()).idxmax()
        out.iloc[s0:s0 + test] = nets[best].iloc[s0:s0 + test]
    return out.iloc[start:]


def placebo(sig_w, n=200, seed=0):
    """Circularly shift each coin's weight path by a random offset: keeps exposure + persistence, kills timing."""
    rng = np.random.default_rng(seed)
    vals = sig_w.values
    res = []
    for _ in range(n):
        sh_ = np.empty_like(vals)
        for j in range(vals.shape[1]):
            sh_[:, j] = np.roll(vals[:, j], rng.integers(200, len(vals) - 200))
        res.append(lab.sharpe(net(pd.DataFrame(sh_, index=sig_w.index, columns=sig_w.columns)), 365))
    return np.array(res)


def alpha(x):
    """Daily net ~ a + b1*EW_top30 + b2*BTC. Returns annual alpha, t, betas."""
    df = pd.concat([x, EW, BTCR], axis=1).dropna()
    df = df[df.iloc[:, 0] != 0]
    X = np.column_stack([np.ones(len(df)), df.iloc[:, 1], df.iloc[:, 2]])
    b, *_ = np.linalg.lstsq(X, df.iloc[:, 0].values, rcond=None)
    r = df.iloc[:, 0].values - X @ b
    se = np.sqrt(r @ r / (len(df) - 3) * np.linalg.inv(X.T @ X)[0, 0])
    return round(b[0] * 365, 3), round(b[0] / se, 2), round(b[1], 2), round(b[2], 2)


rows, years = [], {}
for name, (fn, base, grid, uni) in CANDS.items():
    mask = BTC if uni == "BTC" else U
    w = fn(base, mask)
    x = net(w)
    r = {"candidate": name, "Sharpe_all": sh(x), "IS": sh(x, IS), "OOS": sh(x, OOS),
         "OOS@15bps": sh(net(w, 15), OOS), "OOS +1d delay": sh(net(w, lag=1), OOS)}
    wf = walk_forward(fn, grid, mask)
    r["walkfwd_OOS"] = sh(wf, OOS)
    pl = placebo(w, 100 if uni == "U" else 200)
    r["placebo_p"] = round(float((pl >= lab.sharpe(x, 365)).mean()), 3)
    r["placebo_median"] = round(float(np.median(pl)), 2)
    a, t, b1, b2 = alpha(x)
    r.update({"alpha_ann": a, "alpha_t": t, "beta_EW": b1, "beta_BTC": b2})
    if uni == "U":
        for n_ in (10, 20, 50):
            r[f"OOS top{n_}"] = sh(net(fn(base, UNI[n_])), OOS)
    rows.append(r)
    years[name] = x.groupby(x.index.year).apply(lambda s: round(lab.sharpe(s, 365), 2))
    print(name, r, flush=True)

res = pd.DataFrame(rows)
yr = pd.DataFrame(years).T
# overlap between the market-neutral survivors
corr = pd.DataFrame({n: net(CANDS[n][0](CANDS[n][1], U)) for n in
                     ("Funding contrarian XS (#7b)", "Taker-flow follow XS (#14)", "XS momentum L/S (#17)")}).corr().round(2)
open("results_robust.md", "w").write(
    "# Robustness battery (daily survivors)\n\nBase params = as posted / neutral guess, never re-fit. "
    "7 bps/side unless noted. placebo_p = share of 100-200 time-shifted copies with Sharpe >= the real one.\n\n"
    + res.to_markdown(index=False) + "\n\n## Sharpe by calendar year\n\n" + yr.to_markdown()
    + "\n\n## Correlation of the market-neutral survivors (daily net)\n\n" + corr.to_markdown() + "\n")
print("wrote results_robust.md")
