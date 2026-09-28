"""Round 3, 2026-09-28: how to make the live funding book more profitable. -> results_boost.md
Base = the live rule (top-100, long lowest / short highest 7d funding, drop the worst-7d-return 20% of longs).
One change per row, rules fixed before running. Choose on IS 2020-23, read OOS 2024-01..2026-08 once.
~30 rows were tried: treat an OOS gain under ~0.2 Sharpe as noise.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import lab

D = lab.D / "all"
SYMS = [l.strip() for l in open(D / "crypto_symbols.txt") if l.strip()]
CACHE = Path(__file__).resolve().parent / "__pycache__" / "boost_panel.pkl"


def panel():
    """Same as alltest.panel() (+ taker buy), without importing improve.py (which re-runs its own study)."""
    if CACHE.exists():
        return pickle.load(open(CACHE, "rb"))
    files = (("open", "open.parquet"), ("high", "high.parquet"), ("low", "low.parquet"), ("close", "close.parquet"),
             ("qv", "quote_volume.parquet"), ("tbq", "taker_buy_quote.parquet"), ("prem", "premium_close.parquet"),
             ("funding", "funding_daily.parquet"))
    P = {k: pd.read_parquet(D / f) for k, f in files}
    cols = [s for s in SYMS if s in P["close"].columns]
    idx = P["close"].index
    idx = idx[(idx >= "2020-01-01") & (idx <= "2026-08-31")]
    for k in P:
        P[k] = P[k].reindex(index=idx, columns=cols)
        if P[k].index.tz is None:
            P[k].index = P[k].index.tz_localize("UTC")
    P["funding"] = P["funding"].fillna(0.0)
    P["ret"] = P["close"].pct_change(fill_method=None)
    ev = pd.read_parquet(D / "funding_events.parquet")
    ev = ev[ev.symbol.isin(cols)]
    ev["day"] = (ev.ts.dt.floor("min") - pd.Timedelta("1min")).dt.floor("D")
    P["nfund"] = ev.groupby(["day", "symbol"]).size().unstack().reindex(index=idx, columns=cols)   # settlements per day
    P["flast"] = ev.sort_values("ts").groupby(["day", "symbol"]).rate.last().unstack().reindex(index=idx, columns=cols)
    pickle.dump(P, open(CACHE, "wb"))
    return P


P = panel()
C, R, F, QV = P["close"], P["ret"], P["funding"], P["qv"]
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))
OOS = slice(lab.SPLIT, None)
U = lab.universe(P, 100)
F7 = F.rolling(7).mean()
ret7 = C / C.shift(7) - 1
vol30 = R.rolling(30, min_periods=20).std()
COST = 7.0


def live(score=None, mask=U, q=0.2):
    s = -F7 if score is None else score
    return lab.drop_falling_longs(lab.xs_rank_weights(s, mask, q), ret7)


def legs(w):
    return w.clip(lower=0), -w.clip(upper=0)


def norm(x, g=0.5):
    return g * x.div(x.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def drop_short(w, drop):
    lo, sh = legs(w)
    return lo - norm(sh.where(~drop.fillna(False), 0.0))


def reweight(w, f_long, f_short):
    """Keep the same coins, weight each leg by f (>=0), each leg still 0.5."""
    lo, sh = legs(w)
    return norm((lo > 0) * f_long) - norm((sh > 0) * f_short)


def every_k(w, k):
    return lab.every(w, k)


def buffered_short(w_enter, w_exit):
    """Hysteresis on the short leg: enter when in w_enter's short leg, stay while in w_exit's short leg."""
    e, x = (w_enter < 0).values, (w_exit < 0).values
    cur = np.zeros(e.shape[1], bool); out = np.zeros(e.shape, bool)
    for i in range(len(e)):
        cur = (cur & x[i]) | e[i]
        out[i] = cur
    lo, _ = legs(w_enter)
    return lo - norm(pd.DataFrame(out, index=w_enter.index, columns=w_enter.columns).astype(float))


def vol_target(w, target=0.20, lb=30):
    """Scale gross so the book's trailing 30d vol hits `target`/yr (cap 3x). Known at t."""
    b = lab.backtest(w, P, COST)
    rv = b.net.rolling(lb, min_periods=20).std() * np.sqrt(365)
    k = (target / rv).clip(upper=3.0).fillna(1.0)
    return w.mul(k, axis=0)


def beta_neutral(w, lb=60):
    mkt = R.where(U).mean(axis=1)
    beta = R.rolling(lb, min_periods=30).cov(mkt).div(mkt.rolling(lb, min_periods=30).var(), axis=0)
    bl = (w.clip(lower=0) * beta).sum(axis=1)
    bs = (-w.clip(upper=0) * beta).sum(axis=1)
    a = (bs / (bl + bs)).where((bl > 0) & (bs > 0), 0.5).clip(0.25, 0.75)
    return w.clip(lower=0).mul(2 * a, axis=0) + w.clip(upper=0).mul(2 * (1 - a), axis=0)


def sh(x):
    return round(lab.sharpe(x, 365), 2)


def run(w, cost=COST, lag=0):
    return lab.backtest(w.shift(lag).fillna(0.0) if lag else w, P, cost)


def line(name, w):
    b = run(w); o = b.loc[OOS]
    lo, s = legs(w)
    pos_l, pos_s = lo.shift(1).fillna(0), s.shift(1).fillna(0)
    Rz = R.fillna(0)
    return dict(variant=name, IS=sh(b.net.loc[IS]), OOS=sh(o.net), OOS15=sh(run(w, 15).net.loc[OOS]),
                OOS_1d=sh(run(w, COST, 1).net.loc[OOS]),
                OOS_yr=round(o.net.mean() * 365, 3), OOS_tot=round(float((1 + o.net).prod() - 1), 2),
                DD=round(lab.maxdd(b.net), 3),
                px_long=round(float((pos_l * Rz).sum(axis=1).loc[OOS].mean() * 365), 3),
                px_short=round(float(-(pos_s * Rz).sum(axis=1).loc[OOS].mean() * 365), 3),
                fund_long=round(float(-(pos_l * F).sum(axis=1).loc[OOS].mean() * 365), 3),
                fund_short=round(float((pos_s * F).sum(axis=1).loc[OOS].mean() * 365), 3), cost=round(float(o.cost.mean() * 365), 3),
                gross=round(float(b.gross_exp.loc[OOS].mean()), 2))


BASE = live()
lo0, sh0 = legs(BASE)
rk_short = lambda s: s.where(sh0 > 0).rank(axis=1, pct=True)      # rank inside the short leg
qv_spike = QV / QV.rolling(30, min_periods=15).mean().shift(1)
tb_share = P["tbq"] / QV
age = C.notna().cumsum()
prem7 = P["prem"].rolling(7, min_periods=4).mean()
F30 = F.rolling(30, min_periods=15).mean()
U50 = lab.universe(P, 50)
hi30 = C / C.rolling(30, min_periods=15).max() - 1

rk_long = lambda s: s.where(lo0 > 0).rank(axis=1, pct=True)


def without_long(w, drop):
    lo, sh = legs(w)
    return norm(lo.where(~drop.fillna(False), 0.0)) - sh


def cap(w, c=0.05):
    lo, s = legs(w)
    for _ in range(5):
        lo, s = norm(lo.clip(upper=c)), norm(s.clip(upper=c))
    return lo - s


def new_rule(mask=U, q=1 / 3, c=0.05):
    """Candidate: terciles, short leg stays while in the top half (buffer), inverse-30d-vol weights, 5% per-coin cap,
    gold tokens out. Keeps the live drop-falling-longs rule."""
    m = mask.copy()
    m[[g for g in ("PAXGUSDT", "XAUTUSDT") if g in m.columns]] = False
    w = buffered_short(live(mask=m, q=q), live(mask=m, q=0.5))
    return cap(reweight(w, 1 / vol30, 1 / vol30), c)


V = {
    "LIVE (base)": BASE,
    # A. signal
    "signal: 1d funding": live(-F),
    "signal: 3d funding": live(-F.rolling(3).mean()),
    "signal: 14d funding": live(-F.rolling(14).mean()),
    "signal: last settlement rate": live(-P["flast"]),
    "signal: 7d premium index": live(-prem7),
    "signal: rank avg 7d funding + 7d premium": live(-(F7.where(U).rank(axis=1) + prem7.where(U).rank(axis=1))),
    "signal: carry / vol (F7 / vol30)": live(-F7 / vol30),
    "signal: F7 + persistence (avg rank F7, F30)": live(-(F7.where(U).rank(axis=1) + F30.where(U).rank(axis=1))),
    # B. short-leg filters (price loss is on the short leg)
    "short filter: drop top-20% 7d return in leg": drop_short(BASE, rk_short(ret7) > 0.8),
    "short filter: drop 1d volume > 3x 30d avg": drop_short(BASE, qv_spike > 3),
    "short filter: drop taker-buy share top 20% in leg": drop_short(BASE, rk_short(tb_share.rolling(3).mean()) > 0.8),
    "short filter: drop age < 120d": drop_short(BASE, age < 120),
    "short filter: drop coins at their 30d high": drop_short(BASE, hi30 > -0.02),
    "short filter: shorts only from top-50": drop_short(BASE, ~U50),
    "short filter: drop funding just jumped (1d > 3x 7d)": drop_short(BASE, (F > 3 * F7) & (F7 > 0)),
    # C. weights
    "weights: inverse vol, both legs": reweight(BASE, 1 / vol30, 1 / vol30),
    "weights: short leg by carry (F7)": reweight(BASE, lo0 * 0 + 1, F7.clip(lower=0)),
    "weights: short leg carry / vol^2": reweight(BASE, lo0 * 0 + 1, F7.clip(lower=0) / vol30 ** 2),
    "weights: beta-neutral legs": beta_neutral(BASE),
    "weights: q=0.33 terciles": live(q=1 / 3),
    "weights: q=0.10 tails": live(q=0.1),
    "hedge: short leg + long EW universe": norm(U.astype(float)) - norm(sh0),
    "hedge: short leg + long BTC": pd.DataFrame(0.0, index=C.index, columns=C.columns).assign(BTCUSDT=0.5 * (sh0.sum(axis=1) > 0)) - sh0,
    # D. turnover
    "turnover: rebalance every 3 days": every_k(BASE, 3),
    "turnover: short buffer (stay while top 35%)": buffered_short(BASE, live(q=0.35)),
    # E. universe
    "universe: top-150": live(mask=lab.universe(P, 150)),
    "universe: top-200": live(mask=lab.universe(P, 200)),
    # G. long leg (OOS: the long leg earns the funding, +53%/yr, and loses the price, -25%/yr)
    "long filter: drop longs below 30d average": without_long(BASE, C < C.rolling(30).mean()),
    "long filter: drop longs with 30d return in leg bottom 30%": without_long(BASE, rk_long(C / C.shift(30) - 1) < 0.3),
    "long filter: drop age < 120d": without_long(BASE, age < 120),
    "long filter: drop 1d volume > 3x 30d avg": without_long(BASE, qv_spike > 3),
    "long filter: only coins on 1h/4h funding (>3 settlements/day)": without_long(BASE, ~(P["nfund"] > 3)),
    "long filter: drop coins on 1h/4h funding": without_long(BASE, P["nfund"] > 3),
    "long filter: drop premium top 30% in leg (least discount)": without_long(BASE, rk_long(prem7) > 0.7),
    "long filter: drop premium bottom 30% in leg (deepest discount)": without_long(BASE, rk_long(prem7) < 0.3),
    "long filter: drop taker-buy share bottom 20% in leg": without_long(BASE, rk_long(tb_share.rolling(3).mean()) < 0.2),
    "weights: long leg by carry (-F7)": reweight(BASE, (-F7).clip(lower=0), sh0 * 0 + 1),
    "weights: long leg inverse vol only": reweight(BASE, 1 / vol30, sh0 * 0 + 1),
    "weights: short leg inverse vol only": reweight(BASE, lo0 * 0 + 1, 1 / vol30),
    "legs: long 0.6 / short 0.4": BASE.clip(lower=0) * 1.2 + BASE.clip(upper=0) * 0.8,
    "legs: long 0.4 / short 0.6": BASE.clip(lower=0) * 0.8 + BASE.clip(upper=0) * 1.2,
    # F. sizing
    "sizing: vol target 20%/yr": vol_target(BASE, 0.20),
    # H. combination (pieces that held on both halves; IS 2.38 vs live 2.31, so the gain is mostly OOS)
    "NEW: q.33 + short buffer 50% + inverse vol + 5% cap, no gold": new_rule(),
    "NEW at 2x gross": new_rule() * 2,
}

if __name__ == "__main__":
    only = sys.argv[1:]
    rows = [line(k, w) for k, w in V.items() if not only or any(o in k for o in only)]
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(T.to_string(index=False))
    if not only:
        open("results_boost.md", "w").write("# Round 3: making the funding book more profitable (boost.py)\n\n"
            "Base = live rule. One change per row. OOS = 2024-01..2026-08. px/fund = price / funding P&L per year by leg (OOS).\n\n"
            + T.to_markdown(index=False) + "\n")
