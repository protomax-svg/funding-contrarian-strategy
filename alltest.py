"""Re-test base, live and the IS-chosen combination on ALL Binance crypto perps (no hand-picked list).

Universe = every USDT-M crypto perpetual that ever traded (Binance underlyingType COIN, plus delisted coins),
ranked point-in-time by 30d quote volume. Stocks, commodities, pre-market and index perps are excluded.
"""
import numpy as np
import pandas as pd

import lab
from improve import buffered, without     # pure functions (improve.py also re-runs its study on import)

D = lab.D / "all"
SYMS = [l.strip() for l in open(D / "crypto_symbols.txt") if l.strip()]
COST = 7.0


def panel():
    rd = lambda f: pd.read_parquet(D / f)
    P = {k: rd(f).reindex(columns=[s for s in SYMS if s in rd(f).columns]) for k, f in
         (("open", "open.parquet"), ("high", "high.parquet"), ("low", "low.parquet"), ("close", "close.parquet"),
          ("qv", "quote_volume.parquet"), ("prem", "premium_close.parquet"), ("funding", "funding_daily.parquet"))}
    idx = P["close"].index
    idx = idx[(idx >= "2020-01-01") & (idx <= "2026-08-31")]
    cols = P["close"].columns
    for k in P:
        P[k] = P[k].reindex(index=idx, columns=cols)
    for k in P:
        if P[k].index.tz is None:
            P[k].index = P[k].index.tz_localize("UTC")
    P["funding"] = P["funding"].fillna(0.0)
    P["ret"] = P["close"].pct_change(fill_method=None)
    return P


P = panel()
C, R = P["close"], P["ret"]
F7 = P["funding"].rolling(7).mean()
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))
OOS = slice(lab.SPLIT, None)
ATR_P = lab.pct_rank(lab.atr_pct(P["high"]["BTCUSDT"], P["low"]["BTCUSDT"], C["BTCUSDT"]))
ATR_ON = (ATR_P >= 1 / 3).astype(float).where(ATR_P.notna(), 1.0)
ret7 = C / C.shift(7) - 1


def with_stop(w, stop=0.50, cool=7):
    wv, cv = w.values.copy(), C.values
    entry = np.full(wv.shape[1], np.nan); side = np.zeros(wv.shape[1]); blocked = np.zeros(wv.shape[1])
    for i in range(len(wv)):
        blocked = np.maximum(blocked - 1, 0)
        tgt = np.sign(wv[i])
        b = blocked > 0
        wv[i, b] = 0.0; side[b] = 0
        new = ~b & (tgt != side)
        side[new], entry[new] = tgt[new], cv[i, new]
        held = ~b & ~new & (side != 0) & np.isfinite(entry) & np.isfinite(cv[i])
        with np.errstate(invalid="ignore", divide="ignore"):
            hit = held & (side * (cv[i] / entry - 1) < -stop)
        wv[i, hit] = 0.0; side[hit] = 0; blocked[hit] = cool
    out = pd.DataFrame(wv, index=w.index, columns=w.columns)
    lo, sh = out.clip(lower=0), -out.clip(upper=0)
    return (0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0) - \
        (0.5 * sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0)


def combo(U, score):
    w = buffered(score, U, 0.2, 0.35)
    w = without(w, drop_short=(ret7.where(U).rank(axis=1, pct=True) >= 0.8).fillna(False))
    return with_stop(w, 0.50)


def stats(name, w):
    b = lab.backtest(w, P, COST); x = b["net"]; o = x.loc[OOS]
    return {"variant": name, "IS": round(lab.sharpe(x.loc[IS], 365), 2), "OOS": round(lab.sharpe(o, 365), 2),
            "OOS@15bps": round(lab.sharpe(lab.backtest(w, P, 15)["net"].loc[OOS], 365), 2),
            "OOS +1d": round(lab.sharpe(lab.backtest(w.shift(1).fillna(0), P, COST)["net"].loc[OOS], 365), 2),
            "OOS total %": round(100 * ((1 + o).prod() - 1), 1), "maxDD": round(lab.maxdd(x), 3),
            "OOS maxDD": round(lab.maxdd(o), 3), "cost/yr": round(b["cost"].mean() * 365, 3)}, x


if __name__ == "__main__":
    rows, curves = [], {}
    for n in (30, 40, 50, 100):
        U = lab.universe(P, n)
        base = lab.xs_rank_weights(-F7, U)
        for nm, w in ((f"top-{n} base", base), (f"top-{n} base + ATR (live now)", base.mul(ATR_ON, axis=0)),
                      (f"top-{n} COMBO (buffer+no-short-rally+stop50)", combo(U, -F7))):
            r, x = stats(nm, w); rows.append(r); curves[nm] = x
        print(n, "done", flush=True)
    # premium index instead of funding (research idea #5): perp premium over spot, 7d mean
    U40 = lab.universe(P, 40)
    pr7 = P["prem"].rolling(7).mean()
    for nm, w in (("top-40 base on PREMIUM", lab.xs_rank_weights(-pr7, U40)),
                  ("top-40 COMBO on PREMIUM", combo(U40, -pr7))):
        r, x = stats(nm, w); rows.append(r); curves[nm] = x
    df = pd.DataFrame(rows)
    key = [k for k in curves if "COMBO (" in k or "live now" in k]
    yr = pd.DataFrame({k: curves[k].groupby(curves[k].index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1))
                       for k in key}).T
    n_by_year = lab.universe(P, 40).sum(axis=1).groupby(P["close"].index.year).mean().round(1)
    md = ("# All Binance crypto perps (" + str(len(SYMS)) + " symbols incl. delisted)\n\n"
          "No hand-picked list: point-in-time top-N by 30d volume. 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.\n\n"
          + df.to_markdown(index=False) + "\n\n## Return by year (%)\n\n" + yr.to_markdown()
          + "\n\nAvg coins in the top-40 universe per year: " + ", ".join(f"{y}: {v}" for y, v in n_by_year.items()) + "\n")
    open("results_all.md", "w").write(md)
    print(md)
