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
    alive = P["qv"] > 0                      # delisted coins keep printing flat zero-volume bars in the archive
    rank = adv.where((age >= min_age_bars) & alive).rank(axis=1, ascending=False)
    return (rank <= top_n) & c.notna() & alive


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


def drop_falling_longs(w, ret7, q=0.2):
    """Drop the longs whose 7d return is in the bottom q of the long leg; re-weight the long leg to 0.5.
    Falling low-funding coins keep falling (ret7_test.py: OOS Sharpe 1.10 -> 1.27, placebo p 0.005)."""
    drop = (ret7.where(w > 0).rank(axis=1, pct=True) <= q) & (w > 0)
    lo = w.clip(lower=0).where(~drop, 0.0)
    return 0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) + w.clip(upper=0)


GOLD = ("PAXGUSDT", "XAUTUSDT")


def boost_weights(F7, ret7, vol30, U, q=1 / 3, stay=0.5, cap=0.05, held_short=None):
    """boost.py NEW book: long the lowest-q / short the highest-q 7d funding (gold tokens out), drop falling longs;
    a short stays while it is in the highest `stay` share; both legs weighted by 1/vol30, max `cap` per coin, 0.5 each.
    The short buffer is path dependent: held_short (symbols short now) replaces the path state on the last row (live)."""
    m = U.copy()
    m[[g for g in GOLD if g in m.columns]] = False
    enter = drop_falling_longs(xs_rank_weights(-F7, m, q), ret7)
    e, x = (enter < 0).values, (xs_rank_weights(-F7, m, stay) < 0).values
    cur, out = np.zeros(e.shape[1], bool), np.zeros(e.shape, bool)
    for i in range(len(e)):
        if held_short is not None and i == len(e) - 1:
            cur = np.isin(np.asarray(F7.columns), list(held_short))
        cur = (cur & x[i]) | e[i]
        out[i] = cur
    norm = lambda a: 0.5 * a.div(a.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    iv = 1 / vol30
    lo, sh = norm((enter > 0) * iv), norm(pd.DataFrame(out, index=F7.index, columns=F7.columns) * iv)
    for _ in range(5):
        lo, sh = norm(lo.clip(upper=cap)), norm(sh.clip(upper=cap))
    return lo - sh


def crash_short_weights(P, U, z_lo=-4.2, z_hi=-2.2, hold=21, far_sig=3.3, cap=0.05, vol_spike=2.0):
    """crash_short.py book: short every coin that fell z_lo..z_hi sigma (30d vol before the day) in one day while more than
    far_sig sigma below its 365d high, for `hold` days, equal weight, max `cap` per coin (rest in cash);
    hedged with the same notional long in the equal-weight top-N (U). Known at close t.
    vol_spike: only drops on a day with quote volume > vol_spike x its 30d average (crash_lab.py: IS 0.67 -> 1.96,
    OOS 1.49 -> 1.32, max DD -25% -> -15%); None = the original crash_short.py base."""
    C, R = P["close"], P["close"].pct_change(fill_method=None)
    vol = R.rolling(30, min_periods=20).std().shift(1)
    dist = C / P["high"].rolling(365, min_periods=180).max() - 1
    z = R / vol
    ev = (z >= z_lo) & (z <= z_hi) & U & vol.notna() & (-dist > far_sig * vol)
    if vol_spike is not None:
        ev &= P["qv"] > vol_spike * P["qv"].rolling(30, min_periods=15).mean().shift(1)
    act = ev.astype(float).rolling(hold, min_periods=1).max().fillna(0.0).where(P["qv"] > 0, 0.0)
    sh = act.div(act.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).clip(upper=cap)
    m = U.astype(float)
    m = m.div(m.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return m.mul(sh.sum(axis=1), axis=0) - sh


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
    w = pd.DataFrame([[0.1] * 5 + [-0.1] * 5], columns=list("ABCDEFGHIJ"))
    r7 = pd.DataFrame([[-0.5, 0.1, 0.2, 0.3, 0.4] + [-0.9] * 5], columns=w.columns)
    d = drop_falling_longs(w, r7).iloc[0]
    assert d["A"] == 0 and abs(d[list("BCDE")] - 0.125).max() < 1e-12, "worst 20% of longs out, rest re-weighted"
    assert (d[list("FGHIJ")] == -0.1).all() and abs(d.sum()) < 1e-12, "shorts untouched, still neutral"
    # crash book: one -3 sigma day far below the high -> short for 21 days at the 5% cap, hedged by the EW market
    n = 400
    r = pd.DataFrame(0.001, index=idx[:n], columns=list("ABCDEFGHIJ"))       # the others: smooth, at their high
    r["A"] = np.r_[np.full(300, -0.003), np.tile([0.005, -0.005], 50)]       # A bleeds to ~40% of its high, +-1 sigma
    r.iloc[350, 0] = -3 * r["A"].iloc[320:350].std()                         # then one clean -3 sigma day
    c = (1 + r).cumprod()
    qv = c * 0 + 1; qv.iloc[350, 0] = 3.0                                    # the drop comes with 3x volume
    Pc = {"close": c, "high": c, "qv": qv}
    assert crash_short_weights({**Pc, "qv": c * 0 + 1}, c.notna() & (np.arange(n) >= 60)[:, None]).abs().sum().sum() == 0, \
        "no volume spike -> no trade"
    Uc = c.notna() & (np.arange(n) >= 60)[:, None]
    cw = crash_short_weights(Pc, Uc)
    assert abs(cw["A"].iloc[350] - (0.05 / 10 - 0.05)) < 1e-12 and abs(cw["A"].iloc[370] - cw["A"].iloc[350]) < 1e-12
    assert cw["A"].iloc[371] == 0 and cw.iloc[349].abs().sum() == 0, "held exactly 21 days, nothing before the event"
    assert abs(cw.sum(axis=1)).max() < 1e-12, "dollar neutral"
    # boost book: 30 coins, funding rank = column order; a held short stays while in the top half, cap 5%, legs 0.5
    cols = [f"C{i}" for i in range(29)] + ["PAXGUSDT"]
    f7 = pd.DataFrame([np.arange(30.0)] * 2, columns=cols)
    one = f7 * 0 + 1.0
    bw = boost_weights(f7, one, one * 0.02, one > 0, held_short={"C15"}).iloc[-1]
    assert bw["PAXGUSDT"] == 0 and bw["C15"] < 0 and bw["C14"] == 0, "gold out, held short stays in the top half only"
    assert abs(bw.clip(lower=0).sum() - 0.5) < 1e-12 and abs(bw.clip(upper=0).sum() + 0.5) < 1e-12 and bw.abs().max() <= 0.05 + 1e-12
    print("lab selfcheck ok")
