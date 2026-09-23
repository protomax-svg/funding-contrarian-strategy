"""Shared backtest core for the r/algotrading idea tests.

Conventions (same hygiene as ../dynamic-exit):
- A weight decided with data up to close of bar t earns the return of bar t+1.
  Crypto is 24/7, so close[t] ~= open[t+1]; this is "signal on closed bar, fill next open".
- Costs: |change in weight| * cost_bps, charged every rebalance.
- Funding: a long pays funding_rate, a short receives it, for every funding event inside the bar held.
- Point-in-time universe: a coin is tradable only after 60 days of history and only while it is
  in the top-N by trailing 30-day quote volume. Delisted coins stay in the panel until they die.
- Split: in-sample 2020-2023 (pick parameters here), out-of-sample 2024-01 -> 2026-08 (look once).
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent / "data"
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
PPY = {"1h": 24 * 365, "4h": 6 * 365, "1D": 365, "1W": 52}


def load(freq="1D"):
    """Panels (index=time, columns=symbol): open high low close qv tbq funding ret."""
    cols = {k: {} for k in ("open", "high", "low", "close", "qv", "tbq", "funding")}
    for f in sorted((D / "klines_1h").glob("*.parquet")):
        s = f.stem
        k = pd.read_parquet(f).set_index("ts")
        r = k.resample(freq, label="left", closed="left")
        cols["open"][s] = r.open.first()
        cols["high"][s] = r.high.max()
        cols["low"][s] = r.low.min()
        cols["close"][s] = r.close.last()
        cols["qv"][s] = r.quote_volume.sum(min_count=1)
        cols["tbq"][s] = r.taker_buy_quote.sum(min_count=1)
        fp = D / "funding" / f"{s}.parquet"
        if fp.exists():
            fu = pd.read_parquet(fp).set_index("ts").funding_rate
            # event at 08:00:00.002 belongs to the bar that holds the position over 08:00
            fu.index = fu.index.floor("min") - pd.Timedelta("1min")
            cols["funding"][s] = fu.resample(freq, label="left", closed="left").sum()
    P = {k: pd.DataFrame(v).sort_index() for k, v in cols.items()}
    idx = P["close"].index
    P["funding"] = P["funding"].reindex(index=idx, columns=P["close"].columns).fillna(0.0)
    P["ret"] = P["close"].pct_change(fill_method=None)
    return P


def universe(P, top_n=30, min_age_bars=60, vol_window=30):
    """Boolean mask: tradable at bar t (decided with data up to t)."""
    c = P["close"]
    age = c.notna().cumsum()
    adv = P["qv"].rolling(vol_window, min_periods=vol_window // 2).mean()
    rank = adv.where(age >= min_age_bars).rank(axis=1, ascending=False)
    return (rank <= top_n) & c.notna()


def backtest(w, P, cost_bps=5.0, funding=True):
    """w: target weights at bar t (from info <= t). Returns per-bar net pnl series and details."""
    w = w.reindex_like(P["ret"]).fillna(0.0)
    pos = w.shift(1).fillna(0.0)                     # held during bar t+1
    ret = P["ret"].fillna(0.0)
    gross = (pos * ret).sum(axis=1)
    turn = (w - w.shift(1).fillna(0.0)).abs().sum(axis=1).shift(1).fillna(0.0)
    cost = turn * cost_bps / 1e4
    fund = (pos * P["funding"]).sum(axis=1) if funding else 0.0
    net = gross - cost - fund
    return pd.DataFrame({"net": net, "gross": gross, "cost": cost, "fund": fund, "turn": turn,
                         "gross_exp": pos.abs().sum(axis=1)})


def sharpe(x, ppy):
    x = x.dropna()
    return float(x.mean() / x.std() * np.sqrt(ppy)) if x.std() > 0 else 0.0


def maxdd(x):
    eq = (1 + x.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def block_boot_p(x, n=2000, block=20, seed=0):
    """One-sided p-value that mean <= 0, stationary-ish block bootstrap of the demeaned series."""
    x = x.dropna().values
    m = len(x)
    if m < block * 3:
        return np.nan
    rng = np.random.default_rng(seed)
    z = x - x.mean()
    nb = m // block + 1
    starts = rng.integers(0, m - block, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n, -1)[:, :m]
    means = z[idx].mean(axis=1)
    return float((means >= x.mean()).mean())


def report(bt, freq="1D", name=""):
    ppy = PPY[freq]
    out = {"name": name}
    for tag, sl in (("all", slice(None)), ("IS", slice(None, SPLIT - pd.Timedelta("1ns"))),
                    ("OOS", slice(SPLIT, None))):
        x = bt["net"].loc[sl]
        x = x[bt["gross_exp"].loc[sl].gt(0).cumsum() > 0]  # start at first position
        out[f"{tag}_sharpe"] = round(sharpe(x, ppy), 2)
        out[f"{tag}_annret"] = round(float(x.mean() * ppy), 3)
    x = bt["net"]
    out["maxdd"] = round(maxdd(x), 3)
    out["turn_per_yr"] = round(float(bt["turn"].mean() * ppy), 1)
    out["exposure"] = round(float(bt["gross_exp"].mean()), 2)
    out["cost_ann"] = round(float(bt["cost"].mean() * ppy), 3)
    out["fund_ann"] = round(float(bt["fund"].mean() * ppy), 3)
    out["p_boot"] = round(block_boot_p(x), 3)
    return out


def by_year(bt, freq="1D"):
    g = bt["net"].groupby(bt.index.year)
    return pd.DataFrame({"ret": g.sum().round(3), "sharpe": g.apply(lambda s: round(sharpe(s, PPY[freq]), 2))})


def xs_rank_weights(score, mask, q=0.2, long_only=False):
    """Dollar-neutral quantile portfolio: long top q, short bottom q, equal weight, gross 1 (or 1 long)."""
    s = score.where(mask)
    r = s.rank(axis=1, pct=True)
    n = s.notna().sum(axis=1)
    ok = n >= 10
    lo = (r >= 1 - q) & ok.values[:, None]
    sh = (r <= q) & ok.values[:, None]
    wl = lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    ws = sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    return wl if long_only else 0.5 * wl - 0.5 * ws


# ---------- indicators (Wilder smoothing where the original uses it) ----------
def ema(x, n):
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def adx(h, l, c, n):
    up, dn = h.diff(), -l.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    pc = c.shift(1)
    tr = np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs()))
    w = lambda x: x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    atr = w(tr)
    pdi, ndi = 100 * w(pdm) / atr, 100 * w(ndm) / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return w(dx)


def pct_rank(s, win=365, minp=180):
    """Trailing percentile of today's value among the previous values in the last `win` days (0..1)."""
    return s.rolling(win, min_periods=minp).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)


def atr_pct(h, l, c, n=14):
    """Wilder ATR as a fraction of price."""
    pc = c.shift(1)
    tr = np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / c


def hold(entry, exit_):
    """Stateful long flag: 1 from an entry bar until an exit bar (entry wins ties)."""
    s = pd.DataFrame(np.nan, index=entry.index, columns=entry.columns)
    s = s.mask(exit_.fillna(False).astype(bool), 0.0).mask(entry.fillna(False).astype(bool), 1.0)
    return s.ffill().fillna(0.0)


def ts_weights(sig, mask):
    """Time-series signal -> equal slice of capital per tradable coin (1/N_tradable each)."""
    m = mask.astype(float)
    return (sig * m).div(m.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def every(w, k):
    """Rebalance only every k bars; hold weights in between."""
    keep = np.arange(len(w)) % k == 0
    return w.where(np.broadcast_to(keep[:, None], w.shape)).ffill().fillna(0.0)


def grid_summary(rows):
    df = pd.DataFrame(rows)
    best = df.loc[df.IS_sharpe.idxmax()]
    return df, {"n_variants": len(df), "median_IS": round(df.IS_sharpe.median(), 2),
                "median_OOS": round(df.OOS_sharpe.median(), 2),
                "pct_OOS_pos": round(float((df.OOS_sharpe > 0).mean()), 2),
                "IS_best": best["name"], "IS_best_IS": best.IS_sharpe, "IS_best_OOS": best.OOS_sharpe}


if __name__ == "__main__":
    # self-check on synthetic data: a signal that sees the future must win, a lagged-correct one must not leak
    idx = pd.date_range("2020-01-01", periods=2000, freq="D", tz="UTC")
    rng = np.random.default_rng(1)
    ret = pd.DataFrame(rng.normal(0, 0.03, (2000, 20)), index=idx, columns=[f"C{i}" for i in range(20)])
    close = (1 + ret).cumprod()
    P = {"ret": close.pct_change(), "close": close, "funding": ret * 0, "qv": close * 0 + 1}
    cheat = xs_rank_weights(P["ret"].shift(-1), close.notna())   # peeks at t+1
    honest = xs_rank_weights(P["ret"], close.notna())             # random-walk momentum: no edge
    assert sharpe(backtest(cheat, P, 0)["net"], 365) > 10, "future-peek must look amazing"
    assert abs(sharpe(backtest(honest, P, 0)["net"], 365)) < 1.5, "no edge on iid noise"
    assert backtest(honest, P, 10)["net"].sum() < backtest(honest, P, 0)["net"].sum(), "costs must bite"
    print("lab selfcheck ok")
