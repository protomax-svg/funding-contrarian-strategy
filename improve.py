"""Mechanical improvements to #7b on the existing 50-coin data (no new data needed).

Each variant changes ONE thing vs the base rule. All are run with and without the live ATR filter.
Read the whole table, not the best row: ~10 variants were tried, so a +0.1 Sharpe gain is noise.
"""
import numpy as np
import pandas as pd

import lab

COST = 7.0
P = lab.load("1D")
U = lab.universe(P, 30)
C, R, F = P["close"], P["ret"], P["funding"]
F7 = F.rolling(7).mean()
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))
OOS = slice(lab.SPLIT, None)
ATR_P = lab.pct_rank(lab.atr_pct(P["high"]["BTCUSDT"], P["low"]["BTCUSDT"], C["BTCUSDT"]))
ATR_ON = (ATR_P >= 1 / 3).astype(float).where(ATR_P.notna(), 1.0)


def buffered(score, mask, enter=0.2, exit_=0.35):
    """Hysteresis: enter the long (short) side in the bottom (top) `enter` share of ranks,
    leave only when the coin drifts out of the `exit_` share. Equal weight inside each side."""
    r = score.where(mask).rank(axis=1, pct=True).values
    ok = (score.where(mask).notna().sum(axis=1) >= 10).values
    side = np.zeros(r.shape)
    cur = np.zeros(r.shape[1])
    for i in range(len(r)):
        ri = r[i]
        if not ok[i]:
            cur[:] = 0
        else:
            valid = np.isfinite(ri)
            cur = np.where(~valid, 0, cur)
            cur = np.where((cur > 0) & (ri < 1 - exit_), 0, cur)
            cur = np.where((cur < 0) & (ri > exit_), 0, cur)
            cur = np.where(valid & (cur == 0) & (ri >= 1 - enter), 1, cur)
            cur = np.where(valid & (cur == 0) & (ri <= enter), -1, cur)
        side[i] = cur
    s = pd.DataFrame(side, index=score.index, columns=score.columns)
    lo, sh = (s > 0), (s < 0)
    return 0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) - \
        0.5 * sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)


def rank_weighted(score, mask):
    """Linear rank weights over the whole universe, dollar neutral, gross 1."""
    r = score.where(mask).rank(axis=1, pct=True)
    d = r.sub(r.mean(axis=1), axis=0)
    return d.div(d.abs().sum(axis=1), axis=0).fillna(0)


def beta_neutral(w, lb=60):
    """Scale the long and short legs so the book has zero beta to the equal-weight market."""
    mkt = R.where(U).mean(axis=1)
    beta = R.rolling(lb, min_periods=30).cov(mkt).div(mkt.rolling(lb, min_periods=30).var(), axis=0)
    bl = (w.clip(lower=0) * beta).sum(axis=1)
    bs = (-w.clip(upper=0) * beta).sum(axis=1)
    # keep gross = 1: long leg a, short leg b, a*bl = b*bs, a+b = 1 (legs currently 0.5 each)
    a = (bs / (bl + bs)).where((bl > 0) & (bs > 0), 0.5).clip(0.25, 0.75)
    return w.clip(lower=0).mul(2 * a, axis=0) + w.clip(upper=0).mul(2 * (1 - a), axis=0)


z90 = (F7 - F7.rolling(90, min_periods=45).mean()) / F7.rolling(90, min_periods=45).std()
rk = lambda s: s.where(U).rank(axis=1, pct=True)
VARIANTS = {
    "base (7d funding, top/bottom 20%)": lab.xs_rank_weights(-F7, U),
    "buffer: enter 20%, exit 35%": buffered(-F7, U, 0.2, 0.35),
    "buffer: enter 20%, exit 50%": buffered(-F7, U, 0.2, 0.5),
    "rank-weighted (all coins)": rank_weighted(-F7, U),
    "beta-neutral legs": beta_neutral(lab.xs_rank_weights(-F7, U)),
    "signal: funding z-score vs own 90d": lab.xs_rank_weights(-z90, U),
    "signal: raw + z-score (avg rank)": lab.xs_rank_weights(rk(-F7) + rk(-z90), U),
    "signal: horizons 3+7+14 (avg rank)": lab.xs_rank_weights(sum(rk(-F.rolling(n).mean()) for n in (3, 7, 14)), U),
    "signal: + 28d momentum (avg rank)": lab.xs_rank_weights(rk(-F7) + rk(C / C.shift(28)), U),
    "universe: min age 120d (skip new listings)": lab.xs_rank_weights(-F7, lab.universe(P, 30, min_age_bars=120)),
    "universe: top-40": lab.xs_rank_weights(-F7, lab.universe(P, 40)),
    "buffer 20/35 + beta-neutral": beta_neutral(buffered(-F7, U, 0.2, 0.35)),
}


def row(name, w, atr):
    ww = w.mul(ATR_ON, axis=0) if atr else w
    b = lab.backtest(ww, P, COST)
    x = b["net"]
    return {"variant": name, "ATR filter": "yes" if atr else "no",
            "IS": round(lab.sharpe(x.loc[IS], 365), 2), "OOS": round(lab.sharpe(x.loc[OOS], 365), 2),
            "OOS@15bps": round(lab.sharpe(lab.backtest(ww, P, 15)["net"].loc[OOS], 365), 2),
            "OOS +1d": round(lab.sharpe(lab.backtest(ww.shift(1).fillna(0), P, COST)["net"].loc[OOS], 365), 2),
            "OOS ann": round(x.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(x), 3),
            "turnover/yr": round(b["turn"].mean() * 365, 1), "cost/yr": round(b["cost"].mean() * 365, 3),
            "net beta": round(float(pd.concat([x, R.where(U).mean(axis=1)], axis=1).dropna().cov().iloc[0, 1]
                                    / R.where(U).mean(axis=1).var()), 2)}


rows = []
for nm, w in VARIANTS.items():
    for atr in (False, True):
        rows.append(row(nm, w, atr))
    print(nm, "done", flush=True)
df = pd.DataFrame(rows)
open("results_improve.md", "w").write(
    "# Mechanical improvements (existing 50-coin data)\n\nOne change per row vs base. 7 bps/side, real funding. "
    "IS 2020-2023, OOS 2024-01..2026-08. ~12 variants tried: treat gains under ~0.15 Sharpe as noise.\n\n"
    + df.to_markdown(index=False) + "\n")
print(df.to_string())


# ---------------- literature ideas (research/improvements.md) ----------------
def with_stop(w, stop=0.30, cool=7):
    """Per-coin stop: if a position moves `stop` against its entry close, close it and block that coin
    for `cool` days. Daily closes only (a real stop fills intraday, often worse in a squeeze)."""
    wv = w.values.copy()
    cv = C.values
    entry = np.full(wv.shape[1], np.nan)
    side = np.zeros(wv.shape[1])
    blocked = np.zeros(wv.shape[1])
    for i in range(len(wv)):
        blocked = np.maximum(blocked - 1, 0)
        tgt = np.sign(wv[i])
        for j in range(wv.shape[1]):
            if blocked[j] > 0:
                wv[i, j] = 0.0
                side[j] = 0
                continue
            if tgt[j] != side[j]:
                side[j], entry[j] = tgt[j], cv[i, j]
            elif side[j] != 0 and np.isfinite(entry[j]) and np.isfinite(cv[i, j]):
                move = cv[i, j] / entry[j] - 1
                if side[j] * move < -stop:
                    wv[i, j] = 0.0
                    side[j] = 0
                    blocked[j] = cool
    out = pd.DataFrame(wv, index=w.index, columns=w.columns)
    # re-normalise each leg back to 0.5 after stopped names drop out
    lo, sh = out.clip(lower=0), -out.clip(upper=0)
    return (0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0) - \
        (0.5 * sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0)


def without(w, drop_short=None, drop_long=None):
    """Remove names from a leg and re-weight the rest of that leg to 0.5."""
    lo, sh = w.clip(lower=0), -w.clip(upper=0)
    if drop_short is not None:
        sh = sh.where(~drop_short.fillna(False), 0)
    if drop_long is not None:
        lo = lo.where(~drop_long.fillna(False), 0)
    return (0.5 * lo.div(lo.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0) - \
        (0.5 * sh.div(sh.sum(axis=1).replace(0, np.nan), axis=0)).fillna(0)


xs_z = F7.where(U).sub(F7.where(U).mean(axis=1), axis=0).div(F7.where(U).std(axis=1), axis=0)
ret7 = C / C.shift(7) - 1
ret7_rank = ret7.where(U).rank(axis=1, pct=True)
BASE_W = lab.xs_rank_weights(-F7, U)
BEST_W = beta_neutral(buffered(-F7, U, 0.2, 0.35))
LIT = {}
BUF_W = buffered(-F7, U, 0.2, 0.35)
# filters act on the equal-weight book; beta-neutral sizing is applied last so it is not undone
for tag, w0, post in (("base", BASE_W, lambda w: w), ("buffer+beta", BUF_W, beta_neutral)):
    LIT[f"{tag}"] = post(w0)
    LIT[f"{tag} + stop 30% / 7d block"] = post(with_stop(w0, 0.30))
    LIT[f"{tag} + stop 50% / 7d block"] = post(with_stop(w0, 0.50))
    LIT[f"{tag} + no short if XS funding z > 2.5"] = post(without(w0, drop_short=xs_z > 2.5))
    LIT[f"{tag} + no short if 7d return in top 20%"] = post(without(w0, drop_short=ret7_rank >= 0.8))
    LIT[f"{tag} + no long if 7d return in bottom 20%"] = post(without(w0, drop_long=ret7_rank <= 0.2))
lit_rows = []
for nm, w in LIT.items():
    lit_rows.append(row(nm, w, True))
    print(nm, "done", flush=True)
lit = pd.DataFrame(lit_rows)
open("results_improve.md", "a").write(
    "\n## Ideas from the literature search (all with the live ATR filter)\n\n" + lit.to_markdown(index=False) + "\n")
print(lit.to_string())
