"""What else can be done with the crash-short book (lab.crash_short_weights, live as the second fronttest book)?

Base: short a coin after a -4.2..-2.2 sigma day while > 3.3 sigma below its 365d high, 21 days, max 5% per coin,
hedged with the same notional long in the equal-weight top-100. Rules below were fixed before the first run;
each is ONE change on top of the base. Pick on IS (2020-23) only, read OOS (2024-01..2026-08) once.
The base itself was found by looking at OOS (crash_short.py), so its own OOS is optimistic. -> results_crash_lab.md
  entry filters (only open a short when the condition holds at the close of the drop day):
    market vol high / low, market vol rising (7d vs 60d), BTC ATR not in its low third, the coin's own vol rising,
    idiosyncratic drop (market calm that day) vs market-wide crash, volume spike on the drop day, 7d funding sign
  exits: squeeze stop (+30% / +50% above entry), exit once the coin is back above its pre-drop close
  sizing / hedge: cap 3% / 10%, inverse-vol size, hedge with BTC or the top-10 by volume instead of the top-100
"""
import numpy as np
import pandas as pd

import lab
from dip52 import BTC, C, DIST, EW, IS, OOS, P, R, U, VOL, Z, alpha, net, placebo, sh

QV = P["qv"]
BASE_EV = (Z >= -4.2) & (Z <= -2.2) & U & VOL.notna() & (-DIST > 3.3 * VOL)


def active(ev, hold=21, stop=None, recover=False):
    """1 while a short is open. A new event restarts the clock (same as the rolling max in lab.crash_short_weights).
    stop: close above entry*(1+stop) at a close -> out; recover: close back at the pre-drop close -> out."""
    if stop is None and not recover:
        return ev.astype(float).rolling(hold, min_periods=1).max().fillna(0.0)
    A = np.zeros(ev.shape)
    e, c = ev.values, C.ffill().values
    for j in np.where(e.any(axis=0))[0]:
        left = 0; entry = pre = np.nan
        for t in range(len(e)):
            if e[t, j]:
                left, entry, pre = hold, c[t, j], c[t - 1, j] if t else np.nan
            if left > 0:
                if not e[t, j] and ((stop is not None and c[t, j] > entry * (1 + stop)) or (recover and c[t, j] >= pre)):
                    left = 0
                    continue
                A[t, j] = 1.0; left -= 1
    return pd.DataFrame(A, index=ev.index, columns=ev.columns)


TOP10 = (QV.rolling(30, min_periods=15).mean().where(U).rank(axis=1, ascending=False) <= 10)


def book(extra=None, hold=21, cap=0.05, hedge="EW", stop=None, recover=False, invvol=False):
    ev = BASE_EV & (True if extra is None else extra.fillna(False))
    act = active(ev, hold, stop, recover).where(QV > 0, 0.0)
    if invvol:
        act = act * (1 / VOL.where(ev).ffill()).where(act > 0, 0.0)          # size by 1/vol at the event
    s = act.div(act.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).clip(upper=cap)
    g = s.sum(axis=1)
    if hedge == "BTC":
        m = pd.DataFrame(0.0, index=s.index, columns=s.columns); m["BTCUSDT"] = 1.0
    else:
        m = (U if hedge == "EW" else TOP10).astype(float)
        m = m.div(m.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return m.mul(g, axis=0) - s


assert float((book() - lab.crash_short_weights(P, U, vol_spike=None)).abs().max().max()) < 1e-12, "base = crash_short.py"
assert float((book(QV > 2 * QV.rolling(30, min_periods=15).mean().shift(1)) - lab.crash_short_weights(P, U)).abs().max().max()) < 1e-12, \
    "volume-spike variant = the live function"

ewv30 = EW.rolling(30).std()
mk = lambda s: pd.DataFrame(np.repeat(s.values[:, None], len(C.columns), axis=1), index=C.index, columns=C.columns)
ew_z = EW / ewv30.shift(1)
vol_ratio = R.rolling(7).std().shift(1) / R.rolling(60).std().shift(1)
qv_spike = QV / QV.rolling(30, min_periods=15).mean().shift(1)
f7 = P["funding"].rolling(7).mean()
btc_atr = lab.pct_rank(lab.atr_pct(P["high"]["BTCUSDT"], P["low"]["BTCUSDT"], C["BTCUSDT"]))
mvp = lab.pct_rank(ewv30)
FILTERS = {
    "market vol high (30d EW vol >= median of last year)": mk(mvp >= 0.5),
    "market vol top third": mk(mvp >= 2 / 3),
    "market vol low (below median)": mk(mvp < 0.5),
    "market vol rising (7d/60d EW vol > 1)": mk(EW.rolling(7).std() / EW.rolling(60).std() > 1),
    "market vol rising strongly (> 1.25)": mk(EW.rolling(7).std() / EW.rolling(60).std() > 1.25),
    "BTC ATR not in its low third": mk(btc_atr >= 1 / 3),
    "coin vol rising before the drop (7d/60d > 1)": vol_ratio > 1,
    "coin vol calm before the drop (7d/60d <= 1)": vol_ratio <= 1,
    "idiosyncratic: market that day > -1 sigma": mk(ew_z > -1),
    "market-wide crash day (market <= -1 sigma)": mk(ew_z <= -1),
    "volume spike on the drop day (> 2x 30d avg)": qv_spike > 2,
    "no volume spike (<= 2x)": qv_spike <= 2,
    "7d funding >= 0 (shorts not crowded)": f7 >= 0,
    "7d funding < 0 (shorts crowded)": f7 < 0,
}
OTHER = {
    "exit: squeeze stop +30%": dict(stop=0.30), "exit: squeeze stop +50%": dict(stop=0.50),
    "exit: back above pre-drop close": dict(recover=True),
    "cap 3%": dict(cap=0.03), "cap 10%": dict(cap=0.10), "inverse-vol size": dict(invvol=True),
    "hedge: BTC only": dict(hedge="BTC"), "hedge: top-10 EW": dict(hedge="TOP10"),
}


def row(name, w, n_ev=None):
    x = net(w)
    return {"variant": name, "IS": sh(x, IS), "OOS": sh(x, OOS), "OOS@15bps": sh(net(w, 15), OOS),
            "OOS +1d": sh(net(w, lag=1), OOS), "IS %/yr": round(100 * x.loc[IS].mean() * 365, 1),
            "OOS %/yr": round(100 * x.loc[OOS].mean() * 365, 1), "maxDD": round(lab.maxdd(x), 3),
            "events kept": n_ev, "avg short gross": round(float(-w.clip(upper=0).sum(axis=1).mean()), 2)}, x


if __name__ == "__main__":
    n0 = int(BASE_EV.sum().sum())
    rows, curves = [], {}
    r, curves["base"] = row("base (crash_short.py; live until 2026-09-28)", book(), 1.0); rows.append(r)
    for nm, f in FILTERS.items():
        r, curves[nm] = row(f"filter: {nm}", book(f), round(float((BASE_EV & f.fillna(False)).sum().sum()) / n0, 2)); rows.append(r)
        print(nm, flush=True)
    for nm, kw in OTHER.items():
        r, curves[nm] = row(nm, book(**kw), 1.0); rows.append(r)
        print(nm, flush=True)
    T = pd.DataFrame(rows)
    fund = net(lab.drop_falling_longs(lab.xs_rank_weights(-f7, U), C / C.shift(7) - 1))     # live funding book
    alt = T.iloc[1:]
    best = alt.loc[alt.IS.idxmax()]
    top3 = alt.nlargest(3, "IS")
    extra = []
    for _, b in top3.iterrows():
        nm = b.variant.replace("filter: ", "")
        w = book(FILTERS[nm]) if nm in FILTERS else book(**OTHER[nm])
        pl = placebo(w, 50)
        x = curves[nm]
        extra.append({"variant": b.variant, "IS": b.IS, "OOS": b.OOS, "placebo p (all years)": round(float((pl >= lab.sharpe(x, 365)).mean()), 2),
                      "alpha t": alpha(x)[1], "corr w/ funding book": round(x.corr(fund), 2),
                      "50/50 with funding OOS": sh(0.5 * fund + 0.5 * x, OOS), "50/50 maxDD": round(lab.maxdd(0.5 * fund + 0.5 * x), 3)})
    xb = curves["base"]
    extra.append({"variant": "base (crash_short.py)", "IS": T.IS[0], "OOS": T.OOS[0], "placebo p (all years)": None, "alpha t": alpha(xb)[1],
                  "corr w/ funding book": round(xb.corr(fund), 2), "50/50 with funding OOS": sh(0.5 * fund + 0.5 * xb, OOS),
                  "50/50 maxDD": round(lab.maxdd(0.5 * fund + 0.5 * xb), 3)})
    rank_corr = alt.IS.rank().corr(alt.OOS.rank())
    yr = pd.DataFrame({k: curves[k].groupby(curves[k].index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1))
                       for k in ["base"] + [v.replace("filter: ", "") for v in top3.variant]})
    summ = (f"{len(alt)} variants. IS-best: **{best.variant}** (IS {best.IS} -> OOS {best.OOS}; base IS {T.IS[0]} -> OOS {T.OOS[0]}). "
            f"Rank correlation IS vs OOS across variants: {rank_corr:.2f} (near 0 = the IS ranking does not carry over). "
            f"Variants with IS > base and OOS > base: {int(((alt.IS > T.IS[0]) & (alt.OOS > T.OOS[0])).sum())}.")
    open(lab.D.parent / "results_crash_lab.md", "w").write(
        "# Crash-short book: filters, exits, sizing, hedges\n\nOne change at a time on top of the live base. 7 bps, real funding, "
        "top-100, all perps. IS 2020-23, OOS 2024-01..2026-08. events kept = share of the base's events that pass the filter.\n\n"
        + summ + "\n\n" + T.to_markdown(index=False) + "\n\n## Top 3 by IS: placebo, alpha, blend with the live funding book\n\n"
        + pd.DataFrame(extra).to_markdown(index=False) + "\n\n## Return by year (%)\n\n" + yr.to_markdown() + "\n")
    print(T.to_string(index=False)); print(summ); print(pd.DataFrame(extra).to_string(index=False)); print(yr.to_string())
